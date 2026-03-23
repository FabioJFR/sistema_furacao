import dash
from dash import html, dcc, Input, Output, State, callback_context as ctx
import dash_bootstrap_components as dbc
import uuid

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
    dcc.Store(id="store-projetos", data=[p.to_dict() for p in projetos]),
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
@app.callback(
    Output("store-projetos", "data"),
    Input("btn-add-med", "n_clicks"),
    State("med-prof", "value"),
    State("med-inc", "value"),
    State("med-azi", "value"),
    State("url", "pathname"),
    State("store-projetos", "data"),
    prevent_initial_call=True
)
def add_medicao_furo(n_clicks, profundidade, inclinacao, azimute, pathname, data):
    if not profundidade:
        return dash.no_update

    projetos = [Projeto.from_dict(p) for p in data]
    furo_id = pathname.split("/furo/")[1]

    for p in projetos:
        for f in p.furos:
            if f.id == furo_id:
                f.adicionar_medicao(profundidade, inclinacao, azimute)

    salvar_projetos(projetos)
    return [p.to_dict() for p in projetos]

# ================= CALLBACK UNIFICADO PARA NAVEGAÇÃO =================
@app.callback(
    Output("url", "pathname"),
    Input("mapa-projetos", "clickData", allow_optional=True),
    Input("mapa-furos", "clickData", allow_optional=True),
    State("store-projetos", "data"),
    prevent_initial_call=True
)
def navegar(click_globo, click_furo, data):
    projetos = [Projeto.from_dict(p) for p in data]

    if not ctx.triggered:
        return dash.no_update

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Clique no globo → mapa local do projeto
    if trigger_id == "mapa-projetos" and click_globo:
        proj_id = click_globo["points"][0]["customdata"][0]  # pega o id do projeto
        for p in projetos:
            if p.id == proj_id:
                return f"/projeto/{p.id}"

    # Clique no mapa local → detalhe do furo
    if trigger_id == "mapa-furos" and click_furo:
        furo_nome = click_furo["points"][0]["text"]
        for p in projetos:
            for f in p.furos:
                if f.nome == furo_nome:
                    return f"/furo/{f.id}"

    return dash.no_update

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)