""" from dash import html, dcc
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
    ]) """
from dash import html, dcc
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc

def layout(projetos):
    if not projetos:
        return html.Div([
            dbc.Alert("Sem projetos - crie um novo pelo menu", color="warning")
        ])

    # ================= DADOS =================
    total_furos = sum(len(p.furos) for p in projetos)

    df = pd.DataFrame({
        "lat": [p.localizacao[0] for p in projetos],
        "lon": [p.localizacao[1] for p in projetos],
        "nome": [p.nome for p in projetos],
        "id": [p.id for p in projetos]
    })

    # ================= MAPA =================
    fig = px.scatter_geo(
        df,
        lat="lat",
        lon="lon",
        text="nome",
        custom_data=["id"],
        projection="orthographic"
    )

    fig.update_traces(
        marker=dict(size=12, color="red"),
        textposition="top center"
    )

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

    # ================= CARDS RESUMO =================
    cards = dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4(len(projetos), className="card-title"),
                    html.P("Projetos")
                ])
            ], color="primary", inverse=True),
            width=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4(total_furos, className="card-title"),
                    html.P("Furos")
                ])
            ], color="success", inverse=True),
            width=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("Online", className="card-title"),
                    html.P("Sistema")
                ])
            ], color="dark", inverse=True),
            width=3
        )
    ], className="mb-4")

    # ================= LAYOUT FINAL =================
    return html.Div([

        html.H2("🌍 Dashboard de Perfuração", style={"margin-bottom": "20px"}),

        cards,

        dbc.Card([
            dbc.CardBody([
                html.H4("Globo de Projetos"),
                html.P("Clique num ponto para ver os detalhes do projeto."),
                dcc.Graph(id="mapa-projetos", figure=fig)
            ])
        ])

    ])