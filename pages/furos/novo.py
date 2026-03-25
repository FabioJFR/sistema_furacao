""" from dash import html, dcc
import dash_bootstrap_components as dbc

# pages/furos/novo.py
def layout(projetos):
    return html.Div([

        html.H2("🕳️ Novo Furo", style={"margin-bottom": "20px"}),

        dbc.Card([
            dbc.CardBody([

                html.H4("Informações Gerais", className="mb-3"),

                dbc.Row([
                    dbc.Col([
                        dbc.Label("Projeto"),
                        dbc.Select(
                            id="furo-projeto",
                            options=[{"label": getattr(p, 'nome', 'Sem Nome'), "value": getattr(p, 'id', '')} for p in projetos],
                            value=projetos[0].id if projetos else ""
                        )
                    ], width=6),
                ], className="mb-3"),

                dbc.Row([
                    dbc.Col([
                        dbc.Label("Nome do Furo"),
                        dbc.Input(id="furo-nome", placeholder="Ex: Furo A1", value="")
                    ], width=6),

                    dbc.Col([
                        dbc.Label("Profundidade Alvo (m)"),
                        dbc.Input(id="furo-profundidade", type="number", placeholder="Ex: 120", value=0)
                    ], width=6),
                ], className="mb-3"),

                html.Hr(),

                html.H4("Direção", className="mb-3"),

                dbc.Row([
                    dbc.Col([
                        dbc.Label("Inclinação (°)"),
                        dbc.Input(id="furo-inclinacao", type="number", placeholder="Ex: -45", value=0)
                    ], width=6),

                    dbc.Col([
                        dbc.Label("Azimute (°)"),
                        dbc.Input(id="furo-azimute", type="number", placeholder="Ex: 120", value=0)
                    ], width=6),
                ], className="mb-3"),

                html.Hr(),

                html.H4("Localização", className="mb-3"),

                dbc.Row([
                    dbc.Col([
                        dbc.Label("Latitude"),
                        dbc.Input(id="furo-lat", type="number", placeholder="Ex: 37.9", value=0)
                    ], width=6),

                    dbc.Col([
                        dbc.Label("Longitude"),
                        dbc.Input(id="furo-lon", type="number", placeholder="Ex: -8.1", value=0)
                    ], width=6),
                ], className="mb-4"),

                # 🔹 Botão com ID dinâmico
                dbc.Button(
                    "💾 Salvar Furo",
                    id={"type": "btn-salvar-furo", "index": "novo"},
                    color="success",
                    size="lg"
                ),

                html.Br(), html.Br(),

                dcc.Link("⬅ Voltar", href="/furos/listar")

            ])
        ])

    ], style={"maxWidth": "900px"}) """


from dash import html, dcc
import dash_bootstrap_components as dbc

def layout(projetos, prefix="novo-furo"):
    """
    projetos: lista de projetos
    prefix: prefixo dinâmico
    """

    projeto_options = [{"label": p.nome, "value": p.id} for p in projetos]

    return html.Div([

        html.H3("➕ Novo Furo", className="mb-4"),

        dbc.Row([
            dbc.Col([
                dbc.Card(
                    dbc.CardBody([
                        dbc.Label("Projeto"),
                        dcc.Dropdown(
                            id={"type": "furo-projeto", "index": prefix},
                            options=projeto_options,
                            placeholder="Selecione um projeto"
                        ),

                        dbc.Label("Nome do Furo", className="mt-3"),
                        dbc.Input(
                            id={"type": "furo-nome", "index": prefix}, 
                            placeholder="Ex: Furo 01"
                        ),

                        dbc.Label("Profundidade (m)", className="mt-3"),
                        dbc.Input(
                            id={"type": "furo-profundidade", "index": prefix}, 
                            type="number"
                        ),

                        dbc.Label("Inclinação (°)", className="mt-3"),
                        dbc.Input(
                            id={"type": "furo-inclinacao", "index": prefix}, 
                            type="number"
                        ),

                        dbc.Label("Azimute (°)", className="mt-3"),
                        dbc.Input(
                            id={"type": "furo-azimute", "index": prefix}, 
                            type="number"
                        ),

                        dbc.Label("Latitude", className="mt-3"),
                        dbc.Input(
                            id={"type": "furo-lat", "index": prefix}, 
                            type="number"
                        ),

                        dbc.Label("Longitude", className="mt-3"),
                        dbc.Input(
                            id={"type": "furo-lon", "index": prefix}, 
                            type="number"
                        ),
                    ])
                )
            ])
        ]),

        html.Br(),

        dbc.Row([
            dbc.Col([
                dbc.Button(
                    "💾 Guardar Furo", 
                    id={"type": "btn-salvar-furo", "index": prefix}, 
                    color="success"
                ),
                dcc.Link(
                    "⬅ Voltar", 
                    href="/furos/listar", 
                    className="ms-3"
                )
            ])
        ])

    ], style={"maxWidth": "900px"})