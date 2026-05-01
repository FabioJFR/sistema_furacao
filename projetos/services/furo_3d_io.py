import csv
import io
import json
import zipfile

from django.http import Http404, HttpResponse

from projetos.models import (
    Despesa,
    EmpregadoFuro,
    ImportacaoFuro3DExterna,
    Maquina,
    Material,
    RegistoDiarioEmpregado,
)
from projetos.utils.tragetoria import calcular_linha_planeada
from projetos.utils.tragetoria import calcular_trajetoria_min_curv


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


def dados_exportacao_furo_3d(furo):
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


def renderizar_furo_3d_csv(payload):
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


def renderizar_furo_3d_geojson(payload):
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


def dados_completos_furo(furo):
    payload_3d = dados_exportacao_furo_3d(furo)
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
            for r in RegistoDiarioEmpregado.objects.filter(furo=furo, empresa_id=furo.empresa_id)
            .select_related("empregado")
            .order_by("-data")
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
            for ligacao in EmpregadoFuro.objects.filter(furo=furo, empresa_id=furo.empresa_id)
            .select_related("empregado")
            .order_by("-ativo", "data_inicio")
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


def exportar_furo_3d_response(furo, formato):
    payload = dados_exportacao_furo_3d(furo)
    nome_base = f"furo-{furo.pk}-3d"

    if formato == "json":
        response = HttpResponse(
            json.dumps(payload, ensure_ascii=False, indent=2),
            content_type="application/json; charset=utf-8",
        )
        response["Content-Disposition"] = f'attachment; filename="{nome_base}.json"'
        return response

    if formato == "csv":
        response = HttpResponse(
            renderizar_furo_3d_csv(payload),
            content_type="text/csv; charset=utf-8",
        )
        response["Content-Disposition"] = f'attachment; filename="{nome_base}.csv"'
        return response

    if formato == "geojson":
        response = HttpResponse(
            renderizar_furo_3d_geojson(payload),
            content_type="application/geo+json; charset=utf-8",
        )
        response["Content-Disposition"] = f'attachment; filename="{nome_base}.geojson"'
        return response

    if formato == "zip":
        dados = dados_completos_furo(furo)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(f"{nome_base}-completo.json", json.dumps(dados, ensure_ascii=False, indent=2))
            zip_file.writestr(f"{nome_base}-3d.json", json.dumps(payload, ensure_ascii=False, indent=2))
            zip_file.writestr(f"{nome_base}-3d.csv", renderizar_furo_3d_csv(payload))
            zip_file.writestr(f"{nome_base}-3d.geojson", renderizar_furo_3d_geojson(payload))
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{nome_base}-completo.zip"'
        return response

    raise Http404("Formato 3D não suportado.")


def parse_imported_3d_file(uploaded_file):
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


def guardar_importacao_externa_3d(
    *,
    empresa,
    uploaded_filename,
    imported_trace,
    trace_name,
    origem_aplicacao="",
    furo_destino=None,
    observacoes="",
):
    formato = (uploaded_filename.rsplit(".", 1)[-1] if "." in uploaded_filename else "").lower()
    return ImportacaoFuro3DExterna.objects.create(
        empresa=empresa,
        furo=furo_destino,
        nome=trace_name,
        origem_aplicacao=(origem_aplicacao or "").strip(),
        origem_registo="externa",
        formato_arquivo=formato,
        payload_json=imported_trace,
        observacoes=(observacoes or "").strip(),
    )
