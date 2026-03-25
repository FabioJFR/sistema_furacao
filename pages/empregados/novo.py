from dash import html, dcc
import dash_bootstrap_components as dbc

# pages/empregados/novo.py
def layout():
    return html.Div([

        html.H3("👷 Novo Empregado", className="mb-4"),

        dbc.Card([
            dbc.CardBody([

                # ================= DADOS PESSOAIS =================
                html.H5("Dados Pessoais"),

                dbc.Row([
                    dbc.Col([
                        dbc.Label("Nome"),
                        dbc.Input(id="emp-nome", placeholder="Nome completo", value="")
                    ], width=6),

                    dbc.Col([
                        dbc.Label("Número"),
                        dbc.Input(id="emp-numero", placeholder="Número interno", value="")
                    ], width=3),

                    dbc.Col([
                        dbc.Label("Idade"),
                        dbc.Input(id="emp-idade", type="number", placeholder="Idade", value=None)
                    ], width=3),
                ], className="mb-3"),

                dbc.Row([
                    dbc.Col([
                        dbc.Label("Documento"),
                        dbc.Input(id="emp-doc", placeholder="BI / Passaporte", value="")
                    ], width=6),

                    dbc.Col([
                        dbc.Label("NIF"),
                        dbc.Input(id="emp-nif", placeholder="Número fiscal", value="")
                    ], width=6),
                ], className="mb-3"),

                dbc.Row([
                    dbc.Col([
                        dbc.Label("Nacionalidade"),
                        dbc.Input(id="emp-nacionalidade", placeholder="Nacionalidade", value="")
                    ], width=6),

                    dbc.Col([
                        dbc.Label("Morada"),
                        dbc.Input(id="emp-morada", placeholder="Morada", value="")
                    ], width=6),
                ], className="mb-4"),

                # ================= DADOS PROFISSIONAIS =================
                html.H5("Dados Profissionais"),

                dbc.Row([
                    dbc.Col([
                        dbc.Label("Categoria"),
                        dbc.Input(id="emp-categoria", placeholder="Ex: Sondador, Ajudante", value="")
                    ], width=6),

                    dbc.Col([
                        dbc.Label("Salário (€)"),
                        dbc.Input(id="emp-salario", type="number", placeholder="Salário", value=None)
                    ], width=6),
                ], className="mb-3"),

                dbc.Row([
                    dbc.Col([
                        dbc.Label("NIB / IBAN"),
                        dbc.Input(id="emp-nib", placeholder="IBAN", value="")
                    ], width=12),
                ], className="mb-4"),

                # ================= BOTÕES =================
                dbc.Row([
                    dbc.Col(
                        dbc.Button(
                            "💾 Salvar",
                            id={"type": "btn-salvar-emp", "index": "novo"},
                            color="success",
                            size="lg"
                        ),
                        width="auto"
                    ),
                    dbc.Col(
                        dcc.Link("⬅ Voltar", href="/"),
                        width="auto"
                    )
                ])

            ])
        ])

    ], style={"maxWidth": "900px"})