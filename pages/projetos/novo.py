""" from dash import html, dcc

def layout():
    return html.Div([
        html.H2("Novo Projeto"),
        dcc.Input(id="proj-nome", placeholder="Nome"),
        dcc.Input(id="proj-cliente", placeholder="Cliente"),
        dcc.Input(id="proj-lat", placeholder="Latitude"),
        dcc.Input(id="proj-lon", placeholder="Longitude"),
        html.Button("Guardar", id="btn-add-projeto")
    ]) """

from dash import html, dcc
import dash_bootstrap_components as dbc

def layout():
    return html.Div([

        # 🔹 Título
        html.H2("📁 Novo Projeto", className="mb-4"),

        dbc.Row([

            # 🔸 COLUNA ESQUERDA (Dados principais)
            dbc.Col([
                dbc.Card(
                    dbc.CardBody([

                        html.H5("Informações Gerais", className="mb-3"),

                        dbc.Label("Nome do Projeto"),
                        dbc.Input(id="proj-nome", placeholder="Ex: Furo Mina Aljustrel"),

                        dbc.Label("Cliente", className="mt-3"),
                        dbc.Input(id="proj-cliente", placeholder="Ex: Empresa X"),

                    ])
                )
            ], width=6),

            # 🔸 COLUNA DIREITA (Localização)
            dbc.Col([
                dbc.Card(
                    dbc.CardBody([

                        html.H5("Localização", className="mb-3"),

                        dbc.Label("Latitude"),
                        dbc.Input(id="proj-lat", type="number", placeholder="Ex: 37.9"),

                        dbc.Label("Longitude", className="mt-3"),
                        dbc.Input(id="proj-lon", type="number", placeholder="Ex: -8.1"),

                        html.Small("Dica: pode copiar coordenadas do Google Maps", className="text-muted")

                    ])
                )
            ], width=6),

        ]),

        html.Br(),

        # 🔹 Ações
        dbc.Row([
            dbc.Col([
                dbc.Button("💾 Guardar Projeto", id="btn-add-projeto", color="success", size="lg"),
                dcc.Link("⬅ Voltar", href="/", className="ms-3")
            ])
        ])

    ])