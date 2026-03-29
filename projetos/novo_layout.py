from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from projetos.services import listar_projetos

# 🔹 NOVO
def novo_layout():
    return dbc.Container([

        html.H2("📁 Novo Projeto"),

        dbc.Input(id="proj-nome", placeholder="Nome"),
        dbc.Input(id="proj-cliente", placeholder="Cliente", className="mt-2"),
        dbc.Input(id="proj-lat", type="number", placeholder="Latitude", className="mt-2"),
        dbc.Input(id="proj-lon", type="number", placeholder="Longitude", className="mt-2"),

        dbc.Button("Guardar", id="btn-add-proj", className="mt-3"),

        html.Br(), html.Br(),
        dcc.Link("⬅ Voltar", href="/projetos/listar")

    ], style={"maxWidth": "600px"})


# 🔹 LISTAR + MAPA
def listar_layout():

    projetos = listar_projetos()

    if not projetos:
        return html.H3("Sem projetos")

    lats = [p[3] for p in projetos]
    lons = [p[4] for p in projetos]
    nomes = [p[1] for p in projetos]
    ids = [p[0] for p in projetos]

    fig = go.Figure()
    fig.add_trace(go.Scattermapbox(
        lat=lats,
        lon=lons,
        text=nomes,
        customdata=ids,
        mode='markers',
        marker=dict(size=12, color="red"),
        hovertemplate="<b>%{text}</b><extra></extra>"
    ))

    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox_zoom=5,
        mapbox_center={"lat": 39.5, "lon": -8},
        height=500
    )

    # 🔹 lista cards
    cards = []
    for p in projetos:
        cards.append(
            dbc.Card(
                dbc.CardBody([
                    html.H5(p[1]),
                    html.P(f"Cliente: {p[2]}"),
                    dcc.Link("📍 Ver", href=f"/projeto/{p[0]}")
                ]),
                className="mb-2"
            )
        )

    return html.Div([
        html.H3("📁 Projetos"),
        dcc.Graph(id="mapa-projetos", figure=fig),
        html.Hr(),
        *cards
    ])


# 🔹 DETALHE (MAPA)
def detalhe_layout(projeto):

    fig = go.Figure()
    fig.add_trace(go.Scattermapbox(
        lat=[projeto[3]],
        lon=[projeto[4]],
        mode='markers',
        marker=dict(size=14, color="blue")
    ))

    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox_zoom=10,
        mapbox_center={"lat": projeto[3], "lon": projeto[4]},
        height=500
    )

    return html.Div([
        html.H3(projeto[1]),
        html.P(f"Cliente: {projeto[2]}"),
        dcc.Graph(figure=fig),
        dcc.Link("⬅ Voltar", href="/projetos/listar")
    ])