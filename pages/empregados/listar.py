from dash import html, dcc
import dash_bootstrap_components as dbc
from datetime import datetime
from utils.alertas import analisar_empregado

# pages/empregados/listar.py
def layout(empregados):
    # ================= ESTATÍSTICAS =================
    total = len(empregados)
    categorias = list(set([getattr(e, "categoria", "") for e in empregados if hasattr(e, "categoria")]))
    
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
    
    # ================= FILTROS E ORDENAÇÃO =================
    filtros = dbc.Row([
        dbc.Col(
            dbc.Input(id="filtro-nome", placeholder="🔍 Procurar por nome...", value=""),
            width=4
        ),
        dbc.Col(
            dcc.Dropdown(
                id="filtro-categoria",
                options=[{"label": c, "value": c} for c in categorias],
                placeholder="Filtrar por categoria",
                value=""
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
                placeholder="Ordenar por",
                value=""
            ),
            width=4
        )
    ], className="mb-4")
    
    # ================= FUNÇÃO AUXILIAR DE ORDENAÇÃO =================
    def ordenar(emp_list, criterio):
        if criterio == "salario":
            return sorted(emp_list, key=lambda e: getattr(e, "salario", 0), reverse=True)
        elif criterio == "tempo":
            return sorted(
                emp_list, 
                key=lambda e: datetime.fromisoformat(getattr(e, "data_inicio_contrato", datetime.now().isoformat())), 
                reverse=False
            )
        elif criterio == "metros":
            return sorted(emp_list, key=lambda e: getattr(e, "metros_furados", 0), reverse=True)
        return emp_list
    
    # ================= FUNÇÃO AUXILIAR DE CRIAÇÃO DE CARDS =================
    def criar_cards(emp_list):
        cards = []
        for e in emp_list:
            alertas = analisar_empregado(e)
            card = dbc.Card(
                dbc.CardBody([
                    html.H5(getattr(e, "nome", "Sem Nome")),
                    dbc.Badge(getattr(e, "categoria", "N/A"), color="primary", className="mb-2"),
                    html.Br(),
                    html.P(f"Número: {getattr(e, 'numero', '')}"),
                    html.P(f"Idade: {getattr(e, 'idade', '')}"),
                    html.P(f"Salário: {getattr(e, 'salario', 0):.2f}"),
                    html.P(f"Metros Furados: {getattr(e, 'metros_furados', 0):.2f}"),
                    html.P(f"Início Contrato: {getattr(e, 'data_inicio_contrato', '')}"),
                    # Alertas
                    html.Div([dbc.Alert(a, color="danger", className="p-1 mb-1") for a in alertas]) if alertas else None,
                    # Botões com IDs dinâmicos
                    html.Div([
                        dbc.Button(
                            "👁 Ver",
                            size="sm",
                            color="info",
                            id={"type": "btn-ver-emp", "index": getattr(e, "id", "novo")}
                        ),
                        dbc.Button(
                            "✏ Editar",
                            size="sm",
                            color="warning",
                            className="mx-1",
                            id={"type": "btn-editar-emp", "index": getattr(e, "id", "novo")}
                        ),
                        dbc.Button(
                            "🗑 Remover",
                            size="sm",
                            color="danger",
                            id={"type": "btn-remover-emp", "index": getattr(e, "id", "novo")}
                        )
                    ])
                ]),
                style={"margin": "5px"}
            )
            cards.append(dbc.Col(card, width=4))
        if not cards:
            cards.append(html.P("Sem empregados cadastrados."))
        return cards
    
    # ================= LAYOUT FINAL =================
    cards = criar_cards(empregados)  # inicial sem filtros
    return html.Div([
        html.H3("👷 Painel de Empregados"),
        stats,
        filtros,
        dbc.Row(cards, id="cards-empregados"),
        html.Br(),
        dcc.Link("⬅ Voltar", href="/")
    ])