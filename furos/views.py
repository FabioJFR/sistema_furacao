from furos.novo_layout import novo_layout, listar_layout, detalhe_layout
from furos.services import obter_furo

def furos_routes(pathname):

    if pathname == "/furos/novo":
        return novo_layout()

    if pathname == "/furos/listar":
        return listar_layout()

    if pathname.startswith("/furo/"):
        furo_id = pathname.split("/furo/")[1]
        f = obter_furo(furo_id)

        if f:
            return detalhe_layout(f)

    return None