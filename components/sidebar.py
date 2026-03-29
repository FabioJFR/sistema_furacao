from dash import html, dcc

def sidebar_layout():
    return html.Div([
        html.H2("Menu"),
        dcc.Location(id="url", refresh=False),
        html.Ul([
            html.Li(dcc.Link("Projetos", href="/projetos")),
            html.Li(dcc.Link("Furos", href="/furos")),
            html.Li(dcc.Link("Maquinas", href="/maquinas")),
            html.Li(dcc.Link("Empregados", href="/empregados")),
            html.Li(dcc.Link("Materiais", href="/materiais")),
        ])
    ], style={"width": "200px", "float": "left", "padding": "10px", "border-right": "1px solid #ccc"})