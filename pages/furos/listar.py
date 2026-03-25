from dash import html, dcc
import dash_bootstrap_components as dbc
from utils.alertas import analisar_furo

# pages/furos/listar.py
def layout(projetos):
    cards = []

    for p in projetos:
        for f in p.furos:

            # 🔹 Estado e alertas
            estado = str(getattr(f, "estado", "")).lower()
            ultima = f.medicoes[-1] if getattr(f, "medicoes", None) else None
            alertas = analisar_furo(f) if f else []

            cor_bola = {
                "ativo": "green",
                "parado": "orange",
                "concluido": "gray"
            }.get(estado, "blue")
            if alertas:
                cor_bola = "red"

            bola = html.Span(
                "●",
                style={"color": cor_bola, "margin-right": "5px", "font-size": "18px"}
            )

            # 🔹 Accordion com proteção contra atributos ausentes
            accordion = dbc.Accordion([
                dbc.AccordionItem(
                    [
                        html.P(f"Profundidade Alvo: {getattr(f, 'profundidade_alvo', 0)} m"),
                        html.P(f"Inclinação: {getattr(f, 'inclinacao', 0)}°"),
                        html.P(f"Azimute: {getattr(f, 'azimute', 0)}°"),
                        html.P(f"Local de Sondagem: {getattr(f, 'local_sondagem', '')}"),
                        html.P(f"Tipo: {getattr(f, 'tipo', '')}")
                    ],
                    title="📌 Dados Planejados"
                ),
                dbc.AccordionItem(
                    [
                        html.P(f"Profundidade Atual: {getattr(ultima, 'profundidade', '—')} m"),
                        html.P(f"Inclinação Atual: {getattr(ultima, 'inclinacao', '—')}°"),
                        html.P(f"Azimute Atual: {getattr(ultima, 'azimute', '—')}°"),
                        html.P(f"Magnetismo: {getattr(ultima, 'magnetismo', '—')}")
                    ],
                    title="⏱️ Última Medição"
                ),
                dbc.AccordionItem(
                    [
                        html.P(f"Profundidade Atual: {getattr(f, 'profundidade_atual', 0)} m"),
                        html.P(f"Nº Medições: {len(getattr(f, 'medicoes', []))}"),
                        html.P(f"Metros Furados Diário: {sum(getattr(f, 'metros_furados_diario', [])):.2f} m"),
                        html.P(f"Total Metros Furados: {getattr(f, 'metros_furados', 0):.2f} m")
                    ],
                    title="📊 Estado Atual"
                ),
                dbc.AccordionItem(
                    html.Div([dbc.Alert(a, color="danger", className="p-1") for a in alertas]) if alertas else html.P("Sem alertas"),
                    title="⚠️ Alertas"
                )
            ], always_open=True)

            # 🔹 Card
            card = dbc.Card(
                dbc.CardBody([
                    html.H5([bola, f"{getattr(f, 'nome', 'Sem Nome')} (Projeto: {getattr(p, 'nome', 'Sem Projeto')})"]),
                    html.Hr(),
                    accordion,
                    html.Hr(),

                    # 🔹 Botões com IDs dinâmicos
                    html.Div([
                        dbc.Button("🔍 Detalhes", id={"type": "btn-detalhes-furo", "index": getattr(f, 'id', '')}, color="info", size="sm"),
                        dbc.Button("✏️ Editar", id={"type": "btn-editar-furo", "index": getattr(f, 'id', '')}, color="warning", size="sm", className="mx-1"),
                        dbc.Button("🗑️ Apagar", id={"type": "btn-apagar-furo", "index": getattr(f, 'id', '')}, color="danger", size="sm"),
                        dbc.Button("📍 Mapa", id={"type": "btn-mapa-furo", "index": getattr(f, 'id', '')}, color="secondary", size="sm", className="mx-1")
                    ], style={
                        "display": "flex",
                        "flex-wrap": "nowrap",
                        "overflow-x": "auto"
                    })
                ]),
                style={"margin": "5px"}
            )

            cards.append(card)

    if not cards:
        cards.append(html.P("Não existem furos cadastrados."))

    return html.Div([
        html.H3("Painel de Furos"),
        dbc.Row([dbc.Col(card, width=4) for card in cards]),
        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ], style={"maxWidth": "1200px"})