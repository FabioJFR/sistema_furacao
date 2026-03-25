from dash import html, dcc
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc

# pages/home.py
def layout(projetos, prefix=""):
    """
    projetos: lista de projetos
    ip: IP dinâmico para links
    prefix: prefixo para IDs dinâmicos
    """
    if not projetos:
        return html.Div([
            dbc.Alert("Sem projetos - crie um novo pelo menu", color="warning", id=f"{prefix}alert-sem-projetos")
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
                    html.H4(len(projetos), className="card-title", id=f"{prefix}card-projetos"),
                    html.P("Projetos")
                ])
            ], color="primary", inverse=True),
            width=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4(total_furos, className="card-title", id=f"{prefix}card-furos"),
                    html.P("Furos")
                ])
            ], color="success", inverse=True),
            width=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.H4("Online", className="card-title", id=f"{prefix}card-sistema"),
                    html.P("Sistema")
                ])
            ], color="dark", inverse=True),
            width=3
        )
    ], className="mb-4")

    # ================= LAYOUT FINAL =================
    return html.Div([

        html.H2("🌍 Dashboard de Perfuração", style={"margin-bottom": "20px"}, id=f"{prefix}titulo-home"),

        cards,

        dbc.Card([
            dbc.CardBody([
                html.H4("Globo de Projetos"),
                html.P("Clique num ponto para ver os detalhes do projeto."),
                dcc.Graph(id=f"{prefix}mapa-projetos", figure=fig)
            ])
        ])

    ])