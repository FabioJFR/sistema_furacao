from dash import Output, Input
from core.server import app
from maquinas.services import listar_maquinas

@app.callback(
    Output("maquinas-list", "children"),
    Input("dummy-input", "value")
)
def atualizar_lista(_):
    maquinas = listar_maquinas()
    return [f"{m['nome']}" for m in maquinas]