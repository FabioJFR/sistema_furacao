from dash import Dash, html

app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "Sistema de Furação"

# Layout inicial
app.layout = html.Div(id="page-content")