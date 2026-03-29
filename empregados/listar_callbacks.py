from dash import Output
from core.server import app
from empregados.services import listar_empregados

@app.callback(
    Output("empregados-list", "children"),
    Input("dummy-input", "value")
)
def atualizar_lista(_):
    empregados = listar_empregados()
    return [f"{e['nome']} - {e['cargo']}" for e in empregados]