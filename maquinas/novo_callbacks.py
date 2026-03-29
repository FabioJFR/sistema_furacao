from dash import Input, Output, State, dash
from core.server import app
from maquinas.services import criar_maquina

@app.callback(
    Output("maquina-nome", "value"),
    Input("btn-add-maquina", "n_clicks"),
    State("maquina-nome", "value"),
    prevent_initial_call=True
)
def add_maquina(n_clicks, nome):
    if not n_clicks or not nome:
        return dash.no_update
    criar_maquina(nome)
    return ""