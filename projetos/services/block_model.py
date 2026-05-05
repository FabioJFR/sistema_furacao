import csv
import io
import json
import logging
import math
from dataclasses import dataclass

from django.db import transaction

from projetos.models import BlockModelCell, Medicao, Modelo3DBlock, Projeto

logger = logging.getLogger("core")
MAX_INFERRED_CELLS = 40000
MAX_NEIGHBOR_DISTANCE_CELLS = 2.35


@dataclass
class PontoBloco:
    x: float
    y: float
    z: float
    litologia: str
    dureza: float | None
    densidade: float | None
    teor: float | None
    distancia_ao_furo: float | None
    dados_json: dict


def _to_float(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _inferir_litologia_raw(raw):
    value = (raw or "").strip()
    return value if value else "default"


def _parse_points_from_block_content(modelo_block):
    conteudo = modelo_block.conteudo_texto or ""
    formato = (modelo_block.formato or "").lower()
    pontos = []

    if formato == "csv":
        reader = csv.DictReader(io.StringIO(conteudo))
        for row in reader:
            x = _to_float(row.get("x"))
            y = _to_float(row.get("y"))
            z = _to_float(row.get("z"))
            if x is None or y is None or z is None:
                continue
            pontos.append(
                PontoBloco(
                    x=x,
                    y=y,
                    z=z,
                    litologia=_inferir_litologia_raw(row.get("litologia") or row.get("dominio") or row.get("domain")),
                    dureza=_to_float(row.get("dureza") or row.get("dureza_media")),
                    densidade=_to_float(row.get("densidade")),
                    teor=_to_float(row.get("teor")),
                    distancia_ao_furo=_to_float(row.get("distancia_ao_furo")),
                    dados_json={},
                )
            )
        return pontos

    if formato == "json":
        try:
            payload = json.loads(conteudo or "[]")
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, list):
            return []
        for item in payload:
            if not isinstance(item, dict):
                continue
            x = _to_float(item.get("x"))
            y = _to_float(item.get("y"))
            z = _to_float(item.get("z"))
            if x is None or y is None or z is None:
                continue
            pontos.append(
                PontoBloco(
                    x=x,
                    y=y,
                    z=z,
                    litologia=_inferir_litologia_raw(item.get("litologia") or item.get("dominio") or item.get("domain")),
                    dureza=_to_float(item.get("dureza") or item.get("dureza_media")),
                    densidade=_to_float(item.get("densidade")),
                    teor=_to_float(item.get("teor")),
                    distancia_ao_furo=_to_float(item.get("distancia_ao_furo")),
                    dados_json=item.get("dados_json") if isinstance(item.get("dados_json"), dict) else {},
                )
            )
        return pontos

    return []


def _calcular_indices_bloco(ponto: PontoBloco, modelo_block):
    sx = max(float(modelo_block.tamanho_bloco_x or 1.0), 1e-6)
    sy = max(float(modelo_block.tamanho_bloco_y or 1.0), 1e-6)
    sz = max(float(modelo_block.tamanho_bloco_z or 1.0), 1e-6)
    ox = float(modelo_block.origem_x or 0.0)
    oy = float(modelo_block.origem_y or 0.0)
    oz = float(modelo_block.origem_z or 0.0)

    ix = int(math.floor((ponto.x - ox) / sx))
    iy = int(math.floor((ponto.y - oy) / sy))
    iz = int(math.floor((ponto.z - oz) / sz))

    cx = ox + (ix + 0.5) * sx
    cy = oy + (iy + 0.5) * sy
    cz = oz + (iz + 0.5) * sz
    return ix, iy, iz, cx, cy, cz


def _inferir_celulas_vazias(celulas_map, modelo_block):
    """Preenche volume entre amostras com vizinho mais próximo em espaço de grelha."""
    if not celulas_map:
        return {}

    xs = [k[0] for k in celulas_map.keys()]
    ys = [k[1] for k in celulas_map.keys()]
    zs = [k[2] for k in celulas_map.keys()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)

    total_bbox = (max_x - min_x + 1) * (max_y - min_y + 1) * (max_z - min_z + 1)
    if total_bbox <= len(celulas_map):
        return {}
    if total_bbox > MAX_INFERRED_CELLS:
        logger.info(
            "Block model infill skipped due to bbox size: model=%s bbox=%s limit=%s",
            modelo_block.id,
            total_bbox,
            MAX_INFERRED_CELLS,
        )
        return {}

    sx = max(float(modelo_block.tamanho_bloco_x or 1.0), 1e-6)
    sy = max(float(modelo_block.tamanho_bloco_y or 1.0), 1e-6)
    sz = max(float(modelo_block.tamanho_bloco_z or 1.0), 1e-6)
    ox = float(modelo_block.origem_x or 0.0)
    oy = float(modelo_block.origem_y or 0.0)
    oz = float(modelo_block.origem_z or 0.0)

    seeds = list(celulas_map.items())
    inferred = {}

    # Etapa 1: preenchimento vertical por coluna (X,Y), entre topo/fundo observados.
    colunas = {}
    for (ix, iy, iz), seed in seeds:
        col = colunas.setdefault((ix, iy), {"zs": [], "by_z": {}})
        col["zs"].append(iz)
        col["by_z"][iz] = seed

    for (ix, iy), col in colunas.items():
        zs_col = sorted(col["zs"])
        if len(zs_col) < 2:
            continue
        z_min_col = zs_col[0]
        z_max_col = zs_col[-1]
        for iz in range(z_min_col, z_max_col + 1):
            key = (ix, iy, iz)
            if key in celulas_map or key in inferred:
                continue
            best_z = min(zs_col, key=lambda z0: abs(z0 - iz))
            dz_cells = abs(best_z - iz)
            if dz_cells > 3:
                continue
            seed = col["by_z"][best_z]
            cx = ox + (ix + 0.5) * sx
            cy = oy + (iy + 0.5) * sy
            cz = oz + (iz + 0.5) * sz
            inferred[key] = {
                "x": ix,
                "y": iy,
                "z": iz,
                "centro_x": cx,
                "centro_y": cy,
                "centro_z": cz,
                "litologia": seed.get("litologia") or "default",
                "dureza": [seed["dureza"][0]] if seed.get("dureza") else [],
                "densidade": [seed["densidade"][0]] if seed.get("densidade") else [],
                "teor": [seed["teor"][0]] if seed.get("teor") else [],
                "distancias": [dz_cells * sz],
                "dados_json": [
                    {
                        "inferred": True,
                        "mode": "vertical_column",
                        "seed_cell": {"x": ix, "y": iy, "z": best_z},
                        "neighbor_distance_cells": round(float(dz_cells), 4),
                    }
                ],
            }

    # Etapa 2: preenchimento lateral por vizinho mais próximo, com penalização de ΔZ.
    search_pool = list(celulas_map.items()) + list(inferred.items())
    for ix in range(min_x, max_x + 1):
        for iy in range(min_y, max_y + 1):
            for iz in range(min_z, max_z + 1):
                key = (ix, iy, iz)
                if key in celulas_map or key in inferred:
                    continue

                best_key = None
                best_seed = None
                best_dist = None
                for s_key, seed in search_pool:
                    dx = s_key[0] - ix
                    dy = s_key[1] - iy
                    dz = s_key[2] - iz
                    d = math.sqrt((dx * dx) + (dy * dy) + ((dz * 1.35) * (dz * 1.35)))
                    if best_dist is None or d < best_dist:
                        best_dist = d
                        best_key = s_key
                        best_seed = seed

                if best_seed is None or best_dist is None or best_dist > MAX_NEIGHBOR_DISTANCE_CELLS:
                    continue

                cx = ox + (ix + 0.5) * sx
                cy = oy + (iy + 0.5) * sy
                cz = oz + (iz + 0.5) * sz
                inferred[key] = {
                    "x": ix,
                    "y": iy,
                    "z": iz,
                    "centro_x": cx,
                    "centro_y": cy,
                    "centro_z": cz,
                    "litologia": best_seed.get("litologia") or "default",
                    "dureza": [best_seed["dureza"][0]] if best_seed.get("dureza") else [],
                    "densidade": [best_seed["densidade"][0]] if best_seed.get("densidade") else [],
                    "teor": [best_seed["teor"][0]] if best_seed.get("teor") else [],
                    "distancias": [best_dist * max(sx, sy, sz)],
                    "dados_json": [
                        {
                            "inferred": True,
                            "mode": "nearest_neighbor",
                            "seed_cell": {"x": best_key[0], "y": best_key[1], "z": best_key[2]},
                            "neighbor_distance_cells": round(best_dist, 4),
                        }
                    ],
                }
    return inferred


def atribuir_litologia_ao_bloco(bloco: BlockModelCell, medicoes):
    # Versão inicial simples: usa a litologia mais frequente nas medições próximas (quando disponível).
    if not medicoes:
        return bloco
    freq = {}
    for m in medicoes:
        key = (m.tipo_rocha or "").strip() or "default"
        freq[key] = freq.get(key, 0) + 1
    bloco.litologia = max(freq, key=freq.get) if freq else (bloco.litologia or "default")
    return bloco


@transaction.atomic
def calcular_blocos_a_partir_das_medicoes(projeto: Projeto):
    medicoes = (
        Medicao.objects.select_related("furo")
        .filter(furo__projeto=projeto)
        .order_by("furo_id", "profundidade_medida")
    )
    pontos = []
    for medicao in medicoes:
        profundidade = medicao.profundidade_medida
        if profundidade is None:
            continue
        x = medicao.longitude if medicao.longitude is not None else 0.0
        y = medicao.latitude if medicao.latitude is not None else 0.0
        z = -abs(float(profundidade))
        pontos.append(
            PontoBloco(
                x=x,
                y=y,
                z=z,
                litologia=_inferir_litologia_raw(medicao.tipo_rocha),
                dureza=_to_float(medicao.dureza),
                densidade=None,
                teor=None,
                distancia_ao_furo=0.0,
                dados_json={"medicao_id": str(medicao.id), "furo_id": str(medicao.furo_id)},
            )
        )
    return pontos


@transaction.atomic
def gerar_celulas_block_model(modelo_block: Modelo3DBlock):
    pontos = _parse_points_from_block_content(modelo_block)
    if not pontos and modelo_block.projeto_id:
        try:
            projeto = Projeto.objects.get(pk=modelo_block.projeto_id)
            pontos = calcular_blocos_a_partir_das_medicoes(projeto)
        except Projeto.DoesNotExist:
            pontos = []

    BlockModelCell.objects.filter(block_model=modelo_block).delete()
    if not pontos:
        resumo = dict(modelo_block.resumo_json or {})
        resumo["block_cells"] = 0
        modelo_block.resumo_json = resumo
        modelo_block.save(update_fields=["resumo_json", "atualizado_em"])
        return 0

    celulas_map = {}
    for ponto in pontos:
        ix, iy, iz, cx, cy, cz = _calcular_indices_bloco(ponto, modelo_block)
        key = (ix, iy, iz)
        bucket = celulas_map.setdefault(
            key,
            {
                "x": ix,
                "y": iy,
                "z": iz,
                "centro_x": cx,
                "centro_y": cy,
                "centro_z": cz,
                "litologia": {},
                "dureza": [],
                "densidade": [],
                "teor": [],
                "distancias": [],
                "dados_json": [],
            },
        )
        lit = ponto.litologia or "default"
        bucket["litologia"][lit] = bucket["litologia"].get(lit, 0) + 1
        if ponto.dureza is not None:
            bucket["dureza"].append(float(ponto.dureza))
        if ponto.densidade is not None:
            bucket["densidade"].append(float(ponto.densidade))
        if ponto.teor is not None:
            bucket["teor"].append(float(ponto.teor))
        if ponto.distancia_ao_furo is not None:
            bucket["distancias"].append(float(ponto.distancia_ao_furo))
        if ponto.dados_json:
            bucket["dados_json"].append(ponto.dados_json)

    inferred_map = _inferir_celulas_vazias(celulas_map, modelo_block)
    celulas_map.update(inferred_map)

    celulas = []
    for bucket in celulas_map.values():
        litologia = "default"
        if bucket["litologia"]:
            litologia = max(bucket["litologia"], key=bucket["litologia"].get)
        celulas.append(
            BlockModelCell(
                block_model=modelo_block,
                x=bucket["x"],
                y=bucket["y"],
                z=bucket["z"],
                centro_x=bucket["centro_x"],
                centro_y=bucket["centro_y"],
                centro_z=bucket["centro_z"],
                litologia=litologia,
                dureza_media=(sum(bucket["dureza"]) / len(bucket["dureza"])) if bucket["dureza"] else None,
                densidade=(sum(bucket["densidade"]) / len(bucket["densidade"])) if bucket["densidade"] else None,
                teor=(sum(bucket["teor"]) / len(bucket["teor"])) if bucket["teor"] else None,
                distancia_ao_furo=(sum(bucket["distancias"]) / len(bucket["distancias"])) if bucket["distancias"] else None,
                dados_json={"amostras": bucket["dados_json"][:20], "n_amostras": len(bucket["dados_json"])},
            )
        )

    BlockModelCell.objects.bulk_create(celulas, batch_size=1000)

    resumo = dict(modelo_block.resumo_json or {})
    resumo["block_cells"] = len(celulas)
    resumo["block_cells_inferred"] = len(inferred_map)
    resumo["litologias"] = sorted({c.litologia for c in celulas if c.litologia})
    sx = float(modelo_block.tamanho_bloco_x or 1.0)
    sy = float(modelo_block.tamanho_bloco_y or 1.0)
    sz = float(modelo_block.tamanho_bloco_z or 1.0)
    resumo["volume_estimado_m3"] = round(len(celulas) * sx * sy * sz, 4)
    modelo_block.resumo_json = resumo
    modelo_block.save(update_fields=["resumo_json", "atualizado_em"])
    logger.info("Block model cells generated: model=%s cells=%s", modelo_block.id, len(celulas))
    return len(celulas)


@transaction.atomic
def gerar_block_model_para_projeto(projeto_id, *, nome=None, criado_por=None, tamanho_bloco_x=1.0, tamanho_bloco_y=1.0, tamanho_bloco_z=1.0):
    projeto = Projeto.objects.select_related("empresa").get(pk=projeto_id)
    pontos = calcular_blocos_a_partir_das_medicoes(projeto)
    conteudo = json.dumps(
        [
            {
                "x": p.x,
                "y": p.y,
                "z": p.z,
                "litologia": p.litologia,
                "dureza_media": p.dureza,
                "densidade": p.densidade,
                "teor": p.teor,
                "distancia_ao_furo": p.distancia_ao_furo,
                "dados_json": p.dados_json,
            }
            for p in pontos
        ],
        ensure_ascii=False,
    )
    model = Modelo3DBlock.objects.create(
        criado_por=criado_por,
        empresa=projeto.empresa,
        projeto=projeto,
        nome=nome or f"block-model-{projeto.nome}",
        formato="json",
        conteudo_texto=conteudo,
        tamanho_bytes=len(conteudo.encode("utf-8")),
        tamanho_bloco_x=tamanho_bloco_x,
        tamanho_bloco_y=tamanho_bloco_y,
        tamanho_bloco_z=tamanho_bloco_z,
        resumo_json={"fonte": "medicoes_projeto"},
    )
    gerar_celulas_block_model(model)
    return model


def exportar_block_model_json(block_model: Modelo3DBlock):
    celulas = BlockModelCell.objects.filter(block_model=block_model).order_by("x", "y", "z")
    return {
        "block_model": {
            "id": str(block_model.id),
            "nome": block_model.nome,
            "empresa_id": str(block_model.empresa_id) if block_model.empresa_id else None,
            "projeto_id": str(block_model.projeto_id) if block_model.projeto_id else None,
            "tamanho_bloco_x": block_model.tamanho_bloco_x,
            "tamanho_bloco_y": block_model.tamanho_bloco_y,
            "tamanho_bloco_z": block_model.tamanho_bloco_z,
            "origem_x": block_model.origem_x,
            "origem_y": block_model.origem_y,
            "origem_z": block_model.origem_z,
            "resumo_json": block_model.resumo_json or {},
        },
        "cells": [
            {
                "x": c.x,
                "y": c.y,
                "z": c.z,
                "centro_x": c.centro_x,
                "centro_y": c.centro_y,
                "centro_z": c.centro_z,
                "litologia": c.litologia,
                "dureza_media": c.dureza_media,
                "densidade": c.densidade,
                "teor": c.teor,
                "distancia_ao_furo": c.distancia_ao_furo,
                "dados_json": c.dados_json or {},
            }
            for c in celulas
        ],
    }
