from dash import html, dcc
import plotly.express as px

def layout(projeto):
    if not projeto.furos:
        return html.Div([
            html.H3(f"Projeto: {projeto.nome}"),
            html.P("Sem furos cadastrados"),
            dcc.Link("⬅ Voltar", href="/")
        ])

    fig = px.scatter_mapbox(
        lat=[f.localizacao[0] for f in projeto.furos],
        lon=[f.localizacao[1] for f in projeto.furos],
        text=[f.nome for f in projeto.furos],
        zoom=10,
        height=600
    )
    fig.update_layout(mapbox_style="open-street-map")

    return html.Div([
        html.H3(f"Projeto: {projeto.nome}"),
        dcc.Graph(id="mapa-furos", figure=fig),
        dcc.Link("⬅ Voltar", href="/")
    ])