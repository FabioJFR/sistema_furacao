from dash import Input, Output, State, dash
from core.server import app
from materiais.services import criar_material

@app.callback(
    Output("material-nome", "value"),
    Input("btn-add-material", "n_clicks"),
    State("material-nome", "value"),
    prevent_initial_call=True
)
def add_material(n_clicks, nome):
    if not n_clicks or not nome:
        return dash.no_update
    criar_material(nome)
    return ""