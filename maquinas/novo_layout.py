from dash import html, dcc

novo_layout = html.Div([
    html.H2("Adicionar Nova Máquina"),
    dcc.Input(id="maquina-nome", type="text", placeholder="Nome da Máquina"),
    html.Button("Guardar", id="btn-add-maquina")
])