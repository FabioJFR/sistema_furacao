# furos/listar_callbacks.py
from dash import Input, Output
from core.app import app

@app.callback(
    Output("furos-list", "children"),
    Input("select-projeto", "value")
)
def listar_furos(projeto_id):
    if not projeto_id:
        return "Selecione um projeto"
    # Aqui você chamaria a função do serviço para buscar furos do projeto
    # Exemplo:
    # furos = get_furos(projeto_id)
    furos = ["Furo A", "Furo B", "Furo C"]
    return [html.Div(furo) for furo in furos]