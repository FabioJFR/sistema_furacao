import dash
from dash import html, dcc, Input, Output, State, callback_context as ctx
import dash_bootstrap_components as dbc
import uuid

from utils.alertas import analisar_furo
from utils.persistencia import carregar_projetos, salvar_projetos
from classes.projeto import Projeto
from classes.furo import Furo
from classes.empregado import Empregado
from classes.maquina import Maquina
from classes.material import Material

# Páginas
from pages.home import layout as home_layout
from pages.projetos.novo import layout as novo_projeto_layout
from pages.projetos.listar import layout as listar_projeto_layout
from pages.projetos.mapa import layout as mapa_projeto_layout
from pages.furos.novo import layout as novo_furo_layout
from pages.furos.listar import layout as listar_furo_layout
from pages.furos.detalhe import layout as detalhe_furo_layout
from pages.empregados.novo import layout as novo_empregado_layout
from pages.empregados.listar import layout as listar_empregado_layout
from pages.maquinas.novo import layout as novo_maquina_layout
from pages.maquinas.listar import layout as listar_maquina_layout
from pages.materiais.novo import layout as novo_material_layout
from pages.materiais.listar import layout as listar_material_layout
# main.py é o ponto de entrada da aplicação, onde inicializamos o Dash, definimos o layout principal, o menu lateral e as rotas para cada página. Também é onde carregamos os dados dos projetos e definimos os callbacks para interatividade, como adicionar medições a um furo ou filtrar a lista de furos e empregados. A estrutura é modular, com cada página e classe definida em arquivos separados para manter o código organizado e fácil de manter.

# ================= CARREGA DADOS =================
projetos = carregar_projetos()

# ================= DADOS DE TESTE =================
if not projetos:
    # Cria projeto e furo de teste com IDs únicos
    p = Projeto("Projeto Teste", (37.9, -8.1), "Cliente X")
    p.id = str(uuid.uuid4())
    f = Furo("Furo 1")
    f.id = str(uuid.uuid4())
    f.adicionar_medicao(20, -36, 10)
    f.adicionar_medicao(40, -35.6, 11.3)
    f.adicionar_medicao(60, -34.2, 11.2)
    p.furos.append(f)
    projetos.append(p)
    salvar_projetos(projetos)

# ================= INICIALIZAÇÃO DASH =================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP],
                suppress_callback_exceptions=True)

# ================= MENU LATERAL =================
sidebar = html.Div([
    html.H3("Menu"),
    dcc.Link("🏠 Home", href="/"),
    html.Hr(),

    html.Details([html.Summary("Projetos"), html.Div([
        dcc.Link("➕ Novo", href="/projetos/novo"), html.Br(),
        dcc.Link("📋 Listar", href="/projetos/listar")
    ])]),

    html.Details([html.Summary("Furos"), html.Div([
        dcc.Link("➕ Novo", href="/furos/novo"), html.Br(),
        dcc.Link("📋 Listar", href="/furos/listar")
    ])]),

    html.Details([html.Summary("Empregados"), html.Div([
        dcc.Link("➕ Novo", href="/empregados/novo"), html.Br(),
        dcc.Link("📋 Listar", href="/empregados/listar")
    ])]),

    html.Details([html.Summary("Máquinas"), html.Div([
        dcc.Link("➕ Novo", href="/maquinas/novo"), html.Br(),
        dcc.Link("📋 Listar", href="/maquinas/listar")
    ])]),

    html.Details([html.Summary("Materiais"), html.Div([
        dcc.Link("➕ Novo", href="/materiais/novo"), html.Br(),
        dcc.Link("📋 Listar", href="/materiais/listar")
    ])])
], style={
    "position": "fixed",
    "width": "18%",
    "height": "100vh",
    "background": "#f8f9fa",
    "padding": "20px",
    "overflow": "auto"
})

# ================= LAYOUT PRINCIPAL =================
app.layout = html.Div([
    dcc.Location(id="url"),

    # Store dos projetos
    dcc.Store(id="store-projetos", data=[p.to_dict() for p in projetos]),

    # Store dos empregados (para filtros rápidos)
    dcc.Store(id="store-empregados", data=[e.to_dict() for p in projetos for e in p.empregados]),

    sidebar,
    html.Div(id="page-content", style={"margin-left": "20%", "padding": "20px"})
])

# ================= ROUTER =================
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
    Input("store-projetos", "data")
)
def router(pathname, data):
    projetos = [Projeto.from_dict(p) for p in data]

    if pathname == "/" or pathname is None:
        return home_layout(projetos)

    # Mapa de projeto
    if pathname.startswith("/projeto/"):
        proj_id = pathname.split("/projeto/")[1]
        for p in projetos:
            if p.id == proj_id:
                return mapa_projeto_layout(p)

    # Novo / Listar Furos
    if pathname == "/furos/novo":
        return novo_furo_layout(projetos)
    if pathname == "/furos/listar":
        return listar_furo_layout(projetos)

    # Detalhe furo
    if pathname.startswith("/furo/"):
        furo_id = pathname.split("/furo/")[1]
        for p in projetos:
            for f in p.furos:
                if f.id == furo_id:
                    return detalhe_furo_layout(f)

    # Projetos
    if pathname == "/projetos/novo":
        return novo_projeto_layout()
    if pathname == "/projetos/listar":
        return listar_projeto_layout(projetos)

    # Empregados
    if pathname == "/empregados/novo":
        return novo_empregado_layout()
    if pathname == "/empregados/listar":
        all_emp = []
        for p in projetos:
            all_emp.extend(p.empregados)
        return listar_empregado_layout(all_emp)

    # Máquinas
    if pathname == "/maquinas/novo":
        return novo_maquina_layout()
    if pathname == "/maquinas/listar":
        all_maqs = []
        for p in projetos:
            all_maqs.extend(p.maquinas)
        return listar_maquina_layout(all_maqs)

    # Materiais
    if pathname == "/materiais/novo":
        return novo_material_layout()
    if pathname == "/materiais/listar":
        all_mats = []
        for p in projetos:
            all_mats.extend(p.materiais)
        return listar_material_layout(all_mats)

    return html.H3("Página não encontrada")


# ================= CALLBACKS =================


#================== Callback para adicionar nova medição a um furo =================

@app.callback(
    Output("store-projetos", "data"),
    Input("btn-add-med", "n_clicks"),
    State("med-prof", "value"),
    State("med-inc", "value"),
    State("med-azi", "value"),
    State("med-mag", "value"),  # novo campo
    State("url", "pathname"),
    State("store-projetos", "data"),
    prevent_initial_call=True
)
def add_medicao_furo(n_clicks, profundidade, inclinacao, azimute, magnetismo, pathname, data):
    if profundidade is None:
        return dash.no_update

    projetos = [Projeto.from_dict(p) for p in data]
    furo_id = pathname.split("/furo/")[1]

    for p in projetos:
        for f in p.furos:
            if f.id == furo_id:
                f.adicionar_medicao(profundidade, inclinacao, azimute, magnetismo)

    salvar_projetos(projetos)
    return [p.to_dict() for p in projetos]


#================== Callback unificado para navegação =================
@app.callback(
    Output("url", "pathname"),
    Input("mapa-projetos", "clickData", allow_optional=True),
    Input("mapa-furos", "clickData", allow_optional=True),
    State("store-projetos", "data"),
    prevent_initial_call=True
)
def navegar_mapas(click_proj, click_furo, data):
    triggered = ctx.triggered_id

    if not triggered or not data:
        return dash.no_update

    projetos = [Projeto.from_dict(p) for p in data]

    if triggered == "mapa-projetos" and click_proj:
        try:
            proj_id = click_proj["points"][0]["customdata"][0]
            return f"/projeto/{proj_id}"
        except:
            return dash.no_update

    if triggered == "mapa-furos" and click_furo:
        try:
            furo_id = click_furo["points"][0]["customdata"][0]
            return f"/furo/{furo_id}"
        except:
            return dash.no_update

    return dash.no_update

#================== CALLBACK PARA FILTRAR LISTA DE FUROS =================

@app.callback(
    Output("lista-furos", "children"),
    Input("filtro-projeto", "value"),
    Input("filtro-prof", "value"),
    Input("store-projetos", "data"),
    prevent_initial_call=False
)
def atualizar_lista_furos(filtro_projeto, filtro_prof, data):

    projetos = [Projeto.from_dict(p) for p in data]

    cards = []

    for p in projetos:

        if filtro_projeto and p.nome != filtro_projeto:
            continue

        for f in p.furos:

            ultima = f.medicoes[-1] if f.medicoes else None
            alertas = analisar_furo(f)

            if filtro_prof and (not ultima or ultima["profundidade"] < filtro_prof):
                continue

            cor = "success" if ultima and ultima["profundidade"] > 50 else "warning"

            cards.append(
                dbc.Col(
                    dbc.Card([
                        dbc.CardBody([

                            html.H5(f.nome),
                            html.H6(f"Projeto: {p.nome}", className="text-muted"),

                            html.Hr(),

                            html.P([
                                html.Strong("Profundidade: "),
                                f"{ultima['profundidade']} m" if ultima else "N/A"
                            ]),

                            html.P([
                                html.Strong("Inclinação: "),
                                f"{ultima['inclinacao']}°" if ultima else "N/A"
                            ]),

                            html.P([
                                html.Strong("Azimute: "),
                                f"{ultima['azimute']}°" if ultima else "N/A"
                            ]),

                            dbc.Badge(
                                "Ativo" if cor == "success" else "Raso",
                                color=cor
                            ),

                            html.Br(),

                            dbc.Button(
                                "🔍 Ver Detalhes",
                                href=f"/furo/{f.id}",
                                color="primary",
                                size="sm"
                            )

                        ])
                    ], className="h-100 shadow-sm"),
                    width=4
                )
            )

    if not cards:
        return dbc.Alert("Nenhum furo encontrado.", color="warning")

    return dbc.Row(cards, className="g-3")


#================== Calllback de criação de empregados =================

@app.callback(
    Output("store-empregados", "data"),
    Input("btn-salvar-emp", "n_clicks"),
    State("emp-nome", "value"),
    State("emp-numero", "value"),
    State("emp-idade", "value"),
    State("emp-doc", "value"),
    State("emp-nib", "value"),
    State("emp-morada", "value"),
    State("emp-nacionalidade", "value"),
    State("emp-nif", "value"),
    State("emp-categoria", "value"),
    State("emp-salario", "value"),
    State("store-empregados", "data"),
    prevent_initial_call=True
)
def adicionar_empregado(n_clicks, nome, numero, idade, doc, nib, morada,
                       nacionalidade, nif, categoria, salario, data_empregados):
    if not nome:  # validação mínima
        return dash.no_update

    # Reconstruir lista existente
    empregados = [Empregado.from_dict(d) for d in data_empregados] if data_empregados else []

    # Criar novo empregado
    e = Empregado(nome=nome, numero=numero, categoria=categoria)
    e.idade = int(idade) if idade else 0
    e.doc_id = doc or ""
    e.nib = nib or ""
    e.morada = morada or ""
    e.nacionalidade = nacionalidade or ""
    e.nif = nif or ""
    e.salario = float(salario) if salario else 0.0

    empregados.append(e)

    return [emp.to_dict() for emp in empregados]


#================== Função para criar cards de empregados =================
# (usada na página de listagem de empregados, com alertas automáticos)
# A função de callback para filtrar empregados também está nessa página, para manter a lógica de alertas centralizada.
# A função de análise de alertas está em utils/alertas.py, para ser reutilizada em outros contextos (ex: detalhes do empregado, gráficos mensais, etc).
# A função de criação de cards é simples e pode ser expandida com mais detalhes ou ações conforme necessário.
# A ideia é que a página de listagem de empregados seja um dashboard rápido para monitorar a situação geral dos empregados, com alertas visíveis e filtros para encontrar rapidamente quem precisa de atenção.
# Necessario para o callback de filtragem, que reconstrói os objetos Empregado a partir dos dicts armazenados no dcc.Store, aplica os filtros e depois gera os cards atualizados.
import dash_bootstrap_components as dbc
from dash import html

def criar_cards(empregados):
    """Gera cards de empregados"""
    cards = []
    for e in empregados:
        card = dbc.Card(
            dbc.CardBody([
                html.H5(e.nome),
                dbc.Badge(e.categoria, color="primary", className="mb-2"),
                html.P(f"Número: {e.numero}"),
                html.P(f"Idade: {e.idade}"),
                html.P(f"Salário: {e.salario}"),
                html.Div([
                    dbc.Button("👁 Ver", size="sm", color="info"),
                    dbc.Button("✏ Editar", size="sm", color="warning", className="mx-1"),
                    dbc.Button("🗑 Remover", size="sm", color="danger")
                ])
            ]),
            style={"margin":"5px"}
        )
        cards.append(dbc.Col(card, width=4))
    return cards


#================== CALLBACK PARA FILTRAR LISTA DE EMPREGADOS =================

@app.callback(
    Output("cards-empregados", "children"),
    Input("filtro-nome", "value"),
    Input("filtro-categoria", "value"),
    Input("ordenar-por", "value"),
    State("store-empregados", "data")  # lista de empregados em dicts
)
def filtrar_empregados(nome, categoria, ordenar_por, data_empregados):
    # reconstruir objetos Empregado
    empregados = [Empregado.from_dict(d) for d in data_empregados]
    if nome:
        empregados = [e for e in empregados if nome.lower() in e.nome.lower()]
    if categoria:
        empregados = [e for e in empregados if e.categoria == categoria]
    if ordenar_por:
        if ordenar_por == "salario":
            empregados.sort(key=lambda e: e.salario, reverse=True)
        elif ordenar_por == "tempo":
            empregados.sort(key=lambda e: e.data_inicio_contrato)
        elif ordenar_por == "metros":
            empregados.sort(key=lambda e: e.metros_furados, reverse=True)
    # criar cards filtrados
    return criar_cards(empregados)


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)