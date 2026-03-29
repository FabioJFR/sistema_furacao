from dash import html, dcc

novo_layout = html.Div([
    html.H2("Adicionar Novo Material"),
    dcc.Input(id="material-nome", type="text", placeholder="Nome do Material"),
    html.Button("Guardar", id="btn-add-material")
])