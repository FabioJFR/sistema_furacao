from dash import html, dcc
import plotly.express as px
import pandas as pd

def layout(projetos):
    if not projetos:
        return html.H3("Sem projetos - crie um novo pelo menu")

    # Cria um DataFrame temporário com dados dos projetos
    df = pd.DataFrame({
        "lat": [p.localizacao[0] for p in projetos],
        "lon": [p.localizacao[1] for p in projetos],
        "nome": [p.nome for p in projetos],
        "id": [p.id for p in projetos]  # id único usado no callback
    })

    fig = px.scatter_geo(
        df,
        lat="lat",
        lon="lon",
        text="nome",
        custom_data=["id"],  # agora é aceito pelo Plotly
        projection="orthographic"  # globo 3D
    )
    fig.update_traces(marker=dict(size=10, color="red"))

    fig.update_layout(
        geo=dict(
            showland=True,
            landcolor='rgb(243,243,243)',
            oceancolor='rgb(204,224,255)',
            showcountries=True
        ),
        margin={"l":0,"r":0,"t":0,"b":0},
        height=600
    )

    return html.Div([
        html.H2("Globo de Projetos"),
        dcc.Graph(id="mapa-projetos", figure=fig)
    ])