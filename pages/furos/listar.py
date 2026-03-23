""" from dash import html, dcc

def layout(projetos):
    lista = []
    for p in projetos:
        for f in p.furos:
            lista.append(html.Div([
                html.H5(f"{f.nome} (Projeto: {p.nome})"),
                html.P(f"Última medição: Prof: {f.medicoes[-1]['profundidade'] if f.medicoes else 'N/A'}"),
                html.P(f"Inclinação: {f.medicoes[-1]['inclinacao'] if f.medicoes else 'N/A'}"),
                html.P(f"Azimute: {f.medicoes[-1]['azimute'] if f.medicoes else 'N/A'}"),
                dcc.Link("🔍 Detalhes", href=f"/furo/{f.id}")
            ], style={"border":"1px solid #ccc","padding":"10px","margin":"5px"}))

    if not lista:
        lista.append(html.P("Não existem furos cadastrados."))

    return html.Div([
        html.H3("Lista de Furos"),
        html.Div(lista),
        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ]) """

from dash import html, dcc

def layout(projetos):
    lista = []
    for p in projetos:
        for f in p.furos:
            lista.append(html.Div([
                html.H5(f"{f.nome} (Projeto: {p.nome})"),
                html.P(f"Última medição: Prof: {f.medicoes[-1]['profundidade'] if f.medicoes else 'N/A'}"),
                html.P(f"Inclinação: {f.medicoes[-1]['inclinacao'] if f.medicoes else 'N/A'}"),
                html.P(f"Azimute: {f.medicoes[-1]['azimute'] if f.medicoes else 'N/A'}"),
                dcc.Link("🔍 Detalhes", href=f"/furo/{f.id}")
            ], style={"border":"1px solid #ccc","padding":"10px","margin":"5px"}))

    if not lista:
        lista.append(html.P("Não existem furos cadastrados."))

    return html.Div([
        html.H3("Lista de Furos"),
        html.Div(lista),
        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ])