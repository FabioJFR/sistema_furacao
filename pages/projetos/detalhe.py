from dash import html, dcc
import plotly.graph_objects as go

def layout(projeto):
    if not projeto:
        return html.H3("Projeto não encontrado")

    lat0, lon0 = projeto.localizacao
    lats = [f.localizacao[0] for f in projeto.furos]
    lons = [f.localizacao[1] for f in projeto.furos]
    nomes = [f.nome for f in projeto.furos]

    fig = go.Figure()
    fig.add_trace(go.Scattermapbox(
        lat=lats,
        lon=lons,
        mode='markers',
        text=nomes,
        marker=dict(size=10, color="blue"),
        name="Furos"
    ))
    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox_zoom=14,
        mapbox_center={"lat": lat0, "lon": lon0},
        margin={"r":0,"t":0,"l":0,"b":0}
    )

    return html.Div([
        html.H3(f"Projeto: {projeto.nome}"),
        dcc.Graph(id="mapa-furos", figure=fig),
        dcc.Store(id="furo-clicked"),  # armazena furo clicado
        dcc.Link("⬅ Voltar", href="/")
    ])