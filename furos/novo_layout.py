# furos/novo_layout.py
from dash import html, dcc

def novo_layout():
    return html.Div([
        html.H2("Novo Furo"),
        dcc.Input(id="furo-nome", placeholder="Nome do Furo"),
        dcc.Input(id="furo-local_sondagem", placeholder="Local Sondagem"),
        dcc.Input(id="furo-prof_alvo", type="number", placeholder="Profundidade Alvo"),
        dcc.Input(id="furo-inc", type="number", placeholder="Inclinação"),
        dcc.Input(id="furo-azi", type="number", placeholder="Azimute"),
        dcc.Input(id="furo-lat", type="number", placeholder="Latitude"),
        dcc.Input(id="furo-lon", type="number", placeholder="Longitude"),
        html.Button("Adicionar Furo", id="btn-add-furo"),
        html.Div(id="furo-msg")
    ])