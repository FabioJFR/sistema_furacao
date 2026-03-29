from dash import html, dcc

novo_layout = html.Div([
    html.H2("Adicionar Novo Empregado"),
    dcc.Input(id="empregado-nome", type="text", placeholder="Nome do Empregado"),
    dcc.Input(id="empregado-cargo", type="text", placeholder="Cargo"),
    html.Button("Guardar", id="btn-add-empregado")
])