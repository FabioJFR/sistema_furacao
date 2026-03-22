import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from utils.persistencia import salvar_projetos, carregar_projetos
from classes.projeto import Projeto
from classes.furo import Furo
from classes.empregado import Empregado
from classes.maquina import Maquina
from classes.material import Material

# ==========================
# Carregar dados persistentes
# ==========================
projetos = carregar_projetos()  # lista de Projeto

# ==========================
# Inicializar Dash
# ==========================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Sistema de Perfuração"

# ==========================
# Menu lateral
# ==========================
sidebar = dbc.Nav(
    [
        html.H2("Menu", className="display-5"),
        html.Hr(),
        dbc.NavLink("Projetos", href="/", id="link-projetos"),
        dbc.NavLink("Empregados", href="/empregados", id="link-empregados"),
        dbc.NavLink("Máquinas", href="/maquinas", id="link-maquinas"),
        dbc.NavLink("Materiais", href="/materiais", id="link-materiais"),
        dbc.NavLink("Furos", href="/furos", id="link-furos"),
    ],
    vertical=True,
    pills=True,
    style={"height":"100vh","position":"fixed","width":"18%","padding":"20px"}
)

conteudo = html.Div(id="page-content", style={"margin-left":"20%", "padding":"20px"})

app.layout = html.Div([sidebar, conteudo])

# ==========================
# Função auxiliar: mapa projetos
# ==========================
def mapa_projetos():
    if not projetos:
        return html.P("Nenhum projeto cadastrado.")
    lats = [p.localizacao[0] for p in projetos]
    lons = [p.localizacao[1] for p in projetos]
    nomes = [p.nome for p in projetos]

    fig = go.Figure(go.Scattergeo(
        lat=lats,
        lon=lons,
        text=nomes,
        mode='markers',
        marker=dict(size=12, color="red")
    ))
    fig.update_layout(
        geo=dict(projection_type='orthographic'),
        margin={"r":0,"t":0,"l":0,"b":0}
    )
    return dcc.Graph(figure=fig)

# ==========================
# Página de Projetos
# ==========================
def pagina_projetos():
    lista = []
    for i, p in enumerate(projetos):
        lista.append(html.Div([
            html.H5(p.nome),
            html.P(f"Cliente: {p.cliente}"),
            html.P(f"Localização: {p.localizacao}"),
            dbc.Button("Editar", id={"type":"edit-projeto","index":i}, color="primary", size="sm")
        ], style={"border":"1px solid #ccc","padding":"10px","margin":"5px"}))

    form = html.Div([
        html.H4("Novo Projeto"),
        dbc.Input(id="input-nome", placeholder="Nome"),
        dbc.Input(id="input-cliente", placeholder="Cliente"),
        dbc.Input(id="input-lat", placeholder="Latitude"),
        dbc.Input(id="input-lon", placeholder="Longitude"),
        dbc.Button("Salvar Projeto", id="btn-salvar", color="success", className="mt-2")
    ], style={"border":"1px solid #000","padding":"10px","margin-top":"10px"})

    return html.Div([
        html.H3("Mapa de Projetos"),
        mapa_projetos(),
        html.Hr(),
        html.H4("Projetos cadastrados"),
        html.Div(lista),
        form,
        html.Div(id="dummy")  # para callbacks que não atualizam visual direto
    ])

# ==========================
# Callback principal
# ==========================
@app.callback(
    Output("page-content","children"),
    Input("link-projetos","n_clicks"),
    Input("link-empregados","n_clicks"),
    Input("link-maquinas","n_clicks"),
    Input("link-materiais","n_clicks"),
    Input("link-furos","n_clicks")
)
def render_page(n_proj, n_emp, n_maq, n_mat, n_furo):
    ctx = dash.callback_context
    if not ctx.triggered:
        btn_id = "link-projetos"
    else:
        btn_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if btn_id == "link-projetos":
        return pagina_projetos()
    elif btn_id == "link-empregados":
        return html.H3("Empregados - formulário de criação/edição aqui")
    elif btn_id == "link-maquinas":
        return html.H3("Máquinas - formulário de criação/edição aqui")
    elif btn_id == "link-materiais":
        return html.H3("Materiais - formulário de criação/edição aqui")
    elif btn_id == "link-furos":
        return html.H3("Furos - formulário + visualização 3D aqui")
    return html.H3("Página não encontrada")

# ==========================
# Callback para salvar novo projeto
# ==========================
@app.callback(
    Output("dummy","children"),
    Input("btn-salvar","n_clicks"),
    State("input-nome","value"),
    State("input-cliente","value"),
    State("input-lat","value"),
    State("input-lon","value"),
    prevent_initial_call=True
)
def salvar_novo_projeto(n, nome, cliente, lat, lon):
    if nome:
        p = Projeto(nome, (float(lat), float(lon)), cliente)
        projetos.append(p)
        salvar_projetos(projetos)
    return ""

# ==========================
# Rodar servidor
# ==========================
if __name__=="__main__":
    app.run(debug=True)