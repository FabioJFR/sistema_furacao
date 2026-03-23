""" from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc

def layout():
    return html.Div([
        html.H3("Novo Empregado"),
        dbc.Input(id="emp-nome", placeholder="Nome"),
        dbc.Input(id="emp-numero", placeholder="Número"),
        dbc.Input(id="emp-idade", placeholder="Idade"),
        dbc.Input(id="emp-doc", placeholder="Documento"),
        dbc.Input(id="emp-nib", placeholder="NIB"),
        dbc.Input(id="emp-morada", placeholder="Morada"),
        dbc.Input(id="emp-nacionalidade", placeholder="Nacionalidade"),
        dbc.Input(id="emp-nif", placeholder="NIF"),
        dbc.Input(id="emp-categoria", placeholder="Categoria"),
        dbc.Input(id="emp-salario", placeholder="Salário"),
        html.Br(),
        dbc.Button("Salvar", id="btn-salvar-emp", color="success"),
        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ]) """


from dash import html, dcc
import dash_bootstrap_components as dbc

def layout():
    return html.Div([

        html.H3("👷 Novo Empregado", className="mb-4"),

        dbc.Card([
            dbc.CardBody([

                # 🔹 Dados pessoais
                html.H5("Dados Pessoais"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Nome"),
                        dbc.Input(id="emp-nome", placeholder="Nome completo")
                    ], width=6),

                    dbc.Col([
                        dbc.Label("Número"),
                        dbc.Input(id="emp-numero", placeholder="Número interno")
                    ], width=3),

                    dbc.Col([
                        dbc.Label("Idade"),
                        dbc.Input(id="emp-idade", type="number", placeholder="Idade")
                    ], width=3),
                ], className="mb-3"),

                dbc.Row([
                    dbc.Col([
                        dbc.Label("Documento"),
                        dbc.Input(id="emp-doc", placeholder="BI / Passaporte")
                    ], width=6),

                    dbc.Col([
                        dbc.Label("NIF"),
                        dbc.Input(id="emp-nif", placeholder="Número fiscal")
                    ], width=6),
                ], className="mb-3"),

                dbc.Row([
                    dbc.Col([
                        dbc.Label("Nacionalidade"),
                        dbc.Input(id="emp-nacionalidade", placeholder="Nacionalidade")
                    ], width=6),

                    dbc.Col([
                        dbc.Label("Morada"),
                        dbc.Input(id="emp-morada", placeholder="Morada")
                    ], width=6),
                ], className="mb-4"),

                # 🔹 Dados profissionais
                html.H5("Dados Profissionais"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Categoria"),
                        dbc.Input(id="emp-categoria", placeholder="Ex: Sondador, Ajudante")
                    ], width=6),

                    dbc.Col([
                        dbc.Label("Salário (€)"),
                        dbc.Input(id="emp-salario", type="number", placeholder="Salário")
                    ], width=6),
                ], className="mb-3"),

                dbc.Row([
                    dbc.Col([
                        dbc.Label("NIB / IBAN"),
                        dbc.Input(id="emp-nib", placeholder="IBAN")
                    ], width=12),
                ], className="mb-4"),

                # 🔹 Botões
                dbc.Row([
                    dbc.Col(
                        dbc.Button("💾 Salvar", id="btn-salvar-emp", color="success", size="lg"),
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