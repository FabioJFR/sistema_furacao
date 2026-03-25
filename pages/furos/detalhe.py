from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import numpy as np

# ================= TRAJETÓRIA =================
def calcular_trajetoria(furo, max_pontos=200):
    x, y, z = [0], [0], [0]

    medicoes = sorted(getattr(furo, "medicoes", []), key=lambda m: getattr(m, "data", 0))[-max_pontos:]

    for i in range(1, len(medicoes)):
        prev, curr = medicoes[i-1], medicoes[i]

        delta = getattr(curr, "profundidade", 0) - getattr(prev, "profundidade", 0)
        inc = np.radians(getattr(curr, "inclinacao", 0))
        azi = np.radians(getattr(curr, "azimute", 0))

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
        line=dict(width=5, color=z, colorscale='Viridis', colorbar=dict(title="Profundidade")),
        marker=dict(size=4, color=z, colorscale='Viridis')
    ))

    fig.update_layout(
        scene=dict(
            xaxis_title='X',
            yaxis_title='Y',
            zaxis_title='Profundidade',
            zaxis=dict(autorange="reversed")
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        height=500
    )

    return fig

# ================= LAYOUT =================
def layout(furo):
    ultima = getattr(furo, "medicoes", [])[-1] if getattr(furo, "medicoes", []) else None
    furo_id = getattr(furo, "id", "desconhecido")

    return dbc.Container([

        # ================= HEADER =================
        dbc.Row([
            dbc.Col(html.H2(f"Furo: {getattr(furo, 'nome', '—')}"), width=8),
            dbc.Col(
                dbc.Button("⬅ Voltar", href="/furos/listar", color="secondary"),
                width=4, style={"textAlign": "right"}
            )
        ], className="mb-3"),

        # ================= INFO RÁPIDA =================
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H6("Objetivo de Profundidade"),
                html.H4(f"{getattr(furo, 'profundidade_alvo', '—')} m")
            ])), width=3),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H6("Inclinação"),
                html.H4(f"{getattr(furo, 'inclinacao', '—')}°")
            ])), width=3),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H6("Azimute"),
                html.H4(f"{getattr(furo, 'azimute', '—')}°")
            ])), width=3),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H6("Medições"),
                html.H4(len(getattr(furo, "medicoes", [])))
            ])), width=3),
        ], className="mb-4"),

        # ================= NOVA MEDIÇÃO =================
        dbc.Card([
            dbc.CardHeader("Adicionar Nova Medição"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col(dbc.Input(id={"type": "med-prof", "index": furo_id}, type="number", placeholder="Profundidade (m)", min=0)),
                    dbc.Col(dbc.Input(id={"type": "med-inc", "index": furo_id}, type="number", placeholder="Inclinação (°)")),
                    dbc.Col(dbc.Input(id={"type": "med-azi", "index": furo_id}, type="number", placeholder="Azimute (°)")),
                    dbc.Col(dbc.Input(id={"type": "med-mag", "index": furo_id}, type="number", placeholder="Magnetismo")),
                    dbc.Col(dbc.Button("Adicionar", id={"type": "btn-add-med", "index": furo_id}, color="success"))
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
                        dbc.Col(html.B("#")),
                        dbc.Col(html.B("Data")),
                        dbc.Col(html.B("Profundidade")),
                        dbc.Col(html.B("Inclinação")),
                        dbc.Col(html.B("Azimute")),
                        dbc.Col(html.B("Magnetismo"))
                    ], className="mb-2"),
                    html.Hr(),
                    *[
                        dbc.Row([
                            dbc.Col(i),
                            dbc.Col(getattr(m, "data", "—")),
                            dbc.Col(f"{getattr(m, 'profundidade', 0)} m"),
                            dbc.Col(f"{getattr(m, 'inclinacao', 0)}°"),
                            dbc.Col(f"{getattr(m, 'azimute', 0)}°"),
                            dbc.Col(f"{getattr(m, 'magnetismo', '—')}")
                        ], className="mb-1")
                        for i, m in enumerate(sorted(getattr(furo, "medicoes", []), key=lambda x: getattr(x, "data", 0), reverse=True), 1)
                    ]
                ])
            ])
        ])

    ], fluid=True)