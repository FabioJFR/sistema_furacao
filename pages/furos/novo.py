""" from dash import html, dcc
import dash_bootstrap_components as dbc
import uuid

def layout(projetos):
    return html.Div([
        html.H3("Novo Furo"),
        dbc.Input(id="furo-nome", placeholder="Nome"),
        dbc.Input(id="furo-inclinacao", placeholder="Inclinação"),
        dbc.Input(id="furo-azimute", placeholder="Azimute"),
        dbc.Input(id="furo-profundidade", placeholder="Profundidade"),
        dbc.Input(id="furo-lat", placeholder="Latitude"),
        dbc.Input(id="furo-lon", placeholder="Longitude"),
        html.Br(),
        dbc.Button("Salvar", id="btn-salvar-furo", color="success"),
        html.Br(),
        dcc.Link("⬅ Voltar", href="/furos/listar")
    ]) """
from dash import html, dcc
import dash_bootstrap_components as dbc

def layout(projetos):
    return html.Div([

        html.H2("🕳️ Novo Furo", style={"margin-bottom": "20px"}),

        dbc.Card([
            dbc.CardBody([

                html.H4("Informações Gerais", className="mb-3"),

                dbc.Row([
                    dbc.Col([
                        dbc.Label("Projeto"),
                        dbc.Select(id="furo-projeto",options=[{"label": p.nome, "value": p.id} for p in projetos])
                    ], width=6),
                ], className="mb-3"),

                dbc.Row([
                    dbc.Col([
                        dbc.Label("Nome do Furo"),
                        dbc.Input(id="furo-nome", placeholder="Ex: Furo A1")
                    ], width=6),

                    dbc.Col([
                        dbc.Label("Profundidade Alvo (m)"),
                        dbc.Input(id="furo-profundidade", type="number", placeholder="Ex: 120")
                    ], width=6),
                ], className="mb-3"),

                html.Hr(),

                html.H4("Direção", className="mb-3"),

                dbc.Row([
                    dbc.Col([
                        dbc.Label("Inclinação (°)"),
                        dbc.Input(id="furo-inclinacao", type="number", placeholder="Ex: -45")
                    ], width=6),

                    dbc.Col([
                        dbc.Label("Azimute (°)"),
                        dbc.Input(id="furo-azimute", type="number", placeholder="Ex: 120")
                    ], width=6),
                ], className="mb-3"),

                html.Hr(),

                html.H4("Localização", className="mb-3"),

                dbc.Row([
                    dbc.Col([
                        dbc.Label("Latitude"),
                        dbc.Input(id="furo-lat", type="number", placeholder="Ex: 37.9")
                    ], width=6),

                    dbc.Col([
                        dbc.Label("Longitude"),
                        dbc.Input(id="furo-lon", type="number", placeholder="Ex: -8.1")
                    ], width=6),
                ], className="mb-4"),

                dbc.Button("💾 Salvar Furo", id="btn-salvar-furo", color="success", size="lg"),

                html.Br(), html.Br(),

                dcc.Link("⬅ Voltar", href="/furos/listar")

            ])
        ])

    ])