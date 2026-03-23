from dash import html, dcc

def layout(maquinas):
    lista = []
    for m in maquinas:
        lista.append(html.Div([
            html.H5(m.nome),
            html.P(f"Tipo: {m.tipo}"),
            html.P(f"Modelo: {m.modelo}"),
            html.P(f"Número Série: {m.numero_serie}"),
            html.P(f"KM: {m.km}"),
            html.P(f"Ano: {m.ano}")
        ], style={"border":"1px solid #ccc","padding":"10px","margin":"5px"}))

    return html.Div([
        html.H3("Lista de Máquinas"),
        html.Div(lista),
        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ])