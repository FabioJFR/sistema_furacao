import dash
from Projetos import Projeto
from Furo import Furo
from Material import Material

from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

# ==========================
# EXEMPLO DE PROJETOS
# ==========================
projeto1 = Projeto("Projeto Alpha", "Descrição do Projeto Alpha", (38.0, -8.0), "Cliente A")
projeto2 = Projeto("Projeto Beta", "Descrição do Projeto Beta", (37.5, -7.8), "Cliente B")
projetos = [projeto1, projeto2]

# ==========================
# INICIALIZA DASH
# ==========================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# ==========================
# MENU LATERAL
# ==========================
sidebar = dbc.Nav(
    [
        html.H2("Menu", className="display-5"),
        html.Hr(),
        dbc.NavLink("Projetos", href="/", id="link-projetos"),
        dbc.NavLink("Empregados", href="/empregados", id="link-empregados"),
        dbc.NavLink("Máquinas", href="/maquinas", id="link-maquinas"),
        dbc.NavLink("Materiais", href="/materiais", id="link-materiais"),
    ],
    vertical=True,
    pills=True,
    style={"height": "100vh", "position": "fixed", "width": "15%", "padding": "20px"}
)

# ==========================
# CONTEÚDO
# ==========================
conteudo = html.Div(id="page-content", style={"margin-left": "17%", "padding": "20px"})

# ==========================
# LAYOUT
# ==========================
app.layout = html.Div([sidebar, conteudo])

# ==========================
# CALLBACKS
# ==========================
@app.callback(
    Output("page-content", "children"),
    Input("link-projetos", "n_clicks"),
    Input("link-empregados", "n_clicks"),
    Input("link-maquinas", "n_clicks"),
    Input("link-materiais", "n_clicks")
)
def render_page(n_proj, n_emp, n_maq, n_mat):
    ctx = dash.callback_context

    if not ctx.triggered:
        btn_id = "link-projetos"
    else:
        btn_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if btn_id == "link-projetos":
        # MAPA INTERATIVO
        lats = [p.localizacao[0] for p in projetos]
        lons = [p.localizacao[1] for p in projetos]
        nomes = [p.nome for p in projetos]

        fig = go.Figure(go.Scattergeo(
            lat=lats,
            lon=lons,
            text=nomes,
            mode='markers',
            marker=dict(size=10)
        ))

        fig.update_layout(
            geo=dict(projection_type='orthographic'),
            margin={"r":0,"t":0,"l":0,"b":0}
        )

        # LISTA DE PROJETOS COM CLIQUE SIMULADO
        lista = []
        for p in projetos:
            lista.append(html.Div([
                html.H5(p.nome),
                html.P(f"Cliente: {p.cliente}"),
                html.P(f"Localização: {p.localizacao}"),
            ], style={"border": "1px solid #ccc", "padding": "10px", "margin": "5px"}))

        return html.Div([
            dcc.Graph(figure=fig),
            html.Hr(),
            html.H4("Projetos:"),
            html.Div(lista)
        ])

    elif btn_id == "link-empregados":
        return html.H3("Empregados - lista e detalhes aqui")
    elif btn_id == "link-maquinas":
        return html.H3("Máquinas - lista e detalhes aqui")
    elif btn_id == "link-materiais":
        return html.H3("Materiais - lista e detalhes aqui")

    return html.H3("Página não encontrada")


# ==========================
# RUN SERVER
# ==========================
if __name__ == "__main__":
    app.run(debug=True)