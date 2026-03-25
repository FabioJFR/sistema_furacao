from dash import html, dcc
import dash_bootstrap_components as dbc

# pages/maquinas/novo.py
def layout(prefix="novo"):
    """
    Layout para criar ou editar uma máquina.
    prefix: string para IDs dinâmicos ('novo', '123', etc.)
    """

    return dbc.Container([

        html.H3("🚜 Nova Máquina", className="mb-4"),

        dbc.Card([
            dbc.CardBody([

                # 🔹 Identificação
                html.H5("Identificação"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Nome"),
                        dbc.Input(id={"type": "maq-nome", "index": prefix}, placeholder="Nome da máquina", value="")
                    ], width=6),

                    dbc.Col([
                        dbc.Label("Tipo"),
                        dbc.Input(id={"type": "maq-tipo", "index": prefix}, placeholder="Ex: Sonda, Compressor", value="")
                    ], width=6),
                ], className="mb-3"),

                dbc.Row([
                    dbc.Col([
                        dbc.Label("Modelo"),
                        dbc.Input(id={"type": "maq-modelo", "index": prefix}, placeholder="Modelo", value="")
                    ], width=6),

                    dbc.Col([
                        dbc.Label("Número de Série"),
                        dbc.Input(id={"type": "maq-num-serie", "index": prefix}, placeholder="Nº de série", value="")
                    ], width=6),
                ], className="mb-4"),

                # 🔹 Dados operacionais
                html.H5("Dados Operacionais"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Quilometragem / Horas"),
                        dbc.Input(id={"type": "maq-km", "index": prefix}, type="number", placeholder="Ex: 12000", value=0)
                    ], width=4),

                    dbc.Col([
                        dbc.Label("Ano de Fabricação"),
                        dbc.Input(id={"type": "maq-ano", "index": prefix}, type="number", placeholder="Ano", value=0)
                    ], width=4),

                    dbc.Col([
                        dbc.Label("Data de Compra"),
                        dbc.Input(id={"type": "maq-data-compra", "index": prefix}, type="date", value="")
                    ], width=4),
                ], className="mb-4"),

                # 🔹 Financeiro
                html.H5("Financeiro"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Valor (€)"),
                        dbc.Input(id={"type": "maq-valor", "index": prefix}, type="number", placeholder="Valor da máquina", value=0)
                    ], width=6),
                ], className="mb-4"),

                # 🔹 Botões
                dbc.Row([
                    dbc.Col(
                        dbc.Button("💾 Salvar", id={"type": "btn-salvar-maq", "index": prefix}, color="success", size="lg"),
                        width="auto"
                    ),
                    dbc.Col(
                        dcc.Link("⬅ Voltar", href="/"),
                        width="auto"
                    )
                ])

            ])
        ])

    ], style={"maxWidth": "900px"}, fluid=True)
