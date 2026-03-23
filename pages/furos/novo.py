""" from dash import html, dcc
import dash_bootstrap_components as dbc

def layout(projetos):
    return html.Div([
        html.H3("Novo Furo"),
        dcc.Dropdown(
            id="furo-projeto-dropdown",
            options=[{"label": p.nome, "value": p.id} for p in projetos],
            placeholder="Selecione o projeto"
        ),
        dbc.Input(id="furo-nome", placeholder="Nome"),
        dbc.Input(id="furo-inclinacao", placeholder="Inclinação"),
        dbc.Input(id="furo-azimute", placeholder="Azimute"),
        dbc.Input(id="furo-profundidade", placeholder="Profundidade"),
        dbc.Input(id="furo-lat", placeholder="Latitude"),
        dbc.Input(id="furo-lon", placeholder="Longitude"),
        html.Br(),
        dbc.Button("Salvar", id="btn-salvar-furo", color="success"),
        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ]) """

from dash import html, dcc
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
    ])