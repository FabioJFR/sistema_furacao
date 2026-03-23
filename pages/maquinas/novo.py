from dash import html, dcc
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
    ])