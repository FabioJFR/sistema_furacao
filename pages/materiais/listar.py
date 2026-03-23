from dash import html, dcc
import dash_bootstrap_components as dbc

def layout(materiais):

    # 🔹 Estatísticas
    total = len(materiais)
    tipos = list(set([m.tipo for m in materiais if hasattr(m, "tipo")]))

    stock_total = sum([getattr(m, "quantidade", 0) or 0 for m in materiais])
    valor_total = sum([
        (getattr(m, "quantidade", 0) or 0) * (getattr(m, "valor", 0) or 0)
        for m in materiais
    ])

    stats = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Total Materiais"),
            html.H4(total)
        ])), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Stock Total"),
            html.H4(stock_total)
        ])), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Valor Inventário (€)"),
            html.H4(f"{valor_total:.2f}")
        ])), width=3),
    ], className="mb-4")

    # 🔹 Filtros
    filtros = dbc.Row([
        dbc.Col(
            dbc.Input(id="filtro-mat-nome", placeholder="🔍 Procurar material..."),
            width=6
        ),
        dbc.Col(
            dcc.Dropdown(
                id="filtro-mat-tipo",
                options=[{"label": t, "value": t} for t in tipos],
                placeholder="Filtrar por tipo"
            ),
            width=6
        )
    ], className="mb-4")

    # 🔹 Cards
    cards = []

    for m in materiais:

        quantidade = getattr(m, "quantidade", 0) or 0
        valor = getattr(m, "valor", 0) or 0

        # ⚠️ alerta de stock
        alerta = None
        if quantidade <= 2:
            alerta = dbc.Alert("⚠️ Stock crítico", color="danger", className="p-1")
        elif quantidade <= 5:
            alerta = dbc.Alert("⚠️ Stock baixo", color="warning", className="p-1")

        card = dbc.Card(
            dbc.CardBody([

                html.H5(m.nome),

                dbc.Badge(
                    str(getattr(m, "tipo", "outro")).upper(),
                    color="primary",
                    className="mb-2"
                ),
                html.Br(),

                html.P(f"Quantidade: {quantidade}"),
                html.P(f"Valor Unitário: {valor} €"),
                html.P(f"Total: {quantidade * valor:.2f} €"),

                html.Hr(),

                alerta if alerta else None,

                html.Div([
                    dbc.Button("👁 Ver", size="sm", color="info"),
                    dbc.Button("✏ Editar", size="sm", color="warning", className="mx-1"),
                    dbc.Button("➖ Consumir", size="sm", color="secondary"),
                ])

            ]),
            style={"margin": "5px"}
        )

        cards.append(dbc.Col(card, width=4))

    if not cards:
        cards.append(html.P("Sem materiais cadastrados."))

    return html.Div([
        html.H3("📦 Painel de Materiais"),

        stats,
        filtros,

        dbc.Row(cards),

        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ])