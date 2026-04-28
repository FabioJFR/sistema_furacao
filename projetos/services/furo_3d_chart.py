import math

import plotly.graph_objects as go

from projetos.selectors.furos import obter_configuracao_visual_furo
from projetos.utils.tragetoria import calcular_linha_planeada, construir_segmentos_tubos
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


def _tracos_tracejados_3d(linha, nome, cor_linha, largura=4):
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


def construir_contexto_furo_3d(furo):
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
            largura=8,
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
            uirevision=f"furo-3d-{furo.pk}",
            scene=dict(
                xaxis_title="Este (m)",
                yaxis_title="Norte (m)",
                zaxis_title="TVD / Profundidade Vertical (m)",
                zaxis=dict(autorange="reversed"),
                uirevision=f"furo-3d-scene-{furo.pk}",
                aspectmode="manual",
                aspectratio=dict(x=1, y=1, z=0.7),
                camera=dict(eye=dict(x=1.8, y=1.8, z=1.2)),
            ),
            showlegend=False,
            margin=dict(l=0, r=20, t=20, b=0),
            height=800,
        )
        graph = fig.to_html(
            full_html=False,
            config={"responsive": True, "displaylogo": False, "scrollZoom": True, "plotGlPixelRatio": 1.5},
        )
        return {
            "graph": graph,
            "numero_medicoes": 0,
            "profundidade_final": 0.0,
            "profundidade_visual_max": profundidade_planeada_final or 0.0,
            "dogleg_max": 0.0,
            "estado_max": "OK",
            "sem_medicoes": True,
        }

    pontos, doglegs, alertas = calcular_trajetoria_min_curv(medicoes, origem=origem)
    ultima_md = float(medicoes[-1].profundidade_medida or 0.0)
    linha_planeada_atual = calcular_linha_planeada(origem=origem, inclinacao=inclinacao_planeada, azimute=azimute_planeado, comprimento=ultima_md)
    linha_planeada_atual_tracejada = _linha_tracejada_3d(linha_planeada_atual)
    linha_planeada_final = calcular_linha_planeada(origem=origem, inclinacao=inclinacao_planeada, azimute=azimute_planeado, comprimento=profundidade_planeada_final)

    x, y, z = [], [], []
    customdata = []
    configuracao_visual = obter_configuracao_visual_furo(furo, empresa=furo.empresa_id)

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
        customdata.append([prof, incl, azim, mag, img_url, estado])

    cores_pontos = [0.0]
    for idx in range(total_pontos_medicoes):
        cores_pontos.append(doglegs[idx + 1] if idx + 1 < len(doglegs) else 0.0)

    seta_tracos = _tracos_vetores_direcao_3d(x, y, z, 1)
    mds_path = [float(item[0] or 0.0) for item in customdata]
    segmentos_tubo = construir_segmentos_tubos(
        pontos=list(zip(x, y, z)),
        mds=mds_path,
        comprimento_frontal=(getattr(configuracao_visual, "comprimento_total_conjunto_fundo", 0.0) if configuracao_visual else 0.0),
        comprimento_padrao=(float(getattr(configuracao_visual, "comprimento_tubo", 3.0) or 3.0) if configuracao_visual else 3.0),
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
            hover_extra = f"Comprimento do conjunto de fundo: {segmento['fim_md'] - segmento['inicio_md']:.2f} m<br>"
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
                customdata=[[segmento["inicio_md"], segmento.get("tubo_numero") or 0], [segmento["fim_md"], segmento.get("tubo_numero") or 0]],
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
        tubo_tracos.extend(_tracos_juntas_tubo_3d(segmentos_tubo["juntas"], segmentos_tubo["segmentos"], tamanho=1.25))

    scatter = go.Scatter3d(
        x=x,
        y=y,
        z=z,
        mode="lines+markers",
        line=dict(width=5, color="blue"),
        marker=dict(size=12, color=cores_pontos, colorscale=[[0, "green"], [0.5, "yellow"], [1, "red"]], showscale=False),
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
    planeado_ultima_traces = _tracos_tracejados_3d(linha_planeada_atual_tracejada, "Planeado até última medição", "#f97316", largura=7)
    for trace in planeado_ultima_traces:
        trace.hovertemplate = (
            "Trajetória planeada<br>"
            "Até última medição<br>"
            f"MD alvo: {ultima_md:.2f} m<br>"
            "Este: %{x:.2f} m<br>"
            "Norte: %{y:.2f} m<br>"
            "TVD: %{z:.2f} m<br>"
            "<extra></extra>"
        )

    inicio_final_idx = 0
    if profundidade_planeada_final > 0:
        inicio_final_idx = max(0, min(len(linha_planeada_final["x"]) - 1, int(round((ultima_md / profundidade_planeada_final) * max(len(linha_planeada_final["x"]) - 1, 0)))))

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
    planeado_final_traces = _tracos_tracejados_3d(linha_planeada_final_segmento_tracejada, "Planeado final", "#cbd5e1", largura=7)
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

    fig = go.Figure(data=[trace_origem] + tubo_tracos + [scatter] + planeado_ultima_traces + planeado_final_traces + seta_tracos)
    fig.update_layout(
        uirevision=f"furo-3d-{furo.pk}",
        scene=dict(
            xaxis_title="Este (m)",
            yaxis_title="Norte (m)",
            zaxis_title="TVD / Profundidade Vertical (m)",
            zaxis=dict(autorange="reversed"),
            dragmode="orbit",
            uirevision=f"furo-3d-scene-{furo.pk}",
            aspectmode="manual",
            aspectratio=dict(x=1, y=1, z=0.7),
            camera=dict(eye=dict(x=1.45, y=1.45, z=1.0)),
        ),
        showlegend=False,
        margin=dict(l=0, r=20, t=20, b=0),
        height=800,
    )
    graph = fig.to_html(
        full_html=False,
        config={"responsive": True, "displaylogo": False, "scrollZoom": True, "plotGlPixelRatio": 1.5},
    )

    dogleg_max = max(doglegs) if doglegs else 0.0
    estado_max = "OK"
    if any(a == "CRÍTICO" for a in alertas):
        estado_max = "CRÍTICO"
    elif any(a == "ATENÇÃO" for a in alertas):
        estado_max = "ATENÇÃO"

    profundidade_final = medicoes[-1].profundidade_medida if medicoes else 0.0
    profundidade_visual_max = max(float(profundidade_final or 0.0), float(profundidade_planeada_final or 0.0))

    return {
        "graph": graph,
        "numero_medicoes": len(medicoes),
        "profundidade_final": profundidade_final or 0.0,
        "profundidade_visual_max": profundidade_visual_max or 0.0,
        "dogleg_max": dogleg_max,
        "estado_max": estado_max,
        "sem_medicoes": False,
    }
