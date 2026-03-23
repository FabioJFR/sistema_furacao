from dash import html, dcc
import dash_bootstrap_components as dbc

def layout(projetos):

    # ================= KPIs =================
    total_projetos = len(projetos)
    total_furos = sum(len(p.furos) for p in projetos)

    kpis = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Projetos"),
            html.H4(total_projetos)
        ])), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Total de Furos"),
            html.H4(total_furos)
        ])), width=3),
    ], className="mb-4")


    # ================= LISTA =================
    cards = []

    for p in projetos:
        card = dbc.Card(
            dbc.CardBody([

                # 🔹 Nome
                html.H5(p.nome),

                # 🔹 Info
                html.P(f"Cliente: {p.cliente}"),
                html.P(f"Localização: {p.localizacao}"),
                html.P(f"Furos: {len(p.furos)}"),

                # 🔹 Ações
                html.Div([
                    dcc.Link("📍 Ver no Mapa", href=f"/projeto/{p.id}", style={"margin-right":"10px"}),
                    dcc.Link("📊 Ver Furos", href="/furos/listar")
                ])

            ]),
            style={"margin":"5px"}
        )

        cards.append(card)

    if not cards:
        cards.append(html.P("Não existem projetos cadastrados."))


    # ================= LAYOUT FINAL =================
    return html.Div([

        html.H3("📁 Painel de Projetos"),

        kpis,

        dbc.Row([
            dbc.Col(card, width=4) for card in cards
        ]),

        html.Br(),
        dcc.Link("⬅ Voltar", href="/")

    ])