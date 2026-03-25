from dash import html, dcc
import dash_bootstrap_components as dbc

def layout(materiais, prefix="listar"):
    """
    Layout para listar materiais.
    materiais: lista de objetos/materials
    prefix: string para IDs dinâmicos
    """

    # 🔹 Estatísticas
    total = len(materiais)
    tipos = list(set([m.tipo for m in materiais if hasattr(m, "tipo")]))
    
    stats = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Total Materiais"),
            html.H4(total, id={"type": "total-materiais", "index": prefix})
        ])), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Tipos Diferentes"),
            html.H4(len(tipos), id={"type": "tipos-materiais", "index": prefix})
        ])), width=3)
    ], className="mb-4")

    # 🔹 Filtros
    filtros = dbc.Row([
        dbc.Col(
            dbc.Input(id={"type": "filtro-mat-nome", "index": prefix}, placeholder="🔍 Procurar por nome..."),
            width=6
        ),
        dbc.Col(
            dcc.Dropdown(
                id={"type": "filtro-mat-tipo", "index": prefix},
                options=[{"label": t.capitalize(), "value": t} for t in tipos],
                placeholder="Filtrar por tipo"
            ),
            width=6
        )
    ], className="mb-4")

    # 🔹 Cards de materiais
    cards = []
    for m in materiais:
        card = dbc.Card(
            dbc.CardBody([
                html.H5(m.nome, id={"type": "mat-nome", "index": m.numero_serie}),
                dbc.Badge(m.tipo.capitalize(), color="primary", className="mb-2", id={"type": "mat-tipo", "index": m.numero_serie}),
                html.Br(),
                html.P(f"Diâmetro: {getattr(m, 'diametro', '—')}", id={"type": "mat-diametro", "index": m.numero_serie}),
                html.P(f"Nº Série: {getattr(m, 'numero_serie', '—')}", id={"type": "mat-num-serie", "index": m.numero_serie}),
                html.P(f"Data Compra: {getattr(m, 'data_compra', '—')}", id={"type": "mat-data-compra", "index": m.numero_serie}),
                html.P(f"Quantidade: {getattr(m, 'quantidade', 0)}", id={"type": "mat-quantidade", "index": m.numero_serie}),
                html.P(f"Valor (€): {getattr(m, 'valor', 0):.2f}", id={"type": "mat-valor", "index": m.numero_serie}),

                html.Hr(),

                html.Div([
                    dbc.Button("👁 Ver", size="sm", color="info", id={"type": "btn-ver-mat", "index": m.numero_serie}),
                    dbc.Button("✏ Editar", size="sm", color="warning", className="mx-1", id={"type": "btn-editar-mat", "index": m.numero_serie}),
                    dbc.Button("🗑 Apagar", size="sm", color="danger", id={"type": "btn-apagar-mat", "index": m.numero_serie})
                ])
            ]),
            style={"margin": "5px"}
        )
        cards.append(dbc.Col(card, width=4))

    if not cards:
        cards.append(html.P("Sem materiais cadastrados."))

    return dbc.Container([
        html.H3("📦 Painel de Materiais"),
        stats,
        filtros,
        dbc.Row(cards),
        html.Br(),
        dcc.Link("⬅ Voltar", href="/", id={"type": "link-voltar", "index": prefix})
    ], fluid=True)