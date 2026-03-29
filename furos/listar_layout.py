# furos/listar_layout.py
from dash import html, dcc

def listar_layout():
    return html.Div([
        html.H2("Furos do Projeto"),
        dcc.Dropdown(id="select-projeto", placeholder="Selecione um projeto"),
        html.Div(id="furos-list")
    ])