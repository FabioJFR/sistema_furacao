""" import dash
from dash import html, dcc, Input, Output, State, MATCH, ALL, callback_context as ctx
import dash_bootstrap_components as dbc
import uuid

from utils.persistencia import carregar_projetos, salvar_projetos
from classes.projeto import Projeto
from classes.furo import Furo

# ================= PÁGINAS =================
from pages.home import layout as home_layout
from pages.projetos.novo import layout as novo_projeto_layout
from pages.projetos.listar import layout as listar_projeto_layout
from pages.projetos.mapa import layout as mapa_projeto_layout

from pages.furos.novo import layout as novo_furo_layout
from pages.furos.listar import layout as listar_furo_layout
from pages.furos.detalhe import layout as detalhe_furo_layout
from pages.furos.editar import layout as editar_furo_layout

from pages.empregados.novo import layout as novo_empregado_layout
from pages.empregados.listar import layout as listar_empregado_layout

from pages.maquinas.novo import layout as novo_maquina_layout
from pages.maquinas.listar import layout as listar_maquina_layout

from pages.materiais.novo import layout as novo_material_layout
from pages.materiais.listar import layout as listar_material_layout


# ================= DADOS =================
projetos = carregar_projetos()

if not projetos:
    p = Projeto("Projeto Teste", (37.9, -8.1), "Cliente X")
    p.id = str(uuid.uuid4())

    f = Furo("Furo 1")
    f.id = str(uuid.uuid4())
    f.adicionar_medicao(20, -36, 10)
    f.adicionar_medicao(40, -35.6, 11.3)

    p.furos.append(f)
    projetos.append(p)
    salvar_projetos(projetos)


# ================= APP =================
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)


# ================= SIDEBAR =================
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


# ================= LAYOUT =================
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

    if pathname in ("/", None):
        return home_layout(projetos)

    # PROJETOS
    if pathname == "/projetos/novo":
        return novo_projeto_layout()

    if pathname == "/projetos/listar":
        return listar_projeto_layout(projetos)

    if pathname.startswith("/projeto/"):
        proj_id = pathname.split("/projeto/")[1]
        for p in projetos:
            if p.id == proj_id:
                return mapa_projeto_layout(p)

    # FUROS
    if pathname == "/furos/novo":
        return novo_furo_layout(projetos)

    if pathname == "/furos/listar":
        return listar_furo_layout(projetos)

    if pathname.startswith("/furos/editar/"):
        furo_id = pathname.split("/furos/editar/")[1]
        for p in projetos:
            for f in p.furos:
                if f.id == furo_id:
                    return editar_furo_layout(furo_id)

    if pathname.startswith("/furo/"):
        furo_id = pathname.split("/furo/")[1]
        for p in projetos:
            for f in p.furos:
                if f.id == furo_id:
                    return detalhe_furo_layout(f)

    # EMPREGADOS
    if pathname == "/empregados/novo":
        return novo_empregado_layout()

    if pathname == "/empregados/listar":
        all_emp = [e for p in projetos for e in p.empregados]
        return listar_empregado_layout(all_emp)

    # MÁQUINAS
    if pathname == "/maquinas/novo":
        return novo_maquina_layout()

    if pathname == "/maquinas/listar":
        all_maqs = [m for p in projetos for m in p.maquinas]
        return listar_maquina_layout(all_maqs)

    # MATERIAIS
    if pathname == "/materiais/novo":
        return novo_material_layout()

    if pathname == "/materiais/listar":
        all_mats = [m for p in projetos for m in p.materiais]
        return listar_material_layout(all_mats)

    return html.H3("Página não encontrada")


# ================= CALLBACK FUROS =================
@app.callback(
    Output("store-projetos", "data"),
    Output("url", "pathname"),
    Output({"type": "modal-apagar", "index": ALL}, "is_open"),

    Input({"type": "btn-add-med", "index": ALL}, "n_clicks"),
    Input({"type": "btn-salvar-furo", "index": ALL}, "n_clicks"),
    Input({"type": "btn-apagar-furo", "index": ALL}, "n_clicks"),
    Input({"type": "btn-cancelar-edicao", "index": ALL}, "n_clicks"),
    Input({"type": "btn-cancelar-apagar", "index": ALL}, "n_clicks"),
    Input({"type": "btn-confirmar-apagar", "index": ALL}, "n_clicks"),

    State({"type": "btn-add-med", "index": ALL}, "id"),
    State({"type": "btn-salvar-furo", "index": ALL}, "id"),
    State({"type": "btn-apagar-furo", "index": ALL}, "id"),
    State({"type": "btn-cancelar-edicao", "index": ALL}, "id"),
    State({"type": "btn-cancelar-apagar", "index": ALL}, "id"),
    State({"type": "btn-confirmar-apagar", "index": ALL}, "id"),

    State("med-prof", "value"),
    State("med-inc", "value"),
    State("med-azi", "value"),
    State("med-mag", "value"),

    State("store-projetos", "data"),
    prevent_initial_call=True
)
def gerenciar_furo(
    add, salvar, apagar, cancelar_ed,
    cancelar_modal, confirmar_apagar,
    add_ids, salvar_ids, apagar_ids,
    cancelar_ed_ids, cancelar_modal_ids, confirmar_apagar_ids,
    prof, inc, azim, mag,
    data
):
    import dash

    projetos = [Projeto.from_dict(p) for p in data]

    trigger = ctx.triggered_id
    if not trigger:
        return dash.no_update, dash.no_update, [False] * len(apagar_ids)

    furo_id = trigger["index"]

    furo = None
    for p in projetos:
        for f in p.furos:
            if f.id == furo_id:
                furo = f
                break

    if not furo:
        return dash.no_update, dash.no_update, [False] * len(apagar_ids)

    # ➤ ADD MEDIÇÃO
    if trigger["type"] == "btn-add-med":
        furo.adicionar_medicao(prof, inc, azim, mag)
        return dash.no_update, dash.no_update, [False] * len(apagar_ids)

    # ➤ SALVAR
    elif trigger["type"] == "btn-salvar-furo":
        salvar_projetos(projetos)
        return [p.to_dict() for p in projetos], "/furos/listar", [False] * len(apagar_ids)

    # ➤ ABRIR MODAL
    elif trigger["type"] == "btn-apagar-furo":
        modal_states = [False] * len(apagar_ids)
        for i, btn in enumerate(apagar_ids):
            if btn["index"] == furo_id:
                modal_states[i] = True
        return dash.no_update, dash.no_update, modal_states

    # ➤ CANCELAR EDIÇÃO
    elif trigger["type"] == "btn-cancelar-edicao":
        return dash.no_update, "/furos/listar", [False] * len(apagar_ids)

    # ➤ CANCELAR MODAL
    elif trigger["type"] == "btn-cancelar-apagar":
        return dash.no_update, dash.no_update, [False] * len(apagar_ids)

    # ➤ CONFIRMAR APAGAR
    elif trigger["type"] == "btn-confirmar-apagar":
        for p in projetos:
            p.furos = [f for f in p.furos if f.id != furo_id]

        salvar_projetos(projetos)
        return [p.to_dict() for p in projetos], "/furos/listar", [False] * len(apagar_ids)

    # fallback: garantir 3 valores
    salvar_projetos(projetos)
    return [p.to_dict() for p in projetos], dash.no_update, [False] * len(apagar_ids)


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True) """


""" import dash
from dash import html, dcc, Input, Output, State, MATCH, ALL, callback_context as ctx
import dash_bootstrap_components as dbc
import uuid

from utils._persistencia import carregar_projetos, salvar_projetos
from models._projeto import Projeto
from models._furo import Furo

# ================= PÁGINAS =================
from pages.home import layout as home_layout
from pages.projetos.novo import layout as novo_projeto_layout
from pages.projetos.listar import layout as listar_projeto_layout
from pages.projetos.mapa import layout as mapa_projeto_layout

from pages.furos.novo import layout as novo_furo_layout
from pages.furos.listar import layout as listar_furo_layout
from pages.furos.detalhe import layout as detalhe_furo_layout
from pages.furos.editar import layout as editar_furo_layout

from pages.empregados.novo import layout as novo_empregado_layout
from pages.empregados.listar import layout as listar_empregado_layout

from pages.maquinas.novo import layout as novo_maquina_layout
from pages.maquinas.listar import layout as listar_maquina_layout

from pages.materiais.novo import layout as novo_material_layout
from pages.materiais.listar import layout as listar_material_layout

# ================= DADOS =================
projetos = carregar_projetos()

if not projetos:
    p = Projeto("Projeto Teste", (37.9, -8.1), "Cliente X")
    p.id = str(uuid.uuid4())

    f = Furo("Furo 1")
    f.id = str(uuid.uuid4())
    f.adicionar_medicao(20, -36, 10)
    f.adicionar_medicao(40, -35.6, 11.3)

    p.furos.append(f)
    projetos.append(p)
    salvar_projetos(projetos)

# ================= APP =================
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

# ================= SIDEBAR =================
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

# ================= LAYOUT =================
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

    if pathname in ("/", None):
        return home_layout(projetos)

    # PROJETOS
    if pathname == "/projetos/novo":
        return novo_projeto_layout()

    if pathname == "/projetos/listar":
        return listar_projeto_layout(projetos)

    if pathname.startswith("/projeto/"):
        proj_id = pathname.split("/projeto/")[1]
        for p in projetos:
            if p.id == proj_id:
                return mapa_projeto_layout(p)

    # FUROS
    if pathname == "/furos/novo":
        return novo_furo_layout(projetos)

    if pathname == "/furos/listar":
        return listar_furo_layout(projetos)

    if pathname.startswith("/furos/editar/"):
        furo_id = pathname.split("/furos/editar/")[1]
        for p in projetos:
            for f in p.furos:
                if f.id == furo_id:
                    return editar_furo_layout(furo_id)

    if pathname.startswith("/furo/"):
        furo_id = pathname.split("/furo/")[1]
        for p in projetos:
            for f in p.furos:
                if f.id == furo_id:
                    return detalhe_furo_layout(f)

    # EMPREGADOS
    if pathname == "/empregados/novo":
        return novo_empregado_layout()

    if pathname == "/empregados/listar":
        all_emp = [e for p in projetos for e in p.empregados]
        return listar_empregado_layout(all_emp)

    # MÁQUINAS
    if pathname == "/maquinas/novo":
        return novo_maquina_layout()

    if pathname == "/maquinas/listar":
        all_maqs = [m for p in projetos for m in p.maquinas]
        return listar_maquina_layout(all_maqs)

    # MATERIAIS
    if pathname == "/materiais/novo":
        return novo_material_layout()

    if pathname == "/materiais/listar":
        all_mats = [m for p in projetos for m in p.materiais]
        return listar_material_layout(all_mats)

    return html.H3("Página não encontrada")

# ================= CALLBACK APAGAR / CANCELAR FUROS =================
@app.callback(
    Output("store-projetos", "data"),
    Output("url", "pathname"),
    Output({"type": "modal-apagar", "index": ALL}, "is_open"),
    Input({"type": "btn-salvar-furo", "index": ALL}, "n_clicks"),
    Input({"type": "btn-apagar-furo", "index": ALL}, "n_clicks"),
    Input({"type": "btn-cancelar-edicao", "index": ALL}, "n_clicks"),
    Input({"type": "btn-cancelar-apagar", "index": ALL}, "n_clicks"),
    Input({"type": "btn-confirmar-apagar", "index": ALL}, "n_clicks"),
    State({"type": "btn-salvar-furo", "index": ALL}, "id"),
    State({"type": "btn-apagar-furo", "index": ALL}, "id"),
    State({"type": "btn-cancelar-edicao", "index": ALL}, "id"),
    State({"type": "btn-cancelar-apagar", "index": ALL}, "id"),
    State({"type": "btn-confirmar-apagar", "index": ALL}, "id"),
    State("store-projetos", "data"),
    prevent_initial_call=True
)
def gerenciar_furo_apagar(
    salvar, apagar, cancelar_ed, cancelar_modal, confirmar_apagar,
    salvar_ids, apagar_ids, cancelar_ed_ids, cancelar_modal_ids, confirmar_apagar_ids,
    data
):
    import dash
    projetos = [Projeto.from_dict(p) for p in data]

    trigger = ctx.triggered_id
    if not trigger:
        return dash.no_update, dash.no_update, [False] * len(apagar_ids)

    furo_id = trigger["index"]

    # ➤ SALVAR
    if trigger["type"] == "btn-salvar-furo":
        salvar_projetos(projetos)
        return [p.to_dict() for p in projetos], "/furos/listar", [False] * len(apagar_ids)

    # ➤ ABRIR MODAL
    elif trigger["type"] == "btn-apagar-furo":
        modal_states = [False] * len(apagar_ids)
        for i, btn in enumerate(apagar_ids):
            if btn["index"] == furo_id:
                modal_states[i] = True
        return dash.no_update, dash.no_update, modal_states

    # ➤ CANCELAR EDIÇÃO
    elif trigger["type"] == "btn-cancelar-edicao":
        return dash.no_update, "/furos/listar", [False] * len(apagar_ids)

    # ➤ CANCELAR MODAL
    elif trigger["type"] == "btn-cancelar-apagar":
        return dash.no_update, dash.no_update, [False] * len(apagar_ids)

    # ➤ CONFIRMAR APAGAR
    elif trigger["type"] == "btn-confirmar-apagar":
        for p in projetos:
            p.furos = [f for f in p.furos if f.id != furo_id]
        salvar_projetos(projetos)
        return [p.to_dict() for p in projetos], "/furos/listar", [False] * len(apagar_ids)

    return dash.no_update, dash.no_update, [False] * len(apagar_ids)

# ================= CALLBACK ADICIONAR MEDIÇÃO =================
@app.callback(
    Output("store-projetos", "data"),
    Input({"type": "btn-add-med", "index": ALL}, "n_clicks"),
    State({"type": "btn-add-med", "index": ALL}, "id"),
    State("med-prof", "value"),
    State("med-inc", "value"),
    State("med-azi", "value"),
    State("med-mag", "value"),
    State("store-projetos", "data"),
    prevent_initial_call=True
)
def adicionar_medicao_furo(n_clicks, ids, prof, inc, azim, mag, data):
    import dash
    projetos = [Projeto.from_dict(p) for p in data]
    trigger = ctx.triggered_id
    if not trigger:
        return dash.no_update

    furo_id = trigger["index"]
    furo = None
    for p in projetos:
        for f in p.furos:
            if f.id == furo_id:
                furo = f
                break
    if not furo:
        return dash.no_update

    # Adiciona medição
    furo.adicionar_medicao(prof, inc, azim, mag)
    salvar_projetos(projetos)
    return [p.to_dict() for p in projetos]

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True) """

""" import dash
from dash import html, dcc, Input, Output, State, MATCH, ALL, callback_context as ctx
import dash_bootstrap_components as dbc
import uuid

from utils.persistencia import carregar_projetos, salvar_projetos
from classes.projeto import Projeto
from classes.furo import Furo

# ================= PÁGINAS =================
from pages.home import layout as home_layout
from pages.projetos.novo import layout as novo_projeto_layout
from pages.projetos.listar import layout as listar_projeto_layout
from pages.projetos.mapa import layout as mapa_projeto_layout

from pages.furos.novo import layout as novo_furo_layout
from pages.furos.listar import layout as listar_furo_layout
from pages.furos.detalhe import layout as detalhe_furo_layout
from pages.furos.editar import layout as editar_furo_layout

from pages.empregados.novo import layout as novo_empregado_layout
from pages.empregados.listar import layout as listar_empregado_layout

from pages.maquinas.novo import layout as novo_maquina_layout
from pages.maquinas.listar import layout as listar_maquina_layout

from pages.materiais.novo import layout as novo_material_layout
from pages.materiais.listar import layout as listar_material_layout


# ================= DADOS =================
projetos = carregar_projetos()

if not projetos:
    p = Projeto("Projeto Teste", (37.9, -8.1), "Cliente X")
    p.id = str(uuid.uuid4())

    f = Furo("Furo 1")
    f.id = str(uuid.uuid4())
    f.adicionar_medicao(20, -36, 10)
    f.adicionar_medicao(40, -35.6, 11.3)

    p.furos.append(f)
    projetos.append(p)
    salvar_projetos(projetos)


# ================= APP =================
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)


# ================= SIDEBAR =================
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


# ================= LAYOUT =================
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

    if pathname in ("/", None):
        return home_layout(projetos)

    # PROJETOS
    if pathname == "/projetos/novo":
        return novo_projeto_layout()

    if pathname == "/projetos/listar":
        return listar_projeto_layout(projetos)

    if pathname.startswith("/projeto/"):
        proj_id = pathname.split("/projeto/")[1]
        for p in projetos:
            if p.id == proj_id:
                return mapa_projeto_layout(p)

    # FUROS
    if pathname == "/furos/novo":
        return novo_furo_layout(projetos)

    if pathname == "/furos/listar":
        return listar_furo_layout(projetos)

    if pathname.startswith("/furos/editar/"):
        furo_id = pathname.split("/furos/editar/")[1]
        for p in projetos:
            for f in p.furos:
                if f.id == furo_id:
                    return editar_furo_layout(furo_id)

    if pathname.startswith("/furo/"):
        furo_id = pathname.split("/furo/")[1]
        for p in projetos:
            for f in p.furos:
                if f.id == furo_id:
                    return detalhe_furo_layout(f)

    # EMPREGADOS
    if pathname == "/empregados/novo":
        return novo_empregado_layout()

    if pathname == "/empregados/listar":
        all_emp = [e for p in projetos for e in p.empregados]
        return listar_empregado_layout(all_emp)

    # MÁQUINAS
    if pathname == "/maquinas/novo":
        return novo_maquina_layout()

    if pathname == "/maquinas/listar":
        all_maqs = [m for p in projetos for m in p.maquinas]
        return listar_maquina_layout(all_maqs)

    # MATERIAIS
    if pathname == "/materiais/novo":
        return novo_material_layout()

    if pathname == "/materiais/listar":
        all_mats = [m for p in projetos for m in p.materiais]
        return listar_material_layout(all_mats)

    return html.H3("Página não encontrada")


# ================= CALLBACK FUROS =================
@app.callback(
    Output("store-projetos", "data"),
    Output("url", "pathname"),
    Output({"type": "modal-apagar", "index": ALL}, "is_open"),

    Input({"type": "btn-add-med", "index": ALL}, "n_clicks"),
    Input({"type": "btn-salvar-furo", "index": ALL}, "n_clicks"),
    Input({"type": "btn-apagar-furo", "index": ALL}, "n_clicks"),
    Input({"type": "btn-cancelar-edicao", "index": ALL}, "n_clicks"),
    Input({"type": "btn-cancelar-apagar", "index": ALL}, "n_clicks"),
    Input({"type": "btn-confirmar-apagar", "index": ALL}, "n_clicks"),

    State({"type": "btn-add-med", "index": ALL}, "id"),
    State({"type": "btn-salvar-furo", "index": ALL}, "id"),
    State({"type": "btn-apagar-furo", "index": ALL}, "id"),
    State({"type": "btn-cancelar-edicao", "index": ALL}, "id"),
    State({"type": "btn-cancelar-apagar", "index": ALL}, "id"),
    State({"type": "btn-confirmar-apagar", "index": ALL}, "id"),

    State("med-prof", "value"),
    State("med-inc", "value"),
    State("med-azi", "value"),
    State("med-mag", "value"),

    State("store-projetos", "data"),
    prevent_initial_call=True
)
def gerenciar_furo(
    add, salvar, apagar, cancelar_ed,
    cancelar_modal, confirmar_apagar,
    add_ids, salvar_ids, apagar_ids,
    cancelar_ed_ids, cancelar_modal_ids, confirmar_apagar_ids,
    prof, inc, azim, mag,
    data
):
    import dash

    projetos = [Projeto.from_dict(p) for p in data]

    trigger = ctx.triggered_id
    if not trigger:
        return dash.no_update, dash.no_update, [False] * len(apagar_ids)

    furo_id = trigger["index"]

    furo = None
    for p in projetos:
        for f in p.furos:
            if f.id == furo_id:
                furo = f
                break

    if not furo:
        return dash.no_update, dash.no_update, [False] * len(apagar_ids)

    # ➤ ADD MEDIÇÃO
    if trigger["type"] == "btn-add-med":
        furo.adicionar_medicao(prof, inc, azim, mag)
        return dash.no_update, dash.no_update, [False] * len(apagar_ids)

    # ➤ SALVAR
    elif trigger["type"] == "btn-salvar-furo":
        salvar_projetos(projetos)
        return [p.to_dict() for p in projetos], "/furos/listar", [False] * len(apagar_ids)

    # ➤ ABRIR MODAL
    elif trigger["type"] == "btn-apagar-furo":
        modal_states = [False] * len(apagar_ids)
        for i, btn in enumerate(apagar_ids):
            if btn["index"] == furo_id:
                modal_states[i] = True
        return dash.no_update, dash.no_update, modal_states

    # ➤ CANCELAR EDIÇÃO
    elif trigger["type"] == "btn-cancelar-edicao":
        return dash.no_update, "/furos/listar", [False] * len(apagar_ids)

    # ➤ CANCELAR MODAL
    elif trigger["type"] == "btn-cancelar-apagar":
        return dash.no_update, dash.no_update, [False] * len(apagar_ids)

    # ➤ CONFIRMAR APAGAR
    elif trigger["type"] == "btn-confirmar-apagar":
        for p in projetos:
            p.furos = [f for f in p.furos if f.id != furo_id]

        salvar_projetos(projetos)
        return [p.to_dict() for p in projetos], "/furos/listar", [False] * len(apagar_ids)

    # fallback: garantir 3 valores
    salvar_projetos(projetos)
    return [p.to_dict() for p in projetos], dash.no_update, [False] * len(apagar_ids)


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True) """


import dash
from dash import html, dcc, Input, Output, State, MATCH, ALL, callback_context as ctx
import dash_bootstrap_components as dbc
import uuid

from utils._persistencia import carregar_projetos, salvar_projetos
from models._projeto import Projeto
from models._furo import Furo

# ================= PÁGINAS =================
from pages.home import layout as home_layout
from pages.projetos.novo import layout as novo_projeto_layout
from pages.projetos.listar import layout as listar_projeto_layout
from pages.projetos.mapa import layout as mapa_projeto_layout

from pages.furos.novo import layout as novo_furo_layout
from pages.furos.listar import layout as listar_furo_layout
from pages.furos.detalhe import layout as detalhe_furo_layout
from pages.furos.editar import layout as editar_furo_layout

from pages.empregados.novo import layout as novo_empregado_layout
from pages.empregados.listar import layout as listar_empregado_layout

from pages.maquinas.novo import layout as novo_maquina_layout
from pages.maquinas.listar import layout as listar_maquina_layout

from pages.materiais.novo import layout as novo_material_layout
from pages.materiais.listar import layout as listar_material_layout

# ================= DADOS =================
projetos = carregar_projetos()

if not projetos:
    p = Projeto("Projeto Teste", (37.9, -8.1), "Cliente X")
    p.id = str(uuid.uuid4())

    f = Furo("Furo 1")
    f.id = str(uuid.uuid4())
    f.adicionar_medicao(20, -36, 10)
    f.adicionar_medicao(40, -35.6, 11.3)

    p.furos.append(f)
    projetos.append(p)
    salvar_projetos(projetos)

# ================= APP =================
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

# ================= SIDEBAR =================
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

# ================= LAYOUT =================
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

    if pathname in ("/", None):
        return home_layout(projetos)

    # PROJETOS
    if pathname == "/projetos/novo":
        return novo_projeto_layout()

    if pathname == "/projetos/listar":
        return listar_projeto_layout(projetos)

    if pathname.startswith("/projeto/"):
        proj_id = pathname.split("/projeto/")[1]
        for p in projetos:
            if p.id == proj_id:
                return mapa_projeto_layout(p)

    # FUROS
    if pathname == "/furos/novo":
        return novo_furo_layout(projetos)

    if pathname == "/furos/listar":
        return listar_furo_layout(projetos)

    if pathname.startswith("/furos/editar/"):
        furo_id = pathname.split("/furos/editar/")[1]
        for p in projetos:
            for f in p.furos:
                if f.id == furo_id:
                    return editar_furo_layout(furo_id)

    if pathname.startswith("/furo/"):
        furo_id = pathname.split("/furo/")[1]
        for p in projetos:
            for f in p.furos:
                if f.id == furo_id:
                    return detalhe_furo_layout(f)

    # EMPREGADOS
    if pathname == "/empregados/novo":
        return novo_empregado_layout()

    if pathname == "/empregados/listar":
        all_emp = [e for p in projetos for e in p.empregados]
        return listar_empregado_layout(all_emp)

    # MÁQUINAS
    if pathname == "/maquinas/novo":
        return novo_maquina_layout()

    if pathname == "/maquinas/listar":
        all_maqs = [m for p in projetos for m in p.maquinas]
        return listar_maquina_layout(all_maqs)

    # MATERIAIS
    if pathname == "/materiais/novo":
        return novo_material_layout()

    if pathname == "/materiais/listar":
        all_mats = [m for p in projetos for m in p.materiais]
        return listar_material_layout(all_mats)

    return html.H3("Página não encontrada")

# ================= CALLBACK APAGAR / CANCELAR FUROS =================
@app.callback(
    Output("store-projetos", "data"),
    Output("url", "pathname"),
    Output({"type": "modal-apagar", "index": ALL}, "is_open"),
    Input({"type": "btn-salvar-furo", "index": ALL}, "n_clicks"),
    Input({"type": "btn-apagar-furo", "index": ALL}, "n_clicks"),
    Input({"type": "btn-cancelar-edicao", "index": ALL}, "n_clicks"),
    Input({"type": "btn-cancelar-apagar", "index": ALL}, "n_clicks"),
    Input({"type": "btn-confirmar-apagar", "index": ALL}, "n_clicks"),
    State({"type": "btn-salvar-furo", "index": ALL}, "id"),
    State({"type": "btn-apagar-furo", "index": ALL}, "id"),
    State({"type": "btn-cancelar-edicao", "index": ALL}, "id"),
    State({"type": "btn-cancelar-apagar", "index": ALL}, "id"),
    State({"type": "btn-confirmar-apagar", "index": ALL}, "id"),
    State("store-projetos", "data"),
    prevent_initial_call=True
)
def gerenciar_furo_apagar(
    salvar, apagar, cancelar_ed, cancelar_modal, confirmar_apagar,
    salvar_ids, apagar_ids, cancelar_ed_ids, cancelar_modal_ids, confirmar_apagar_ids,
    data
):
    import dash
    projetos = [Projeto.from_dict(p) for p in data]

    trigger = ctx.triggered_id
    if not trigger:
        return dash.no_update, dash.no_update, [False] * len(apagar_ids)

    furo_id = trigger["index"]

    # ➤ SALVAR
    if trigger["type"] == "btn-salvar-furo":
        salvar_projetos(projetos)
        return [p.to_dict() for p in projetos], "/furos/listar", [False] * len(apagar_ids)

    # ➤ ABRIR MODAL
    elif trigger["type"] == "btn-apagar-furo":
        modal_states = [False] * len(apagar_ids)
        for i, btn in enumerate(apagar_ids):
            if btn["index"] == furo_id:
                modal_states[i] = True
        return dash.no_update, dash.no_update, modal_states

    # ➤ CANCELAR EDIÇÃO
    elif trigger["type"] == "btn-cancelar-edicao":
        return dash.no_update, "/furos/listar", [False] * len(apagar_ids)

    # ➤ CANCELAR MODAL
    elif trigger["type"] == "btn-cancelar-apagar":
        return dash.no_update, dash.no_update, [False] * len(apagar_ids)

    # ➤ CONFIRMAR APAGAR
    elif trigger["type"] == "btn-confirmar-apagar":
        for p in projetos:
            p.furos = [f for f in p.furos if f.id != furo_id]
        salvar_projetos(projetos)
        return [p.to_dict() for p in projetos], "/furos/listar", [False] * len(apagar_ids)

    return dash.no_update, dash.no_update, [False] * len(apagar_ids)

# ================= CALLBACK ADICIONAR MEDIÇÃO =================
@app.callback(
    Output("store-projetos", "data"),
    Input({"type": "btn-add-med", "index": ALL}, "n_clicks"),
    State({"type": "btn-add-med", "index": ALL}, "id"),
    State("med-prof", "value"),
    State("med-inc", "value"),
    State("med-azi", "value"),
    State("med-mag", "value"),
    State("store-projetos", "data"),
    prevent_initial_call=True
)
def adicionar_medicao_furo(n_clicks, ids, prof, inc, azim, mag, data):
    import dash
    projetos = [Projeto.from_dict(p) for p in data]
    trigger = ctx.triggered_id
    if not trigger:
        return dash.no_update

    furo_id = trigger["index"]
    furo = None
    for p in projetos:
        for f in p.furos:
            if f.id == furo_id:
                furo = f
                break
    if not furo:
        return dash.no_update

    # Adiciona medição
    furo.adicionar_medicao(prof, inc, azim, mag)
    salvar_projetos(projetos)
    return [p.to_dict() for p in projetos]

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)