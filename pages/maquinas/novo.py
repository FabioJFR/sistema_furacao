""" from dash import html, dcc
import dash_bootstrap_components as dbc

def layout():
    return html.Div([
        html.H3("Nova Máquina"),
        dbc.Input(id="maq-nome", placeholder="Nome"),
        dbc.Input(id="maq-tipo", placeholder="Tipo"),
        dbc.Input(id="maq-modelo", placeholder="Modelo"),
        dbc.Input(id="maq-num-serie", placeholder="Número de Série"),
        dbc.Input(id="maq-km", placeholder="Quilometragem"),
        dbc.Input(id="maq-ano", placeholder="Ano de Fabricação"),
        dbc.Input(id="maq-data-compra", placeholder="Data de Compra"),
        dbc.Input(id="maq-valor", placeholder="Valor"),
        html.Br(),
        dbc.Button("Salvar", id="btn-salvar-maq", color="success"),
        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ]) """

from dash import html, dcc
import dash_bootstrap_components as dbc

def layout():
    return html.Div([

        html.H3("🚜 Nova Máquina", className="mb-4"),

        dbc.Card([
            dbc.CardBody([

                # 🔹 Identificação
                html.H5("Identificação"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Nome"),
                        dbc.Input(id="maq-nome", placeholder="Nome da máquina")
                    ], width=6),

                    dbc.Col([
                        dbc.Label("Tipo"),
                        dbc.Input(id="maq-tipo", placeholder="Ex: Sonda, Compressor")
                    ], width=6),
                ], className="mb-3"),

                dbc.Row([
                    dbc.Col([
                        dbc.Label("Modelo"),
                        dbc.Input(id="maq-modelo", placeholder="Modelo")
                    ], width=6),

                    dbc.Col([
                        dbc.Label("Número de Série"),
                        dbc.Input(id="maq-num-serie", placeholder="Nº de série")
                    ], width=6),
                ], className="mb-4"),

                # 🔹 Dados operacionais
                html.H5("Dados Operacionais"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Quilometragem / Horas"),
                        dbc.Input(id="maq-km", type="number", placeholder="Ex: 12000")
                    ], width=4),

                    dbc.Col([
                        dbc.Label("Ano de Fabricação"),
                        dbc.Input(id="maq-ano", type="number", placeholder="Ano")
                    ], width=4),

                    dbc.Col([
                        dbc.Label("Data de Compra"),
                        dbc.Input(id="maq-data-compra", type="date")
                    ], width=4),
                ], className="mb-4"),

                # 🔹 Financeiro
                html.H5("Financeiro"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Valor (€)"),
                        dbc.Input(id="maq-valor", type="number", placeholder="Valor da máquina")
                    ], width=6),
                ], className="mb-4"),

                # 🔹 Botões
                dbc.Row([
                    dbc.Col(
                        dbc.Button("💾 Salvar", id="btn-salvar-maq", color="success", size="lg"),
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