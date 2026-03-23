from dash import html, dcc

def layout():
    return html.Div([
        html.H2("Novo Projeto"),
        dcc.Input(id="proj-nome", placeholder="Nome"),
        dcc.Input(id="proj-cliente", placeholder="Cliente"),
        dcc.Input(id="proj-lat", placeholder="Latitude"),
        dcc.Input(id="proj-lon", placeholder="Longitude"),
        html.Button("Guardar", id="btn-add-projeto")
    ])