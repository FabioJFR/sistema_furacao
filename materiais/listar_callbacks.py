from dash import Input, Output
from core.server import app
from materiais.services import listar_materiais

@app.callback(
    Output("materiais-list", "children"),
    Input("dummy-input", "value")
)
def atualizar_lista(_):
    materiais = listar_materiais()
    return [f"{m['nome']}" for m in materiais]