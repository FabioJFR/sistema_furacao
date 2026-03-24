from dash import html, dcc
import plotly.express as px
import dash_bootstrap_components as dbc

def layout(projeto):
    if not projeto.furos:
        return dbc.Container([
            dbc.Row([dbc.Col(html.H3(f"Projeto: {projeto.nome}"), width=12)]),
            dbc.Row([dbc.Col(html.P("Sem furos cadastrados"), width=12)]),
            dbc.Row([dbc.Col(dcc.Link("⬅ Voltar", href="/"), width=12)])
        ], fluid=True)

    # filtra furos válidos
    furos_validos = [f for f in projeto.furos if f.localizacao and len(f.localizacao) == 2]

    if not furos_validos:
        return dbc.Container([
            dbc.Row([dbc.Col(html.H3(f"Projeto: {projeto.nome}"), width=12)]),
            dbc.Row([dbc.Col(html.P("Sem furos válidos para mostrar no mapa"), width=12)]),
            dbc.Row([dbc.Col(dcc.Link("⬅ Voltar", href="/"), width=12)])
        ], fluid=True)

    latitudes = [f.localizacao[0] for f in furos_validos]
    longitudes = [f.localizacao[1] for f in furos_validos]
    ids = [f.id for f in furos_validos]

    # hovertemplate personalizado
    hover_template = [
        f"Nome: {f.nome}<br>Profundidade Alvo: {f.profundidade_alvo} m<br>Inclinação: {f.inclinacao}°<extra></extra>"
        for f in furos_validos
    ]

    fig = px.scatter_mapbox(
        lat=latitudes,
        lon=longitudes,
        custom_data=[ids],
        zoom=10,
        height=600
    )

    fig.update_traces(
        marker=dict(size=10, color="blue"),
        hovertemplate=hover_template  # só aparece na janela popup
    )

    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    return dbc.Container([
        dbc.Row([dbc.Col(html.H3(f"Projeto: {projeto.nome}"), width=12)]),
        dbc.Row([dbc.Col(dcc.Graph(id="mapa-furos", figure=fig), width=12)]),
        dbc.Row([dbc.Col(dcc.Link("⬅ Voltar", href="/"), width=12)])
    ], fluid=True)