""" from dash import html, dcc
import dash_bootstrap_components as dbc
from utils.alertas import analisar_empregado  # função de alertas automáticos

def layout(empregados):

    # 🔹 Estatísticas
    total = len(empregados)
    categorias = list(set([e.categoria for e in empregados if hasattr(e, "categoria")]))

    stats = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Total"),
            html.H4(total)
        ])), width=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Categorias"),
            html.H4(len(categorias))
        ])), width=3),
    ], className="mb-4")

    # 🔹 Filtros
    filtros = dbc.Row([
        dbc.Col(
            dbc.Input(id="filtro-nome", placeholder="🔍 Procurar por nome..."),
            width=6
        ),
        dbc.Col(
            dcc.Dropdown(
                id="filtro-categoria",
                options=[{"label": c, "value": c} for c in categorias],
                placeholder="Filtrar por categoria"
            ),
            width=6
        )
    ], className="mb-4")

    # 🔹 Lista de empregados (cards)
    cards = []

    for e in empregados:
        # Alertas automáticos
        alertas = analisar_empregado(e)

        card = dbc.Card(
            dbc.CardBody([
                html.H5(e.nome),

                dbc.Badge(e.categoria, color="primary", className="mb-2"),
                html.Br(),

                html.P(f"Número: {e.numero}"),
                html.P(f"Idade: {e.idade}"),

                # 🔹 Alertas automáticos
                html.Div([
                    dbc.Alert(a, color="danger", className="p-1 mb-1") for a in alertas
                ]) if alertas else None,

                # 🔹 Botões de ação
                html.Div([
                    dbc.Button("👁 Ver", size="sm", color="info"),
                    dbc.Button("✏ Editar", size="sm", color="warning", className="mx-1"),
                    dbc.Button("🗑 Remover", size="sm", color="danger")
                ])
            ]),
            style={"margin": "5px"}
        )

        cards.append(dbc.Col(card, width=4))

    if not cards:
        cards.append(html.P("Sem empregados cadastrados."))

    return html.Div([
        html.H3("👷 Painel de Empregados"),

        stats,
        filtros,

        dbc.Row(cards),

        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ]) """

from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from datetime import datetime
from utils.alertas import analisar_empregado

def layout(empregados):
    # 🔹 Estatísticas
    total = len(empregados)
    categorias = list(set([e.categoria for e in empregados if hasattr(e, "categoria")]))
    
    stats = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Total"),
            html.H4(total)
        ])), width=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Categorias"),
            html.H4(len(categorias))
        ])), width=3),
    ], className="mb-4")
    
    # 🔹 Filtros e Ordenação
    filtros = dbc.Row([
        dbc.Col(
            dbc.Input(id="filtro-nome", placeholder="🔍 Procurar por nome..."),
            width=4
        ),
        dbc.Col(
            dcc.Dropdown(
                id="filtro-categoria",
                options=[{"label": c, "value": c} for c in categorias],
                placeholder="Filtrar por categoria"
            ),
            width=4
        ),
        dbc.Col(
            dcc.Dropdown(
                id="ordenar-por",
                options=[
                    {"label": "Salário", "value": "salario"},
                    {"label": "Tempo de Empresa", "value": "tempo"},
                    {"label": "Metros Furados", "value": "metros"}
                ],
                placeholder="Ordenar por"
            ),
            width=4
        )
    ], className="mb-4")
    
    # 🔹 Função auxiliar para ordenar empregados
    def ordenar(emp_list, criterio):
        if criterio == "salario":
            return sorted(emp_list, key=lambda e: getattr(e, "salario", 0), reverse=True)
        elif criterio == "tempo":
            return sorted(emp_list, key=lambda e: datetime.fromisoformat(e.data_inicio_contrato), reverse=False)
        elif criterio == "metros":
            return sorted(emp_list, key=lambda e: getattr(e, "metros_furados", 0), reverse=True)
        return emp_list
    
    # 🔹 Lista de cards
    def criar_cards(emp_list):
        cards = []
        for e in emp_list:
            alertas = analisar_empregado(e)
            card = dbc.Card(
                dbc.CardBody([
                    html.H5(e.nome),
                    dbc.Badge(e.categoria, color="primary", className="mb-2"),
                    html.Br(),
                    html.P(f"Número: {e.numero}"),
                    html.P(f"Idade: {e.idade}"),
                    html.P(f"Salário: {getattr(e, 'salario', 0):.2f}"),
                    html.P(f"Metros Furados: {getattr(e, 'metros_furados', 0):.2f}"),
                    html.P(f"Início Contrato: {e.data_inicio_contrato}"),
                    # Alertas
                    html.Div([dbc.Alert(a, color="danger", className="p-1 mb-1") for a in alertas]) if alertas else None,
                    # Botões
                    html.Div([
                        dbc.Button("👁 Ver", size="sm", color="info"),
                        dbc.Button("✏ Editar", size="sm", color="warning", className="mx-1"),
                        dbc.Button("🗑 Remover", size="sm", color="danger")
                    ])
                ]),
                style={"margin": "5px"}
            )
            cards.append(dbc.Col(card, width=4))
        if not cards:
            cards.append(html.P("Sem empregados cadastrados."))
        return cards
    
    # 🔹 Layout final
    cards = criar_cards(empregados)  # inicial sem filtros
    return html.Div([
        html.H3("👷 Painel de Empregados"),
        stats,
        filtros,
        dbc.Row(cards, id="cards-empregados"),
        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ])