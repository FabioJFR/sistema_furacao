from dash import Input, Output, State, dash
from core.server import app
from projetos.services import criar_projeto

@app.callback(
    Output("projeto-nome", "value"),
    Input("btn-add-projeto", "n_clicks"),
    State("projeto-nome", "value"),
    State("projeto-descricao", "value"),
    prevent_initial_call=True
)
def add_projeto(n_clicks, nome, descricao):
    if not n_clicks or not nome:
        return dash.no_update
    criar_projeto(nome, descricao)
    return ""