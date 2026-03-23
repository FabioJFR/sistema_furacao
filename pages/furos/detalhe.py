""" 
from dash import html, dcc
import plotly.graph_objects as go
import numpy as np

def calcular_trajetoria(furo):
    x, y, z = [0], [0], [0]
    medicoes = sorted(furo.medicoes, key=lambda m: m["data"])
    for i in range(1, len(medicoes)):
        prev, curr = medicoes[i-1], medicoes[i]
        delta = curr["profundidade"] - prev["profundidade"]
        inc = np.radians(curr["inclinacao"])
        azi = np.radians(curr["azimute"])
        x.append(x[-1] + delta*np.cos(inc)*np.sin(azi))
        y.append(y[-1] + delta*np.cos(inc)*np.cos(azi))
        z.append(z[-1] + delta*np.sin(inc))
    return x, y, z

def grafico_3d(furo):
    x, y, z = calcular_trajetoria(furo)
    fig = go.Figure()
    fig.add_trace(go.Scatter3d(x=x, y=y, z=z, mode='lines+markers'))
    fig.update_layout(scene=dict(xaxis_title='X', yaxis_title='Y', zaxis_title='Profundidade'))
    return fig

def layout(furo):
    return html.Div([
        html.H2(furo.nome),
        html.H4("Nova Medição"),
        dcc.Input(id="med-prof", type="number", placeholder="Profundidade"),
        dcc.Input(id="med-inc", type="number", placeholder="Inclinação"),
        dcc.Input(id="med-azi", type="number", placeholder="Azimute"),
        html.Button("Adicionar", id="btn-add-med"),
        html.Hr(),
        html.H4("Histórico de Medições"),
        html.Ul([
            html.Li(f"{m['data']} | {m['profundidade']}m | Inc:{m['inclinacao']} | Azi:{m['azimute']}")
            for m in furo.medicoes
        ]),
        dcc.Graph(figure=grafico_3d(furo)),
        dcc.Link("⬅ Voltar", href="/furos/listar")
    ]) """

from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import numpy as np


# ================= TRAJETÓRIA =================
def calcular_trajetoria(furo):
    x, y, z = [0], [0], [0]

    medicoes = sorted(furo.medicoes, key=lambda m: m["data"])

    for i in range(1, len(medicoes)):
        prev, curr = medicoes[i-1], medicoes[i]

        delta = curr["profundidade"] - prev["profundidade"]
        inc = np.radians(curr["inclinacao"])
        azi = np.radians(curr["azimute"])

        x.append(x[-1] + delta * np.cos(inc) * np.sin(azi))
        y.append(y[-1] + delta * np.cos(inc) * np.cos(azi))
        z.append(z[-1] + delta * np.sin(inc))

    return x, y, z


# ================= GRÁFICO 3D =================
def grafico_3d(furo):
    x, y, z = calcular_trajetoria(furo)

    fig = go.Figure()

    fig.add_trace(go.Scatter3d(
        x=x,
        y=y,
        z=z,
        mode='lines+markers',
        line=dict(width=5),
        marker=dict(size=4)
    ))

    fig.update_layout(
        scene=dict(
            xaxis_title='X',
            yaxis_title='Y',
            zaxis_title='Profundidade',
            zaxis=dict(autorange="reversed")  # profundidade para baixo
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        height=500
    )

    return fig


# ================= LAYOUT =================
def layout(furo):

    # 🔹 Última medição
    ultima = furo.medicoes[-1] if furo.medicoes else None

    return dbc.Container([

        # ================= HEADER =================
        dbc.Row([
            dbc.Col(html.H2(f"Furo: {furo.nome}"), width=8),
            dbc.Col(
                dbc.Button("⬅ Voltar", href="/furos/listar", color="secondary"),
                width=4, style={"textAlign": "right"}
            )
        ], className="mb-3"),

        # ================= INFO RÁPIDA =================
        dbc.Row([

            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H6("Profundidade Atual"),
                    html.H4(f"{ultima['profundidade']} m" if ultima else "—")
                ])
            ]), width=3),

            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H6("Inclinação"),
                    html.H4(f"{ultima['inclinacao']}°" if ultima else "—")
                ])
            ]), width=3),

            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H6("Azimute"),
                    html.H4(f"{ultima['azimute']}°" if ultima else "—")
                ])
            ]), width=3),

            dbc.Col(dbc.Card([
                dbc.CardBody([
                    html.H6("Medições"),
                    html.H4(len(furo.medicoes))
                ])
            ]), width=3),

        ], className="mb-4"),

        # ================= NOVA MEDIÇÃO =================
        dbc.Card([
            dbc.CardHeader("Adicionar Nova Medição"),
            dbc.CardBody([

                dbc.Row([
                    dbc.Col(dbc.Input(id="med-prof", type="number", placeholder="Profundidade (m)")),
                    dbc.Col(dbc.Input(id="med-inc", type="number", placeholder="Inclinação (°)")),
                    dbc.Col(dbc.Input(id="med-azi", type="number", placeholder="Azimute (°)")),
                    dbc.Col(dbc.Button("Adicionar", id="btn-add-med", color="success"))
                ])

            ])
        ], className="mb-4"),

        # ================= GRÁFICO =================
        dbc.Card([
            dbc.CardHeader("Trajetória 3D do Furo"),
            dbc.CardBody([
                dcc.Graph(figure=grafico_3d(furo))
            ])
        ], className="mb-4"),

        # ================= HISTÓRICO =================
        dbc.Card([
            dbc.CardHeader("Histórico de Medições"),
            dbc.CardBody([

                html.Div([
                    dbc.Row([
                        dbc.Col(html.B("Data")),
                        dbc.Col(html.B("Profundidade")),
                        dbc.Col(html.B("Inclinação")),
                        dbc.Col(html.B("Azimute")),
                    ], className="mb-2"),

                    html.Hr(),

                    *[
                        dbc.Row([
                            dbc.Col(m["data"]),
                            dbc.Col(f"{m['profundidade']} m"),
                            dbc.Col(f"{m['inclinacao']}°"),
                            dbc.Col(f"{m['azimute']}°"),
                        ], className="mb-1")

                        for m in sorted(furo.medicoes, key=lambda x: x["data"], reverse=True)
                    ]

                ])

            ])
        ])

    ], fluid=True)