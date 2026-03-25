from dash import html, dcc
import dash_bootstrap_components as dbc


# pages/projetos/listar.py
def layout(projetos, prefix="listar"):
    
    # projetos: lista de projetos
    # prefix: prefixo para IDs dinâmicos
    
    # ================= KPIs =================
    total_projetos = len(projetos)
    total_furos = sum(len(p.furos) for p in projetos)

    kpis = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Projetos"),
            html.H4(total_projetos, id={"type": "kpi-projetos", "index": prefix})
        ])), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Total de Furos"),
            html.H4(total_furos, id={"type": "kpi-furos", "index": prefix})
        ])), width=3),
    ], className="mb-4")


    # ================= LISTA =================
    cards = []

    for p in projetos:
        card = dbc.Card(
            dbc.CardBody([

                # 🔹 Nome
                html.H5(p.nome, id={"type": "proj-nome", "index": p.id}),

                # 🔹 Info
                html.P(f"Cliente: {p.cliente}", id={"type": "proj-cliente", "index": p.id}),
                html.P(f"Localização: {p.localizacao}", id={"type": "proj-localizacao", "index": p.id}),
                html.P(f"Furos: {len(p.furos)}", id={"type": "proj-furos", "index": p.id}),

                # 🔹 Ações
                html.Div([
                    dcc.Link("📍 Ver no Mapa", href=f"/projeto/{p.id}", 
                             style={"margin-right":"10px"}, id={"type": "link-mapa", "index": p.id}),
                    dcc.Link("📊 Ver Furos", href="/furos/listar", id={"type": "link-furos", "index": p.id})
                ])

            ]),
            style={"margin":"5px"},
            id={"type": "card-proj", "index": p.id}
        )

        cards.append(card)

    if not cards:
        cards.append(html.P("Não existem projetos cadastrados.", id={"type": "sem-projetos", "index": prefix}))

    # ================= LAYOUT FINAL =================
    return html.Div([

        html.H3("📁 Painel de Projetos", id={"type": "titulo-projetos", "index": prefix}),

        kpis,

        dbc.Row([
            dbc.Col(card, width=4) for card in cards
        ]),

        html.Br(),
        dcc.Link("⬅ Voltar", href="/", id={"type": "link-voltar", "index": prefix})

    ])
