import logging
import math
import csv
import io
import json
import zipfile

import plotly.graph_objects as go
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ..decorators import admin_required, empregado_required
from ..forms.furo import FuroCreateForm, FuroForm
from ..models.empregado import Empregados
from ..models.furo import Furo
from ..models.importacao_furo_3d import ImportacaoFuro3DExterna
from ..models.medicao import Medicao
from ..models.registo import RegistoDiarioEmpregado
from ..models.despesa import Despesa
from ..models.material import Material
from ..models.maquina import Maquina
from ..models.empregado_furo import EmpregadoFuro
from ..models.configuracao_perfuracao import ConfiguracaoPerfuracaoEmpregado
from ..utils.tragetoria import calcular_linha_planeada, construir_segmentos_tubos
from projetos.selectors.furos import (
    obter_contexto_detalhe_furo,
    obter_equipa_e_configuracao_por_furo,
    obter_furo,
    obter_lista_furos,
)
from projetos.services.furos import criar_furo
from projetos.utils.tragetoria import calcular_trajetoria_min_curv

from geologia.models import LogGeologicoFuro, MissaoDroneFuro
from plataforma.models import PerfilPlataforma

logger = logging.getLogger("core")



ADMIN_TIPOS_ACESSO_EMPRESA = ["empresa_admin", "empresa_gestor"]


def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


def _medicoes_ordenadas_furo(furo):
    return list(furo.medicoes.filter(empresa_id=furo.empresa_id).order_by("profundidade_medida"))


def _origem_furo(furo):
    return (
        float(furo.origem_este or 0.0),
        float(furo.origem_norte or 0.0),
        float(furo.origem_tvd or 0.0),
    )


def _profundidade_planeada_final(furo):
    return float(
        furo.profundidade_alvo_atual
        or furo.profundidade_alvo_inicial
        or furo.profundidade_maxima_atingida
        or furo.profundidade_atual
        or 0.0
    )


def _orientacao_planeada_furo(furo):
    return (
        float(furo.inclinacao_planeada_atual or furo.inclinacao_planeada_inicial or 0.0),
        float(furo.azimute_planeado_atual or furo.azimute_planeado_inicial or 0.0),
    )


def _obter_configuracao_visual_furo(furo):
    return (
        ConfiguracaoPerfuracaoEmpregado.objects
        .filter(furo=furo, empresa_id=furo.empresa_id)
        .order_by("-atualizado_em", "-pk")
        .first()
    )


def _linha_tracejada_3d(linha, dash_size=1, gap_size=24):
    x_vals = linha.get("x") or []
    y_vals = linha.get("y") or []
    z_vals = linha.get("z") or []

    if len(x_vals) <= 1:
        return {"x": list(x_vals), "y": list(y_vals), "z": list(z_vals)}

    traced_x = []
    traced_y = []
    traced_z = []

    segment_index = 0
    points_in_segment = max(1, int(dash_size))
    points_in_gap = max(1, int(gap_size))

    while segment_index < len(x_vals) - 1:
        end_index = min(segment_index + points_in_segment, len(x_vals) - 1)
        for idx in range(segment_index, end_index + 1):
            traced_x.append(x_vals[idx])
            traced_y.append(y_vals[idx])
            traced_z.append(z_vals[idx])
        traced_x.append(None)
        traced_y.append(None)
        traced_z.append(None)
        segment_index = end_index + points_in_gap

    return {"x": traced_x, "y": traced_y, "z": traced_z}


def _tracos_tracejados_3d(linha, nome, cor_linha, cor_marcador, largura=4, marcador=2):
    x_vals = linha.get("x") or []
    y_vals = linha.get("y") or []
    z_vals = linha.get("z") or []
    custom_vals = linha.get("customdata") or []

    traces = []
    current_x = []
    current_y = []
    current_z = []
    current_custom = []

    for idx, x_val in enumerate(x_vals):
        if x_val is None:
            if current_x:
                traces.append(
                    go.Scatter3d(
                        x=current_x,
                        y=current_y,
                        z=current_z,
                        customdata=current_custom if current_custom else None,
                        mode="lines",
                        name=nome,
                        line=dict(width=largura, color=cor_linha),
                        showlegend=len(traces) == 0,
                    )
                )
                current_x, current_y, current_z, current_custom = [], [], [], []
            continue

        current_x.append(x_val)
        current_y.append(y_vals[idx])
        current_z.append(z_vals[idx])
        if idx < len(custom_vals):
            current_custom.append(custom_vals[idx])

    if current_x:
        traces.append(
            go.Scatter3d(
                x=current_x,
                y=current_y,
                z=current_z,
                customdata=current_custom if current_custom else None,
                mode="lines",
                name=nome,
                line=dict(width=largura, color=cor_linha),
                showlegend=len(traces) == 0,
            )
        )

    return traces


def _tracos_vetores_direcao_3d(x_vals, y_vals, z_vals, passo):
    vx = []
    vy = []
    vz = []

    for i in range(1, len(x_vals)):
        if passo > 1 and i % passo != 0 and i != len(x_vals) - 1:
            continue

        vx.extend([x_vals[i - 1], x_vals[i], None])
        vy.extend([y_vals[i - 1], y_vals[i], None])
        vz.extend([z_vals[i - 1], z_vals[i], None])

    if not vx:
        return []

    return [
        go.Scatter3d(
            x=vx,
            y=vy,
            z=vz,
            mode="lines+markers",
            name="Vetores de direção",
            line=dict(width=6, color="#38bdf8"),
            marker=dict(size=4, color="#7dd3fc", opacity=0.95),
            hoverinfo="skip",
            legendgroup="vetores-direcao",
            showlegend=True,
        )
    ]


def _tracos_juntas_tubo_3d(juntas, segmentos, tamanho=1.1):
    if not juntas or not segmentos:
        return []

    traces = []

    for junta in juntas:
        idx_segmento = int(junta.get("indice", 0) or 0)
        segmento = segmentos[min(max(idx_segmento, 0), len(segmentos) - 1)]
        (x0, y0, z0) = segmento["inicio"]
        (x1, y1, z1) = segmento["fim"]
        px, py, pz = junta["ponto"]

        dx = float(x1 - x0)
        dy = float(y1 - y0)
        dz = float(z1 - z0)

        perp_x = dy
        perp_y = -dx
        perp_z = 0.0
        perp_norm = math.sqrt((perp_x ** 2) + (perp_y ** 2) + (perp_z ** 2))

        if perp_norm < 1e-6:
            perp_x = -dz
            perp_y = 0.0
            perp_z = dx
            perp_norm = math.sqrt((perp_x ** 2) + (perp_y ** 2) + (perp_z ** 2))

        if perp_norm < 1e-6:
            perp_x, perp_y, perp_z = 1.0, 0.0, 0.0
            perp_norm = 1.0

        factor = float(tamanho) / perp_norm
        off_x = perp_x * factor * 0.5
        off_y = perp_y * factor * 0.5
        off_z = perp_z * factor * 0.5

        md = float(junta.get("md", 0.0) or 0.0)
        rotulo_atual = junta.get("rotulo_atual") or "Tubo"
        rotulo_proximo = junta.get("rotulo_proximo") or "Tubo"

        traces.append(
            go.Scatter3d(
                x=[px - off_x, px + off_x],
                y=[py - off_y, py + off_y],
                z=[pz - off_z, pz + off_z],
                mode="lines",
                name="Tubo do furo",
                line=dict(width=9, color="#ffffff"),
                customdata=[[md], [md]],
                hovertemplate=(
                    "Conexão entre tubos<br>"
                    f"Medida do furo neste ponto: {md:.2f} m<br>"
                    f"Conexão entre {rotulo_atual} e {rotulo_proximo}<br>"
                    "Este: %{x:.2f} m<br>"
                    "Norte: %{y:.2f} m<br>"
                    "TVD: %{z:.2f} m<br>"
                    "<extra></extra>"
                ),
                showlegend=False,
            )
        )

    return traces


def _dados_exportacao_furo_3d(furo):
    medicoes = _medicoes_ordenadas_furo(furo)
    origem = _origem_furo(furo)
    profundidade_planeada = _profundidade_planeada_final(furo)
    inclinacao_planeada, azimute_planeado = _orientacao_planeada_furo(furo)
    linha_planeada = calcular_linha_planeada(
        origem=origem,
        inclinacao=inclinacao_planeada,
        azimute=azimute_planeado,
        comprimento=profundidade_planeada,
    )

    real_points = []
    if medicoes:
        pontos, doglegs, alertas = calcular_trajetoria_min_curv(medicoes, origem=origem)
        for idx, medicao in enumerate(medicoes, start=1):
            x, y, z = pontos[idx]
            real_points.append(
                {
                    "md": float(medicao.profundidade_medida or 0.0),
                    "inclination": float(medicao.inclinacao_real_medida or 0.0),
                    "azimuth": float(medicao.azimute_real_medido or 0.0),
                    "dogleg": float(doglegs[idx] if idx < len(doglegs) else 0.0),
                    "status": alertas[idx] if idx < len(alertas) else "OK",
                    "x": float(x),
                    "y": float(y),
                    "z": float(z),
                }
            )

    planned_points = []
    for idx, x in enumerate(linha_planeada["x"]):
        planned_points.append(
            {
                "index": idx,
                "x": float(x),
                "y": float(linha_planeada["y"][idx]),
                "z": float(linha_planeada["z"][idx]),
            }
        )

    return {
        "furo": {
            "id": str(furo.pk),
            "nome": furo.nome,
            "projeto": furo.projeto.nome if furo.projeto_id else "",
            "origem_este": origem[0],
            "origem_norte": origem[1],
            "origem_tvd": origem[2],
            "profundidade_alvo": profundidade_planeada,
            "inclinacao_planeada": inclinacao_planeada,
            "azimute_planeado": azimute_planeado,
        },
        "real_points": real_points,
        "planned_points": planned_points,
    }


def _renderizar_furo_3d_csv(payload):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["track", "md", "inclination", "azimuth", "dogleg", "status", "x", "y", "z"])
    for point in payload["real_points"]:
        writer.writerow([
            "real",
            point["md"],
            point["inclination"],
            point["azimuth"],
            point["dogleg"],
            point["status"],
            point["x"],
            point["y"],
            point["z"],
        ])
    for point in payload["planned_points"]:
        writer.writerow([
            "planned",
            "",
            payload["furo"]["inclinacao_planeada"],
            payload["furo"]["azimute_planeado"],
            "",
            "",
            point["x"],
            point["y"],
            point["z"],
        ])
    return output.getvalue()


def _renderizar_furo_3d_geojson(payload):
    return json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "name": payload["furo"]["nome"],
                        "track": "real",
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[p["x"], p["y"], p["z"]] for p in payload["real_points"]],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {
                        "name": payload["furo"]["nome"],
                        "track": "planned",
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[p["x"], p["y"], p["z"]] for p in payload["planned_points"]],
                    },
                },
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


def _dados_completos_furo(furo):
    payload_3d = _dados_exportacao_furo_3d(furo)
    return {
        "furo": payload_3d["furo"],
        "planeado": payload_3d["planned_points"],
        "trajetoria_real": payload_3d["real_points"],
        "medicoes": [
            {
                "id": str(m.pk),
                "profundidade_medida": m.profundidade_medida,
                "inclinacao_real_medida": m.inclinacao_real_medida,
                "azimute_real_medido": m.azimute_real_medido,
                "magnetismo": m.magnetismo,
                "tipo_rocha": m.tipo_rocha,
                "criado_em": m.criado_em.isoformat() if m.criado_em else "",
            }
            for m in _medicoes_ordenadas_furo(furo)
        ],
        "registos": [
            {
                "id": str(r.pk),
                "data": r.data.isoformat() if r.data else "",
                "empregado": r.empregado.nome if r.empregado_id else "",
                "metros_furados": r.metros_furados,
                "horas_trabalhadas": r.horas_trabalhadas,
                "observacoes": r.observacoes,
            }
            for r in RegistoDiarioEmpregado.objects.filter(furo=furo, empresa_id=furo.empresa_id).select_related("empregado").order_by("-data")
        ],
        "materiais": [
            {
                "id": str(material.pk),
                "nome": material.nome,
                "tipo": material.tipo,
                "quantidade": material.quantidade,
                "valor": material.valor,
            }
            for material in Material.objects.filter(furo=furo, empresa_id=furo.empresa_id).order_by("nome")
        ],
        "maquinas": [
            {
                "id": str(maquina.pk),
                "nome": maquina.nome,
                "tipo": maquina.tipo,
                "estado": maquina.estado,
                "horimetro": maquina.horimetro,
            }
            for maquina in Maquina.objects.filter(furos=furo, empresa_id=furo.empresa_id).distinct().order_by("nome")
        ],
        "empregados": [
            {
                "id": str(ligacao.empregado.pk),
                "nome": ligacao.empregado.nome,
                "funcao": ligacao.empregado.funcao,
                "data_inicio": ligacao.data_inicio.isoformat() if ligacao.data_inicio else "",
                "data_fim": ligacao.data_fim.isoformat() if ligacao.data_fim else "",
                "ativo": ligacao.ativo,
            }
            for ligacao in EmpregadoFuro.objects.filter(furo=furo, empresa_id=furo.empresa_id).select_related("empregado").order_by("-ativo", "data_inicio")
        ],
        "despesas": [
            {
                "id": str(d.pk),
                "data": d.data.isoformat() if d.data else "",
                "categoria": d.categoria,
                "tipo": d.tipo,
                "descricao": d.descricao,
                "valor": d.valor,
            }
            for d in Despesa.objects.filter(furo=furo, empresa_id=furo.empresa_id).order_by("-data")
        ],
    }


def _parse_imported_3d_file(uploaded_file):
    nome = (uploaded_file.name or "").lower()
    raw = uploaded_file.read()
    text = raw.decode("utf-8", errors="ignore")

    if nome.endswith(".json") or nome.endswith(".geojson"):
        data = json.loads(text)
        if data.get("type") == "FeatureCollection":
            for feature in data.get("features", []):
                geometry = feature.get("geometry") or {}
                if geometry.get("type") == "LineString":
                    coords = geometry.get("coordinates") or []
                    return {
                        "name": feature.get("properties", {}).get("name") or uploaded_file.name,
                        "x": [float(c[0]) for c in coords],
                        "y": [float(c[1]) for c in coords],
                        "z": [float(c[2]) for c in coords],
                    }
        if isinstance(data, dict) and "points" in data:
            points = data.get("points") or []
            return {
                "name": data.get("name") or uploaded_file.name,
                "x": [float(p.get("x", 0)) for p in points],
                "y": [float(p.get("y", 0)) for p in points],
                "z": [float(p.get("z", 0)) for p in points],
            }
        raise ValueError("JSON/GeoJSON sem estrutura reconhecida para trajetória 3D.")

    if nome.endswith(".csv"):
        reader = csv.DictReader(io.StringIO(text))
        x, y, z = [], [], []
        for row in reader:
            x.append(float(row.get("x", 0) or 0))
            y.append(float(row.get("y", 0) or 0))
            z.append(float(row.get("z", 0) or 0))
        if not x:
            raise ValueError("CSV sem pontos válidos.")
        return {
            "name": uploaded_file.name,
            "x": x,
            "y": y,
            "z": z,
        }

    raise ValueError("Formato não suportado. Usa CSV, JSON ou GeoJSON.")


# ---------------- HELPERS ----------------
def _obter_contexto_admin_furos(request):
    logger.debug(
        "A resolver contexto administrativo em furos.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    perfil = PerfilPlataforma.objects.filter(
        user=request.user,
        ativo=True,
        tipo_acesso__in=ADMIN_TIPOS_ACESSO_EMPRESA,
    ).select_related("empresa").first()
    if perfil:
        logger.info(
            "Contexto administrativo resolvido via PerfilPlataforma em furos.py. user_id=%s, empresa_id=%s, tipo_acesso=%s",
            request.user.id,
            perfil.empresa_id,
            perfil.tipo_acesso,
        )
        return perfil

    logger.warning(
        "Falha ao resolver contexto administrativo em furos.py. user_id=%s",
        request.user.id,
    )
    return None



def _obter_empresa_admin_furos(request):
    contexto_admin = _obter_contexto_admin_furos(request)
    if not contexto_admin:
        messages.error(request, "Não tens permissão para aceder a esta área.")
        return None, redirect("projetos:redirect_after_login")

    empresa = getattr(contexto_admin, "empresa", None)
    empresa_id = getattr(contexto_admin, "empresa_id", None)

    if not empresa_id or not empresa:
        logger.warning(
            "Contexto administrativo sem empresa em furos.py. user_id=%s",
            request.user.id,
        )
        messages.error(request, "O utilizador administrador não está associado a uma empresa.")
        return None, redirect("projetos:dashboard")

    return empresa, None



def _obter_empregado_autenticado_furos(request):
    logger.debug(
        "A resolver empregado autenticado em furos.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    empregado = Empregados.objects.filter(user=request.user).select_related("empresa").first()
    if not empregado:
        logger.warning(
            "Utilizador autenticado sem registo em Empregados em furos.py. user_id=%s",
            request.user.id,
        )
        messages.error(
            request,
            "A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        )
        return None, redirect("projetos:redirect_after_login")

    if not empregado.empresa_id:
        logger.warning(
            "Empregado sem empresa associada em furos.py. user_id=%s, empregado_id=%s",
            request.user.id,
            empregado.id,
        )
        messages.error(request, "A tua conta não está associada a uma empresa. Contacta o administrador.")
        return None, redirect("projetos:redirect_after_login")

    return empregado, None



# ---------------- FUROS ----------------
@login_required
@empregado_required
def furo_detail_empregado(request, pk):
    logger.info(
        "Entrada na view furo_detail_empregado. user_id=%s, username='%s', furo_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_furos(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_detail_empregado. user_id=%s", request.user.id)
        return resposta_erro

    furo = get_object_or_404(Furo, pk=pk, empresa_id=empregado.empresa_id)

    trabalhou_no_furo = empregado.registos_diarios.filter(
        furo=furo,
        empresa_id=empregado.empresa_id,
    ).exists()
    if not trabalhou_no_furo:
        logger.warning(
            "Empregado sem permissão para furo_detail_empregado em furos.py. user_id=%s, empregado_id=%s, furo_id=%s",
            request.user.id,
            empregado.id,
            furo.id,
        )
        messages.error(request, "Não tens permissão para ver os detalhes deste furo.")
        return redirect("projetos:area_empregado")

    registos_furo = (
        RegistoDiarioEmpregado.objects
        .filter(furo=furo, empresa_id=empregado.empresa_id)
        .select_related("empregado", "projeto", "furo")
        .order_by("-data", "-criado_em")
    )

    medicoes_furo = (
        Medicao.objects
        .filter(furo=furo, empresa_id=empregado.empresa_id)
        .order_by("-criado_em", "-profundidade_medida")
    )

    logger.info(
        "View furo_detail_empregado carregada com sucesso em furos.py. user_id=%s, empregado_id=%s, furo_id=%s",
        request.user.id,
        empregado.id,
        furo.id,
    )
    return render(request, "projetos/furo_detail_empregado.html", {
        "empregado": empregado,
        "furo": furo,
        "registos_furo": registos_furo,
        "medicoes_furo": medicoes_furo,
    })



@login_required
@admin_required
def furo_create(request):
    logger.info(
        "Entrada na view furo_create. user_id=%s, username='%s', method=%s",
        request.user.id,
        request.user.username,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_create. user_id=%s", request.user.id)
        return resposta_erro

    if request.method == "POST":
        form = FuroCreateForm(request.POST, empresa=empresa_id)
        if form.is_valid():
            furo = criar_furo(form, empresa=empresa_id)
            logger.info(
                "Furo criado com sucesso. user_id=%s, empresa_id=%s, furo_id=%s",
                request.user.id,
                empresa.id,
                furo.pk,
            )
            messages.success(request, "Furo criado com sucesso.")
            return redirect(reverse("projetos:furo_detail", kwargs={"pk": furo.pk}))

        logger.warning(
            "Erro ao criar furo. user_id=%s, erros=%s",
            request.user.id,
            form.errors,
        )
        messages.error(request, "Erro ao criar o furo. Verifique os dados.")
    else:
        form = FuroCreateForm(empresa=empresa_id)

    return render(request, "projetos/form.html", {
        "form": form,
        "titulo": "Criar Novo Furo",
    })


@login_required
@admin_required
def furo_detail(request, pk):
    logger.info(
        "Entrada na view furo_detail. user_id=%s, username='%s', furo_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empresa, resposta_erro = _obter_empresa_admin_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_detail. user_id=%s", request.user.id)
        return resposta_erro

    context = obter_contexto_detalhe_furo(pk, empresa=empresa_id)
    furo = context["furo"]
    context["configuracoes"] = obter_equipa_e_configuracao_por_furo(
        furo,
        empresa=empresa_id,
    )
    context["logs_geologicos_recentes"] = (
        LogGeologicoFuro.objects.filter(furo=furo, empresa_id=empresa_id)
        .select_related("missao_drone", "medicao")
        .order_by("-data_registo", "-criado_em")[:5]
    )
    context["missoes_drone_recentes"] = (
        MissaoDroneFuro.objects.filter(furo=furo, empresa_id=empresa_id)
        .order_by("-data_voo", "-criado_em")[:3]
    )

    logger.info(
        "View furo_detail carregada com sucesso. user_id=%s, empresa_id=%s, furo_id=%s",
        request.user.id,
        empresa.id,
        furo.pk,
    )
    return render(request, "projetos/furo_detail.html", context)

# Multiempresa: o administrador só pode listar e gerir furos da sua própria empresa.
@login_required
@admin_required
def furo_list(request):
    logger.info(
        "Entrada na view furo_list. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empresa, resposta_erro = _obter_empresa_admin_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_list. user_id=%s", request.user.id)
        return resposta_erro

    furos = obter_lista_furos(empresa=empresa_id)
    logger.info(
        "View furo_list carregada com sucesso. user_id=%s, empresa_id=%s, total_furos=%s",
        request.user.id,
        empresa.id,
        furos.count() if hasattr(furos, "count") else "n/a",
    )
    return render(request, "projetos/furo_list.html", {"furos": furos})




@login_required
@admin_required
def furo_update(request, pk):
    logger.info(
        "Entrada na view furo_update. user_id=%s, username='%s', furo_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_update. user_id=%s", request.user.id)
        return resposta_erro

    furo = get_object_or_404(Furo, pk=pk, empresa_id=empresa_id)

    if request.method == "POST":
        form = FuroForm(request.POST, instance=furo, empresa=empresa_id)
        if form.is_valid():
            furo = form.save(commit=False)
            furo.empresa_id = empresa_id

            if furo.profundidade_atual and furo.profundidade_maxima_atingida:
                if furo.profundidade_atual > furo.profundidade_maxima_atingida:
                    furo.profundidade_maxima_atingida = furo.profundidade_atual

            if not furo.medicoes.exists():
                furo.profundidade_atual = 0.0
                furo.profundidade_maxima_atingida = 0.0

            furo.origem_este = furo.origem_este or 0.0
            furo.origem_norte = furo.origem_norte or 0.0
            furo.origem_tvd = furo.origem_tvd or 0.0

            furo.save()

            logger.info(
                "Furo atualizado com sucesso. user_id=%s, empresa_id=%s, furo_id=%s",
                request.user.id,
                empresa.id,
                furo.pk,
            )
            messages.success(request, "Furo atualizado com sucesso.")
            return redirect(reverse("projetos:furo_detail", kwargs={"pk": furo.pk}))

        logger.warning(
            "Erro ao atualizar furo. user_id=%s, furo_pk=%s, erros=%s",
            request.user.id,
            pk,
            form.errors,
        )
        messages.error(request, "Erro ao atualizar o furo. Verifique os dados.")
    else:
        form = FuroForm(instance=furo, empresa=empresa_id)

    return render(request, "projetos/furo_update.html", {
        "form": form,
        "furo": furo,
    })



@login_required
@admin_required
def furo_delete(request, pk):
    logger.info(
        "Entrada na view furo_delete. user_id=%s, username='%s', furo_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_delete. user_id=%s", request.user.id)
        return resposta_erro

    furo = get_object_or_404(Furo, pk=pk, empresa_id=empresa_id)
    if request.method == "POST":
        furo_id = furo.pk
        furo.delete()
        logger.info(
            "Furo apagado com sucesso. user_id=%s, empresa_id=%s, furo_id=%s",
            request.user.id,
            empresa.id,
            furo_id,
        )
        messages.success(request, "Furo apagado com sucesso.")
        return redirect(reverse("projetos:furo_list"))

    return render(request, "projetos/furo_confirm_delete.html", {"furo": furo})



@login_required
def furo_3d_geologico(request, furo_id):
    logger.info(
        "Entrada na view furo_3d_geologico. user_id=%s, username='%s', furo_id=%s",
        request.user.id,
        request.user.username,
        furo_id,
    )
    furo = None

    contexto_admin = _obter_contexto_admin_furos(request)
    if contexto_admin:
        empresa = getattr(contexto_admin, "empresa", None)
        empresa_id = getattr(contexto_admin, "empresa_id", None)

        if not empresa_id or not empresa:
            logger.warning(
                "Contexto administrativo sem empresa em furo_3d_geologico. user_id=%s",
                request.user.id,
            )
            messages.error(request, "O utilizador administrador não está associado a uma empresa.")
            return redirect("projetos:dashboard")

        furo = obter_furo(furo_id, empresa=empresa_id)
    else:
        empregado, resposta_erro = _obter_empregado_autenticado_furos(request)
        if resposta_erro:
            logger.warning("Acesso bloqueado na view furo_3d_geologico. user_id=%s", request.user.id)
            return resposta_erro

        furo = obter_furo(furo_id, empresa=empregado.empresa_id)

        trabalhou_no_furo = RegistoDiarioEmpregado.objects.filter(
            empregado=empregado,
            furo=furo,
            empresa_id=empregado.empresa_id,
        ).exists()

        if not trabalhou_no_furo:
            logger.warning(
                "Empregado sem permissão para furo_3d_geologico. user_id=%s, empregado_id=%s, furo_id=%s",
                request.user.id,
                empregado.id,
                furo.id,
            )
            messages.error(request, "Não tens permissão para ver o 3D deste furo.")
            return redirect("projetos:area_empregado")

    medicoes = _medicoes_ordenadas_furo(furo)

    origem = _origem_furo(furo)

    profundidade_planeada_final = _profundidade_planeada_final(furo)

    inclinacao_planeada, azimute_planeado = _orientacao_planeada_furo(furo)

    if not medicoes:
        linha_planeada_final = calcular_linha_planeada(
            origem=origem,
            inclinacao=inclinacao_planeada,
            azimute=azimute_planeado,
            comprimento=profundidade_planeada_final,
        )
        linha_planeada_final_tracejada = _linha_tracejada_3d(linha_planeada_final)

        linha_planeada_final_tracejada["customdata"] = [
            [float(profundidade_planeada_final or 0.0)] if linha_planeada_final_tracejada["x"][idx] is not None else None
            for idx in range(len(linha_planeada_final_tracejada["x"]))
        ]
        trace_planeado = _tracos_tracejados_3d(
            linha_planeada_final_tracejada,
            "Trajetória planeada",
            "#f97316",
            "#fb923c",
            largura=8,
            marcador=3,
        )
        for trace in trace_planeado:
            trace.hovertemplate = (
                "Trajetória planeada<br>"
                f"MD alvo: {profundidade_planeada_final:.2f} m<br>"
                "Este: %{x:.2f} m<br>"
                "Norte: %{y:.2f} m<br>"
                "TVD: %{z:.2f} m<br>"
                "<extra></extra>"
            )

        trace_origem = go.Scatter3d(
            x=[origem[0]],
            y=[origem[1]],
            z=[origem[2]],
            mode="markers",
            name="Origem",
            marker=dict(size=7, color="green"),
            hovertemplate=(
                "Origem do furo<br>"
                "Este: %{x:.2f} m<br>"
                "Norte: %{y:.2f} m<br>"
                "TVD: %{z:.2f} m<br>"
                "<extra></extra>"
            ),
        )

        fig = go.Figure(data=trace_planeado + [trace_origem])
        fig.update_layout(
            scene=dict(
                xaxis_title="Este (m)",
                yaxis_title="Norte (m)",
                zaxis_title="TVD / Profundidade Vertical (m)",
                zaxis=dict(autorange="reversed"),
                aspectmode="manual",
                aspectratio=dict(x=1, y=1, z=0.7),
                camera=dict(
                    eye=dict(x=1.8, y=1.8, z=1.2),
                ),
            ),
            legend=dict(
                orientation="v",
                yanchor="top",
                y=0.95,
                xanchor="left",
                x=1.02,
                bgcolor="rgba(255,255,255,0.85)",
                bordercolor="lightgray",
                borderwidth=1,
                font=dict(size=11),
            ),
            margin=dict(l=0, r=140, t=20, b=0),
            height=800,
        )
        graph = fig.to_html(
            full_html=False,
            config={
                "responsive": True,
                "displaylogo": False,
                "scrollZoom": True,
                "plotGlPixelRatio": 1.5,
            },
        )

        logger.info(
            "Furo sem medições em furo_3d_geologico. user_id=%s, furo_id=%s",
            request.user.id,
            furo.id,
        )
        messages.warning(request, "Este furo ainda não possui medições.")
        return render(request, "projetos/furo_3d.html", {
            "furo": furo,
            "graph": graph,
            "numero_medicoes": 0,
            "profundidade_final": 0.0,
            "profundidade_visual_max": profundidade_planeada_final or 0.0,
            "dogleg_max": 0.0,
            "estado_max": "OK",
        })

    pontos, doglegs, alertas = calcular_trajetoria_min_curv(
        medicoes,
        origem=origem,
    )

    ultima_md = float(medicoes[-1].profundidade_medida or 0.0)

    linha_planeada_atual = calcular_linha_planeada(
        origem=origem,
        inclinacao=inclinacao_planeada,
        azimute=azimute_planeado,
        comprimento=ultima_md,
    )
    linha_planeada_atual_tracejada = _linha_tracejada_3d(linha_planeada_atual)

    linha_planeada_final = calcular_linha_planeada(
        origem=origem,
        inclinacao=inclinacao_planeada,
        azimute=azimute_planeado,
        comprimento=profundidade_planeada_final,
    )

    x, y, z = [], [], []
    customdata = []
    configuracao_visual = _obter_configuracao_visual_furo(furo)

    if pontos:
        x.append(pontos[0][0])
        y.append(pontos[0][1])
        z.append(pontos[0][2])
        customdata.append([0.0, 0.0, 0.0, 0.0, None, "ORIGEM"])

    total_pontos_medicoes = min(len(medicoes), max(len(pontos) - 1, 0))

    for idx in range(total_pontos_medicoes):
        med = medicoes[idx]
        x_coord, y_coord, z_coord = pontos[idx + 1]

        prof = float(med.profundidade_medida or 0.0)
        incl = float(med.inclinacao_real_medida or 0.0)
        azim = float(med.azimute_real_medido or 0.0)
        mag = float(med.magnetismo or 0.0)
        img_url = med.imagem.url if med.imagem else None
        estado = alertas[idx + 1] if idx + 1 < len(alertas) else "OK"

        x.append(x_coord)
        y.append(y_coord)
        z.append(z_coord)

        customdata.append([
            prof,
            incl,
            azim,
            mag,
            img_url,
            estado,
        ])

    cores_pontos = [0.0]
    for idx in range(total_pontos_medicoes):
        if idx + 1 < len(doglegs):
            cores_pontos.append(doglegs[idx + 1])
        else:
            cores_pontos.append(0.0)

    passo_setas = 1
    seta_tracos = _tracos_vetores_direcao_3d(x, y, z, passo_setas)

    mds_path = [float(item[0] or 0.0) for item in customdata]
    segmentos_tubo = construir_segmentos_tubos(
        pontos=list(zip(x, y, z)),
        mds=mds_path,
        comprimento_frontal=(
            getattr(configuracao_visual, "comprimento_total_conjunto_fundo", 0.0)
            if configuracao_visual else 0.0
        ),
        comprimento_padrao=(
            float(getattr(configuracao_visual, "comprimento_tubo", 3.0) or 3.0)
            if configuracao_visual else 3.0
        ),
        total_md=mds_path[-1] if mds_path else 0.0,
    )

    tubo_tracos = []
    for idx, segmento in enumerate(segmentos_tubo["segmentos"]):
        (x0, y0, z0) = segmento["inicio"]
        (x1, y1, z1) = segmento["fim"]
        if segmento["tipo"] == "frontal":
            cor_segmento = "#f59e0b"
            largura_segmento = 12
            hover_titulo = "Conjunto de fundo"
            hover_extra = (
                f"Comprimento do conjunto de fundo: "
                f"{segmento['fim_md'] - segmento['inicio_md']:.2f} m<br>"
            )
        else:
            cor_segmento = "#38bdf8" if idx % 2 == 0 else "#0ea5e9"
            largura_segmento = 9
            hover_titulo = segmento.get("rotulo") or "Tubo do furo"
            hover_extra = (
                f"{segmento.get('rotulo') or 'Tubo'}<br>"
                f"Troço do tubo: {segmento['inicio_md']:.2f} m → {segmento['fim_md']:.2f} m<br>"
            )

        tubo_tracos.append(
            go.Scatter3d(
                x=[x0, x1],
                y=[y0, y1],
                z=[z0, z1],
                mode="lines",
                name="Tubo do furo",
                line=dict(width=largura_segmento, color=cor_segmento),
                customdata=[
                    [segmento["inicio_md"], segmento.get("tubo_numero") or 0],
                    [segmento["fim_md"], segmento.get("tubo_numero") or 0],
                ],
                hovertemplate=(
                    f"{hover_titulo}<br>"
                    f"{hover_extra}"
                    "Medida do furo neste ponto: %{customdata[0]:.2f} m<br>"
                    "Este: %{x:.2f} m<br>"
                    "Norte: %{y:.2f} m<br>"
                    "TVD: %{z:.2f} m<br>"
                    "<extra></extra>"
                ),
                showlegend=idx == 0,
            )
        )

    if segmentos_tubo["juntas"]:
        tubo_tracos.extend(
            _tracos_juntas_tubo_3d(
                segmentos_tubo["juntas"],
                segmentos_tubo["segmentos"],
                tamanho=1.25,
            )
        )

    scatter = go.Scatter3d(
        x=x,
        y=y,
        z=z,
        mode="lines+markers",
        line=dict(width=5, color="blue"),
        marker=dict(
            size=12,
            color=cores_pontos,
            colorscale=[
                [0, "green"],
                [0.5, "yellow"],
                [1, "red"],
            ],
            colorbar=dict(
                title="Dogleg",
                len=0.6,
                thickness=12,
                x=1.08,
                y=0.45,
            ),
            showscale=True,
        ),
        customdata=customdata,
        hovertemplate=(
            "Trajetória real<br>"
            "MD: %{customdata[0]:.2f} m<br>"
            "Inclinação: %{customdata[1]:.2f}°<br>"
            "Azimute: %{customdata[2]:.2f}°<br>"
            "Magnetismo: %{customdata[3]:.2f}<br>"
            "Estado: %{customdata[5]}<br>"
            "Este: %{x:.2f} m<br>"
            "Norte: %{y:.2f} m<br>"
            "TVD: %{z:.2f} m<br>"
            "<extra></extra>"
        ),
        name="Trajetória real",
    )

    linha_planeada_atual_tracejada["customdata"] = [
        [((ultima_md / max(len(linha_planeada_atual["x"]) - 1, 1)) * idx)] if linha_planeada_atual_tracejada["x"][idx] is not None else None
        for idx in range(len(linha_planeada_atual_tracejada["x"]))
    ]
    planeado_ultima_traces = _tracos_tracejados_3d(
        linha_planeada_atual_tracejada,
        "Planeado até última medição",
        "#f97316",
        "#fb923c",
        largura=7,
        marcador=3,
    )
    for trace in planeado_ultima_traces:
        trace.hovertemplate = (
            "Trajetória planeada<br>"
            f"Até última medição<br>"
            f"MD alvo: {ultima_md:.2f} m<br>"
            "Este: %{x:.2f} m<br>"
            "Norte: %{y:.2f} m<br>"
            "TVD: %{z:.2f} m<br>"
            "<extra></extra>"
        )

    inicio_final_idx = 0
    if profundidade_planeada_final > 0:
        inicio_final_idx = max(
            0,
            min(
                len(linha_planeada_final["x"]) - 1,
                int(round((ultima_md / profundidade_planeada_final) * max(len(linha_planeada_final["x"]) - 1, 0))),
            ),
        )

    linha_planeada_final_segmento = {
        "x": linha_planeada_final["x"][inicio_final_idx:],
        "y": linha_planeada_final["y"][inicio_final_idx:],
        "z": linha_planeada_final["z"][inicio_final_idx:],
    }
    linha_planeada_final_segmento_tracejada = _linha_tracejada_3d(linha_planeada_final_segmento)

    planeado_final_customdata = []
    total_segmento = max(len(linha_planeada_final_segmento["x"]) - 1, 1)
    for idx in range(len(linha_planeada_final_segmento["x"])):
        if profundidade_planeada_final <= ultima_md:
            md_value = profundidade_planeada_final
        else:
            md_value = ultima_md + (((profundidade_planeada_final - ultima_md) / total_segmento) * idx)
        planeado_final_customdata.append([md_value])

    linha_planeada_final_segmento_tracejada["customdata"] = [
        planeado_final_customdata[idx] if idx < len(planeado_final_customdata) and linha_planeada_final_segmento_tracejada["x"][idx] is not None else None
        for idx in range(len(linha_planeada_final_segmento_tracejada["x"]))
    ]
    planeado_final_traces = _tracos_tracejados_3d(
        linha_planeada_final_segmento_tracejada,
        "Planeado final",
        "#cbd5e1",
        "#e2e8f0",
        largura=7,
        marcador=3,
    )
    for trace in planeado_final_traces:
        trace.hovertemplate = (
            "Trajetória planeada<br>"
            "Até profundidade final<br>"
            f"MD alvo: {profundidade_planeada_final:.2f} m<br>"
            "Este: %{x:.2f} m<br>"
            "Norte: %{y:.2f} m<br>"
            "TVD: %{z:.2f} m<br>"
            "<extra></extra>"
        )

    trace_origem = go.Scatter3d(
        x=[origem[0]],
        y=[origem[1]],
        z=[origem[2]],
        mode="markers",
        name="Origem",
        marker=dict(size=7, color="#22c55e"),
        customdata=[[0.0]],
        hovertemplate=(
            "Origem do furo<br>"
            "Este: %{x:.2f} m<br>"
            "Norte: %{y:.2f} m<br>"
            "TVD: %{z:.2f} m<br>"
            "<extra></extra>"
        ),
    )

    fig = go.Figure(
        data=[trace_origem] + tubo_tracos + [scatter] + planeado_ultima_traces + planeado_final_traces + seta_tracos
    )

    dogleg_max = max(doglegs) if doglegs else 0.0
    estado_max = "OK"
    if any(a == "CRÍTICO" for a in alertas):
        estado_max = "CRÍTICO"
    elif any(a == "ATENÇÃO" for a in alertas):
        estado_max = "ATENÇÃO"

    profundidade_final = medicoes[-1].profundidade_medida if medicoes else 0.0
    profundidade_visual_max = max(float(profundidade_final or 0.0), float(profundidade_planeada_final or 0.0))

    fig.update_layout(
        scene=dict(
            xaxis_title="Este (m)",
            yaxis_title="Norte (m)",
            zaxis_title="TVD / Profundidade Vertical (m)",
            zaxis=dict(autorange="reversed"),
            dragmode="orbit",
            aspectmode="manual",
            aspectratio=dict(x=1, y=1, z=0.7),
            camera=dict(
                eye=dict(x=1.45, y=1.45, z=1.0),
            ),
        ),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.95,
            xanchor="left",
            x=1.02,
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="lightgray",
            borderwidth=1,
            font=dict(size=11),
        ),
        margin=dict(l=0, r=140, t=20, b=0),
        height=800,
    )

    graph = fig.to_html(
        full_html=False,
        config={
            "responsive": True,
            "displaylogo": False,
            "scrollZoom": True,
            "plotGlPixelRatio": 1.5,
        },
    )

    logger.info(
        "View furo_3d_geologico carregada com sucesso. user_id=%s, furo_id=%s, numero_medicoes=%s, estado_max=%s",
        request.user.id,
        furo.id,
        len(medicoes),
        estado_max,
    )
    return render(request, "projetos/furo_3d.html", {
        "furo": furo,
        "graph": graph,
        "numero_medicoes": len(medicoes),
        "profundidade_final": profundidade_final or 0.0,
        "profundidade_visual_max": profundidade_visual_max or 0.0,
        "dogleg_max": dogleg_max,
        "estado_max": estado_max,
    })


@login_required
@admin_required
def furo_3d_importar_externo(request):
    empresa, resposta_erro = _obter_empresa_admin_furos(request)
    if resposta_erro:
        return resposta_erro

    imported_trace = None
    trace_name = ""
    total_pontos = 0
    origem_aplicacao = ""
    furo_destino_id = ""
    observacoes = ""

    if request.method == "POST" and request.FILES.get("ficheiro_3d"):
        try:
            imported_trace = _parse_imported_3d_file(request.FILES["ficheiro_3d"])
            trace_name = imported_trace.get("name") or request.FILES["ficheiro_3d"].name
            total_pontos = len(imported_trace.get("x") or [])
            origem_aplicacao = (request.POST.get("origem_aplicacao") or "").strip()
            furo_destino_id = (request.POST.get("furo_destino") or "").strip()
            observacoes = (request.POST.get("observacoes") or "").strip()

            if "guardar_importacao" in request.POST:
                furo_destino = None
                if furo_destino_id:
                    furo_destino = Furo.objects.filter(pk=furo_destino_id, empresa=empresa).first()

                ImportacaoFuro3DExterna.objects.create(
                    empresa=empresa,
                    furo=furo_destino,
                    nome=trace_name,
                    origem_aplicacao=origem_aplicacao,
                    origem_registo="externa",
                    formato_arquivo=(request.FILES["ficheiro_3d"].name.rsplit(".", 1)[-1] or "").lower(),
                    payload_json=imported_trace,
                    observacoes=observacoes,
                )
                messages.success(
                    request,
                    "Importação 3D guardada na base de dados com origem externa.",
                )
            else:
                messages.success(request, "Trajetória externa carregada com sucesso.")
        except ValueError as exc:
            messages.error(request, str(exc))

    return render(
        request,
        "projetos/furo_3d_importar_externo.html",
        {
            "empresa": empresa,
            "imported_trace": imported_trace,
            "trace_name": trace_name,
            "total_pontos": total_pontos,
            "furos_empresa": Furo.objects.filter(empresa=empresa).order_by("nome"),
            "origem_aplicacao": origem_aplicacao,
            "furo_destino_id": furo_destino_id,
            "observacoes": observacoes,
        },
    )


@login_required
@admin_required
def furo_3d_export(request, furo_id, formato):
    empresa, resposta_erro = _obter_empresa_admin_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        return resposta_erro

    furo = get_object_or_404(Furo, pk=furo_id, empresa_id=empresa_id)
    payload = _dados_exportacao_furo_3d(furo)
    nome_base = f"furo-{furo.pk}-3d"

    if formato == "json":
        response = HttpResponse(
            json.dumps(payload, ensure_ascii=False, indent=2),
            content_type="application/json; charset=utf-8",
        )
        response["Content-Disposition"] = f'attachment; filename="{nome_base}.json"'
        return response

    if formato == "csv":
        response = HttpResponse(_renderizar_furo_3d_csv(payload), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{nome_base}.csv"'
        return response

    if formato == "geojson":
        response = HttpResponse(_renderizar_furo_3d_geojson(payload), content_type="application/geo+json; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{nome_base}.geojson"'
        return response

    if formato == "zip":
        dados = _dados_completos_furo(furo)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(f"{nome_base}-completo.json", json.dumps(dados, ensure_ascii=False, indent=2))
            zip_file.writestr(f"{nome_base}-3d.json", json.dumps(payload, ensure_ascii=False, indent=2))
            zip_file.writestr(f"{nome_base}-3d.csv", _renderizar_furo_3d_csv(payload))
            zip_file.writestr(f"{nome_base}-3d.geojson", _renderizar_furo_3d_geojson(payload))
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{nome_base}-completo.zip"'
        return response

    raise Http404("Formato 3D não suportado.")
