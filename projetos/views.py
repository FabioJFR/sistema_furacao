from projetos.novo_layout import novo_layout, listar_layout, detalhe_layout
from projetos.services import obter_projeto

def projetos_routes(pathname):

    if pathname == "/projetos/novo":
        return novo_layout()

    if pathname == "/projetos/listar":
        return listar_layout()

    if pathname.startswith("/projeto/"):
        proj_id = pathname.split("/projeto/")[1]
        projeto = obter_projeto(proj_id)

        if projeto:
            return detalhe_layout(projeto)

    return None