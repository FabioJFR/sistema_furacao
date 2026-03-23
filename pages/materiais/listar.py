from dash import html, dcc

def layout(materiais):
    lista = []
    for m in materiais:
        lista.append(html.Div([
            html.H5(m.nome),
            html.P(f"Tipo: {m.tipo}"),
            html.P(f"Quantidade: {m.quantidade}"),
            html.P(f"Valor: {m.valor}")
        ], style={"border":"1px solid #ccc","padding":"10px","margin":"5px"}))

    return html.Div([
        html.H3("Lista de Materiais"),
        html.Div(lista),
        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ])