from dash import html, dcc

def layout(empregados):
    lista = []
    for e in empregados:
        lista.append(html.Div([
            html.H5(e.nome),
            html.P(f"Número: {e.numero}"),
            html.P(f"Idade: {e.idade}"),
            html.P(f"Categoria: {e.categoria}")
        ], style={"border":"1px solid #ccc","padding":"10px","margin":"5px"}))
    
    return html.Div([
        html.H3("Lista de Empregados"),
        html.Div(lista),
        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ])