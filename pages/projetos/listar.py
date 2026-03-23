from dash import html, dcc

def layout(projetos):
    lista = []
    for p in projetos:
        lista.append(html.Div([
            html.H5(p.nome),
            html.P(f"Cliente: {p.cliente}"),
            html.P(f"Localização: {p.localizacao}")
        ], style={"border":"1px solid #ccc","padding":"10px","margin":"5px"}))

    return html.Div([
        html.H3("Lista de Projetos"),
        html.Div(lista),
        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ])