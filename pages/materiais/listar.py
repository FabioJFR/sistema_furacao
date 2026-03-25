from dash import html, dcc
import dash_bootstrap_components as dbc
# pages/materiais/listar.py

def layout(materiais, prefix="listar"):
    
    # materiais: lista de objetos de materiais
    # prefix: string para tornar os IDs dinâmicos (ex: 'listar', 'editar', 'novo')
    
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
            html.H4(total, id={"type": "total-materiais", "index": prefix})
        ])), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Stock Total"),
            html.H4(stock_total, id={"type": "stock-total", "index": prefix})
        ])), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Valor Inventário (€)"),
            html.H4(f"{valor_total:.2f}", id={"type": "valor-inventario", "index": prefix})
        ])), width=3),
    ], className="mb-4")

    # 🔹 Filtros
    filtros = dbc.Row([
        dbc.Col(
            dbc.Input(id={"type": "filtro-mat-nome", "index": prefix}, placeholder="🔍 Procurar material..."),
            width=6
        ),
        dbc.Col(
            dcc.Dropdown(
                id={"type": "filtro-mat-tipo", "index": prefix},
                options=[{"label": t, "value": t} for t in tipos],
                placeholder="Filtrar por tipo"
            ),
            width=6
        )
    ], className="mb-4")

    # 🔹 Cards
    cards = []

    for i, m in enumerate(materiais, 1):
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

                html.H5(m.nome, id={"type": "mat-nome", "index": i}),

                dbc.Badge(
                    str(getattr(m, "tipo", "outro")).upper(),
                    color="primary",
                    className="mb-2",
                    id={"type": "mat-tipo", "index": i}
                ),
                html.Br(),

                html.P(f"Quantidade: {quantidade}", id={"type": "mat-quantidade", "index": i}),
                html.P(f"Valor Unitário: {valor} €", id={"type": "mat-valor", "index": i}),
                html.P(f"Total: {quantidade * valor:.2f} €", id={"type": "mat-total", "index": i}),

                html.Hr(),

                alerta if alerta else None,

                html.Div([
                    dbc.Button("👁 Ver", size="sm", color="info", id={"type": "btn-ver-mat", "index": i}),
                    dbc.Button("✏ Editar", size="sm", color="warning", className="mx-1", id={"type": "btn-editar-mat", "index": i}),
                    dbc.Button("➖ Consumir", size="sm", color="secondary", id={"type": "btn-consumir-mat", "index": i}),
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
        dcc.Link("⬅ Voltar", href="/", id={"type": "link-voltar-mat", "index": prefix})
    ]) 

