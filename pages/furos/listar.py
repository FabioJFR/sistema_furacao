""" from dash import html, dcc
import dash_bootstrap_components as dbc

def layout(projetos):
    cards = []

    for p in projetos:
        for f in p.furos:

            ultima = f.medicoes[-1] if f.medicoes else None

            card = dbc.Col(
                dbc.Card([
                    dbc.CardBody([

                        html.H5(f.nome, className="card-title"),
                        html.H6(f"Projeto: {p.nome}", className="card-subtitle mb-2 text-muted"),

                        html.Hr(),

                        html.P([
                            html.Strong("Profundidade: "),
                            f"{ultima['profundidade']} m" if ultima else "N/A"
                        ]),

                        html.P([
                            html.Strong("Inclinação: "),
                            f"{ultima['inclinacao']}°" if ultima else "N/A"
                        ]),

                        html.P([
                            html.Strong("Azimute: "),
                            f"{ultima['azimute']}°" if ultima else "N/A"
                        ]),

                        html.Br(),

                        dbc.Button(
                            "🔍 Ver Detalhes",
                            href=f"/furo/{f.id}",
                            color="primary",
                            size="sm"
                        )

                    ])
                ], className="h-100 shadow-sm"),
                width=4  # 3 por linha
            )

            cards.append(card)

    if not cards:
        return html.Div([
            dbc.Alert("Não existem furos cadastrados.", color="warning"),
            html.Br(),
            dcc.Link("⬅ Voltar", href="/")
        ])

    return html.Div([

        html.H2("🕳️ Lista de Furos", className="mb-4"),

        dbc.Row(cards, className="g-3"),

        html.Br(),
        dcc.Link("⬅ Voltar", href="/")

    ]) """

# pages/furos/listar.py
from dash import html, dcc
import dash_bootstrap_components as dbc
from utils.alertas import analisar_furo

def layout(projetos):
    cards = []

    for p in projetos:
        for f in p.furos:

            # 🔹 Garantir que estado é sempre string
            estado = str(f.estado).lower()

            # 🔹 Cor do badge
            cor_estado = {
                "ativo": "success",
                "parado": "warning",
                "concluido": "secondary"
            }.get(estado, "dark")

            # 🔹 Última medição segura
            ultima = f.medicoes[-1] if f.medicoes else None

            # 🔹 Alertas automáticos
            alertas = analisar_furo(f)

            card = dbc.Card(
                dbc.CardBody([
                    html.H5(f"{f.nome} (Projeto: {p.nome})"),

                    dbc.Badge(estado.upper(), color=cor_estado),
                    html.Br(),

                    # Última medição
                    html.P(f"Profundidade: {ultima['profundidade']} m" if ultima else "Sem medições"),
                    html.P(f"Inclinação: {ultima['inclinacao']}" if ultima else ""),
                    html.P(f"Azimute: {ultima['azimute']}" if ultima else ""),

                    # Alertas
                    html.Div([
                        dbc.Alert(a, color="danger", className="p-1")
                        for a in alertas
                    ]) if alertas else None,

                    # Botões
                    html.Div([
                        dcc.Link("🔍 Detalhes", href=f"/furo/{f.id}", style={"margin-right": "10px"}),
                        dcc.Link("📍 Ver no Mapa", href=f"/projeto/{p.id}")
                    ])
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
    ])