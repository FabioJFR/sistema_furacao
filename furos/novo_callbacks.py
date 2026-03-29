# furos/novo_callbacks.py
from dash import Input, Output, State
from core.app import app
from furos.services import criar_furo
import dash

@app.callback(
    Output("furo-msg", "children"),
    Input("btn-add-furo", "n_clicks"),
    State("furo-nome", "value"),
    State("furo-local_sondagem", "value"),
    State("furo-prof_alvo", "value"),
    State("furo-inc", "value"),
    State("furo-azi", "value"),
    State("furo-lat", "value"),
    State("furo-lon", "value"),
    prevent_initial_call=True
)
def add_furo(n_clicks, nome, local_sondagem, prof_alvo, inc, azi, lat, lon):
    if not n_clicks:
        return dash.no_update

    obrigatorios = [nome, local_sondagem, prof_alvo, inc, azi, lat, lon]
    if not all(obrigatorios):
        return "Todos os campos obrigatórios devem ser preenchidos!"

    criar_furo(nome, local_sondagem, prof_alvo, inc, azi, lat, lon)
    return f"Furo {nome} adicionado com sucesso!"