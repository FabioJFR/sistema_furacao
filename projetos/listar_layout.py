from dash import html, dcc

def listar_layout():
    return html.Div([
        html.H2("Projetos"),
        dcc.Dropdown(id="select-projeto", placeholder="Selecione um projeto"),
        html.Div(id="projetos-list")
    ])