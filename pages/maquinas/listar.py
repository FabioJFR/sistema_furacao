from dash import html, dcc
import dash_bootstrap_components as dbc

# pages/maquinas/listar.py
def layout(maquinas, prefix="listar"):
    """
    Layout para listar máquinas.
    prefix: string para IDs dinâmicos ('listar', 'novo', '123')
    """

    # 🔹 Estatísticas
    total = len(maquinas)
    tipos = list(set([getattr(m, "tipo", "") for m in maquinas]))

    operacionais = len([m for m in maquinas if getattr(m, "estado", "operacional") == "operacional"])
    manutencao = len([m for m in maquinas if getattr(m, "estado", "") == "manutencao"])

    stats = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Total Máquinas"),
            html.H4(total, id={"type": "total-maquinas", "index": prefix})
        ])), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Operacionais"),
            html.H4(operacionais, id={"type": "operacionais", "index": prefix})
        ])), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Em Manutenção"),
            html.H4(manutencao, id={"type": "manutencao", "index": prefix})
        ])), width=3),
    ], className="mb-4")

    # 🔹 Filtros
    filtros = dbc.Row([
        dbc.Col(
            dbc.Input(id={"type": "filtro-maq-nome", "index": prefix}, placeholder="🔍 Procurar máquina...", value=""),
            width=6
        ),
        dbc.Col(
            dcc.Dropdown(
                id={"type": "filtro-maq-tipo", "index": prefix},
                options=[{"label": t, "value": t} for t in tipos],
                placeholder="Filtrar por tipo",
                value=None
            ),
            width=6
        )
    ], className="mb-4")

    # 🔹 Cards de máquinas
    cards = []

    for m in maquinas:

        estado = str(getattr(m, "estado", "operacional")).lower()

        cor_estado = {
            "operacional": "success",
            "manutencao": "warning",
            "parada": "danger"
        }.get(estado, "secondary")

        card = dbc.Card(
            dbc.CardBody([

                html.H5(getattr(m, "nome", "—"), id={"type": "maq-nome", "index": getattr(m, "numero_serie", m)}),
                dbc.Badge(estado.upper(), color=cor_estado, className="mb-2", id={"type": "maq-estado", "index": getattr(m, "numero_serie", m)}),
                html.Br(),

                html.P(f"Tipo: {getattr(m, 'tipo', '—')}", id={"type": "maq-tipo", "index": getattr(m, "numero_serie", m)}),
                html.P(f"Modelo: {getattr(m, 'modelo', '—')}", id={"type": "maq-modelo", "index": getattr(m, "numero_serie", m)}),
                html.P(f"Nº Série: {getattr(m, 'numero_serie', '—')}", id={"type": "maq-num-serie", "index": getattr(m, "numero_serie", m)}),

                html.Hr(),

                html.P(f"KM/Horas: {getattr(m, 'km', 0)}", id={"type": "maq-km", "index": getattr(m, "numero_serie", m)}),
                html.P(f"Ano: {getattr(m, 'ano', 0)}", id={"type": "maq-ano", "index": getattr(m, "numero_serie", m)}),

                html.Div([
                    dbc.Button("👁 Ver", size="sm", color="info", id={"type": "btn-ver-maq", "index": getattr(m, "numero_serie", m)}),
                    dbc.Button("✏ Editar", size="sm", color="warning", className="mx-1", id={"type": "btn-editar-maq", "index": getattr(m, "numero_serie", m)}),
                    dbc.Button("🛠 Manutenção", size="sm", color="secondary", id={"type": "btn-manut-maq", "index": getattr(m, "numero_serie", m)}),
                ])

            ]),
            style={"margin": "5px"}
        )

        cards.append(dbc.Col(card, width=4))

    if not cards:
        cards.append(html.P("Sem máquinas cadastradas."))

    return dbc.Container([
        html.H3("🚜 Painel de Máquinas"),

        stats,
        filtros,

        dbc.Row(cards),

        html.Br(),
        dcc.Link("⬅ Voltar", href="/", id={"type": "link-voltar", "index": prefix})
    ], fluid=True)