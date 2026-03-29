from dash import Input, Output, State, dash
from core.server import app
from empregados.services import criar_empregado

@app.callback(
    Output("empregado-nome", "value"),
    Input("btn-add-empregado", "n_clicks"),
    State("empregado-nome", "value"),
    State("empregado-cargo", "value"),
    prevent_initial_call=True
)
def add_empregado(n_clicks, nome, cargo):
    if not n_clicks or not nome or not cargo:
        return dash.no_update
    criar_empregado(nome, cargo)
    return ""