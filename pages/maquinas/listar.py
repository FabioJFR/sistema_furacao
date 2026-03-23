""" from dash import html, dcc

def layout(maquinas):
    lista = []
    for m in maquinas:
        lista.append(html.Div([
            html.H5(m.nome),
            html.P(f"Tipo: {m.tipo}"),
            html.P(f"Modelo: {m.modelo}"),
            html.P(f"Número Série: {m.numero_serie}"),
            html.P(f"KM: {m.km}"),
            html.P(f"Ano: {m.ano}")
        ], style={"border":"1px solid #ccc","padding":"10px","margin":"5px"}))

    return html.Div([
        html.H3("Lista de Máquinas"),
        html.Div(lista),
        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ]) """

from dash import html, dcc
import dash_bootstrap_components as dbc

def layout(maquinas):

    # 🔹 Estatísticas
    total = len(maquinas)
    tipos = list(set([m.tipo for m in maquinas if hasattr(m, "tipo")]))

    operacionais = len([m for m in maquinas if getattr(m, "estado", "operacional") == "operacional"])
    manutencao = len([m for m in maquinas if getattr(m, "estado", "") == "manutencao"])

    stats = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Total Máquinas"),
            html.H4(total)
        ])), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Operacionais"),
            html.H4(operacionais)
        ])), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Em Manutenção"),
            html.H4(manutencao)
        ])), width=3),
    ], className="mb-4")

    # 🔹 Filtros
    filtros = dbc.Row([
        dbc.Col(
            dbc.Input(id="filtro-maq-nome", placeholder="🔍 Procurar máquina..."),
            width=6
        ),
        dbc.Col(
            dcc.Dropdown(
                id="filtro-maq-tipo",
                options=[{"label": t, "value": t} for t in tipos],
                placeholder="Filtrar por tipo"
            ),
            width=6
        )
    ], className="mb-4")

    # 🔹 Cards de máquinas
    cards = []

    for m in maquinas:

        estado = str(getattr(m, "estado", "operacional")).lower()

        cor_estado = {
            "operacional": "success",
            "manutencao": "warning",
            "parada": "danger"
        }.get(estado, "secondary")

        card = dbc.Card(
            dbc.CardBody([

                html.H5(m.nome),

                dbc.Badge(estado.upper(), color=cor_estado, className="mb-2"),
                html.Br(),

                html.P(f"Tipo: {m.tipo}"),
                html.P(f"Modelo: {m.modelo}"),
                html.P(f"Nº Série: {m.numero_serie}"),

                html.Hr(),

                html.P(f"KM/Horas: {m.km}"),
                html.P(f"Ano: {m.ano}"),

                html.Div([
                    dbc.Button("👁 Ver", size="sm", color="info"),
                    dbc.Button("✏ Editar", size="sm", color="warning", className="mx-1"),
                    dbc.Button("🛠 Manutenção", size="sm", color="secondary"),
                ])

            ]),
            style={"margin": "5px"}
        )

        cards.append(dbc.Col(card, width=4))

    if not cards:
        cards.append(html.P("Sem máquinas cadastradas."))

    return html.Div([
        html.H3("🚜 Painel de Máquinas"),

        stats,
        filtros,

        dbc.Row(cards),

        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ])