""" from dash import html, dcc
import dash_bootstrap_components as dbc

def layout():
    return html.Div([
        html.H3("Novo Material"),
        dbc.Input(id="mat-nome", placeholder="Nome"),
        dbc.Input(id="mat-valor", placeholder="Valor"),
        dbc.Input(id="mat-quantidade", placeholder="Quantidade"),
        dbc.Input(id="mat-diametro", placeholder="Diâmetro"),
        dbc.Input(id="mat-tipo", placeholder="Tipo"),
        dbc.Input(id="mat-num-serie", placeholder="Número de Série"),
        dbc.Input(id="mat-data-compra", placeholder="Data de Compra"),
        html.Br(),
        dbc.Button("Salvar", id="btn-salvar-mat", color="success"),
        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ]) """


from dash import html, dcc
import dash_bootstrap_components as dbc

def layout():
    return html.Div([

        html.H3("📦 Novo Material", className="mb-4"),

        dbc.Card([
            dbc.CardBody([

                # 🔹 Identificação
                html.H5("Identificação"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Nome"),
                        dbc.Input(id="mat-nome", placeholder="Ex: Coroa diamantada HQ")
                    ], width=6),

                    dbc.Col([
                        dbc.Label("Tipo"),
                        dbc.Select(
                            id="mat-tipo",
                            options=[
                                {"label": "Coroa", "value": "coroa"},
                                {"label": "Haste", "value": "haste"},
                                {"label": "Lubrificante", "value": "lubrificante"},
                                {"label": "Outro", "value": "outro"}
                            ],
                            placeholder="Tipo de material"
                        )
                    ], width=6),
                ], className="mb-4"),

                # 🔹 Especificações
                html.H5("Especificações"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Diâmetro"),
                        dbc.Input(id="mat-diametro", placeholder="Ex: HQ, NQ, 76mm")
                    ], width=4),

                    dbc.Col([
                        dbc.Label("Número de Série"),
                        dbc.Input(id="mat-num-serie", placeholder="Nº série")
                    ], width=4),

                    dbc.Col([
                        dbc.Label("Data de Compra"),
                        dbc.Input(id="mat-data-compra", type="date")
                    ], width=4),
                ], className="mb-4"),

                # 🔹 Stock e custos
                html.H5("Stock e Custos"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Quantidade"),
                        dbc.Input(id="mat-quantidade", type="number", placeholder="Qtd")
                    ], width=4),

                    dbc.Col([
                        dbc.Label("Valor (€)"),
                        dbc.Input(id="mat-valor", type="number", placeholder="Preço unitário")
                    ], width=4),
                ], className="mb-4"),

                # 🔹 Botões
                dbc.Row([
                    dbc.Col(
                        dbc.Button("💾 Salvar", id="btn-salvar-mat", color="success", size="lg"),
                        width="auto"
                    ),
                    dbc.Col(
                        dcc.Link("⬅ Voltar", href="/"),
                        width="auto"
                    )
                ])

            ])
        ])

    ], style={"maxWidth": "900px"})