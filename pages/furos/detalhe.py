""" from dash import html, dcc
import dash_bootstrap_components as dbc
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
        x.append(x[-1] + delta * np.cos(inc) * np.sin(azi))
        y.append(y[-1] + delta * np.cos(inc) * np.cos(azi))
        z.append(z[-1] + delta * np.sin(inc))
    return x, y, z

def grafico_3d(furo):
    x, y, z = calcular_trajetoria(furo)
    fig = go.Figure()
    fig.add_trace(go.Scatter3d(x=x, y=y, z=z, mode='lines+markers'))
    fig.update_layout(scene=dict(xaxis_title='X', yaxis_title='Y', zaxis_title='Profundidade'),
                      margin=dict(l=0, r=0, t=0, b=0))
    return fig

def layout(furo):
    return html.Div([
        html.H2(furo.nome),
        html.H4("Nova Medição"),
        dbc.Input(id="med-prof", type="number", placeholder="Profundidade"),
        dbc.Input(id="med-inc", type="number", placeholder="Inclinação"),
        dbc.Input(id="med-azi", type="number", placeholder="Azimute"),
        html.Br(),
        dbc.Button("Adicionar Medição", id="btn-add-med", color="success"),
        html.Hr(),
        html.H4("Histórico de Medições"),
        html.Ul([
            html.Li(f"{m['data']} | Prof: {m['profundidade']} | Inc: {m['inclinacao']} | Azi: {m['azimute']}")
            for m in furo.medicoes
        ]),
        html.Hr(),
        html.H4("Trajetória 3D do Furo"),
        dcc.Graph(figure=grafico_3d(furo)),
        html.Br(),
        dcc.Link("⬅ Voltar para lista de furos", href="/furos/listar")
    ]) """

""" from dash import html, dcc
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
        html.Ul([html.Li(f"{m['data']} | {m['profundidade']}m | Inc:{m['inclinacao']} | Azi:{m['azimute']}") for m in furo.medicoes]),
        dcc.Graph(figure=grafico_3d(furo)),
        dcc.Link("⬅ Voltar", href="/furos/listar")
    ]) """

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
    ])