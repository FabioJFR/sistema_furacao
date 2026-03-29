from dash import Output
from core.server import app
from projetos.services import listar_projetos

@app.callback(
    Output("projetos-list", "children"),
    Input("dummy-input", "value")  # pode ser substituído por evento real
)
def atualizar_lista(_):
    projetos = listar_projetos()
    return [f"{p['nome']}" for p in projetos]