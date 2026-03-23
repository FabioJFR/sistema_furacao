from dash import html, dcc
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
    ])