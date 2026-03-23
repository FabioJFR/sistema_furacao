""" from dash import html, dcc

def layout(empregados):
    lista = []
    for e in empregados:
        lista.append(html.Div([
            html.H5(e.nome),
            html.P(f"Número: {e.numero}"),
            html.P(f"Idade: {e.idade}"),
            html.P(f"Categoria: {e.categoria}")
        ], style={"border":"1px solid #ccc","padding":"10px","margin":"5px"}))
    
    return html.Div([
        html.H3("Lista de Empregados"),
        html.Div(lista),
        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ]) """

from dash import html, dcc
import dash_bootstrap_components as dbc

def layout(empregados):

    # 🔹 Estatísticas
    total = len(empregados)
    categorias = list(set([e.categoria for e in empregados if hasattr(e, "categoria")]))

    stats = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Total"),
            html.H4(total)
        ])), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Categorias"),
            html.H4(len(categorias))
        ])), width=3),
    ], className="mb-4")

    # 🔹 Filtros
    filtros = dbc.Row([
        dbc.Col(
            dbc.Input(id="filtro-nome", placeholder="🔍 Procurar por nome..."),
            width=6
        ),
        dbc.Col(
            dcc.Dropdown(
                id="filtro-categoria",
                options=[{"label": c, "value": c} for c in categorias],
                placeholder="Filtrar por categoria"
            ),
            width=6
        )
    ], className="mb-4")

    # 🔹 Lista de empregados (cards)
    cards = []

    for e in empregados:
        card = dbc.Card(
            dbc.CardBody([
                html.H5(e.nome),

                dbc.Badge(e.categoria, color="primary", className="mb-2"),
                html.Br(),

                html.P(f"Número: {e.numero}"),
                html.P(f"Idade: {e.idade}"),

                html.Div([
                    dbc.Button("👁 Ver", size="sm", color="info"),
                    dbc.Button("✏ Editar", size="sm", color="warning", className="mx-1"),
                    dbc.Button("🗑 Remover", size="sm", color="danger")
                ])
            ]),
            style={"margin": "5px"}
        )

        cards.append(dbc.Col(card, width=4))

    if not cards:
        cards.append(html.P("Sem empregados cadastrados."))

    return html.Div([
        html.H3("👷 Painel de Empregados"),

        stats,
        filtros,

        dbc.Row(cards),

        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ])