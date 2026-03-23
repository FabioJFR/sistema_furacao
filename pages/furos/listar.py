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
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
import dash

def layout(projetos):

    # ================= STATS =================
    total_furos = sum(len(p.furos) for p in projetos)

    total_metros = sum(
        f.medicoes[-1]["profundidade"]
        for p in projetos
        for f in p.furos
        if f.medicoes
    )

    projetos_nomes = list(set(p.nome for p in projetos))

    return html.Div([
        html.H2("🕳️ Painel de Furos", className="mb-4"),

        # ================= CARDS =================
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H4(total_furos), html.P("Furos")
            ]), color="primary", inverse=True), width=3),

            dbc.Col(dbc.Card(dbc.CardBody([
                html.H4(f"{total_metros:.1f} m"), html.P("Metros Perfurados")
            ]), color="success", inverse=True), width=3),

            dbc.Col(dbc.Card(dbc.CardBody([
                html.H4(len(projetos_nomes)), html.P("Projetos")
            ]), color="dark", inverse=True), width=3),
        ], className="mb-4"),

        # ================= FILTROS =================
        dbc.Card([
            dbc.CardBody([
                html.H5("🔎 Filtros"),

                dbc.Row([
                    dbc.Col([
                        dbc.Label("Projeto"),
                        dcc.Dropdown(
                            id="filtro-projeto",
                            options=[{"label": p, "value": p} for p in projetos_nomes],
                            placeholder="Todos os projetos",
                            clearable=True
                        )
                    ], width=4),

                    dbc.Col([
                        dbc.Label("Profundidade mínima"),
                        dbc.Input(id="filtro-prof", type="number")
                    ], width=4),
                ])
            ])
        ], className="mb-4"),

        html.Div(id="lista-furos"),

        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ])