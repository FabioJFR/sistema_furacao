from dash import html
from core.app import app
from components.sidebar import sidebar_layout
from urls import PAGES

@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname")
)
def router(pathname):
    if pathname is None or pathname == "/":
        pathname = "/projetos"

    page_name = pathname[1:]
    if page_name not in PAGES:
        return html.Div("Página não encontrada")

    # Import dinâmico do layout
    module_path, func_name = PAGES[page_name].rsplit(".", 1)
    module = __import__(module_path, fromlist=[func_name])
    layout_func = getattr(module, func_name)

    return html.Div([
        sidebar_layout(),
        html.Div(layout_func(), style={"margin-left": "220px", "padding": "10px"})
    ])