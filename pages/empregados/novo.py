from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc

def layout():
    return html.Div([
        html.H3("Novo Empregado"),
        dbc.Input(id="emp-nome", placeholder="Nome"),
        dbc.Input(id="emp-numero", placeholder="Número"),
        dbc.Input(id="emp-idade", placeholder="Idade"),
        dbc.Input(id="emp-doc", placeholder="Documento"),
        dbc.Input(id="emp-nib", placeholder="NIB"),
        dbc.Input(id="emp-morada", placeholder="Morada"),
        dbc.Input(id="emp-nacionalidade", placeholder="Nacionalidade"),
        dbc.Input(id="emp-nif", placeholder="NIF"),
        dbc.Input(id="emp-categoria", placeholder="Categoria"),
        dbc.Input(id="emp-salario", placeholder="Salário"),
        html.Br(),
        dbc.Button("Salvar", id="btn-salvar-emp", color="success"),
        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ])