from projetos.models import Projeto
from core.utils.coordenadas import obter_coordenadas_por_cidade_pais


def preencher_coordenadas_projeto(projeto):
    if projeto.cidade and projeto.pais:
        lat, lon = obter_coordenadas_por_cidade_pais(projeto.cidade, projeto.pais)
        projeto.localizacao_lat = lat
        projeto.localizacao_lon = lon
    return projeto


def criar_projeto(form):
    projeto = form.save(commit=False)
    preencher_coordenadas_projeto(projeto)
    projeto.save()
    form.save_m2m()
    return projeto


def atualizar_projeto(form):

    projeto = form.save(commit=False)
    preencher_coordenadas_projeto(projeto)
    projeto.save()
    form.save_m2m()
    return projeto


def preparar_localizacao_projeto(projeto):
    if projeto.cidade and projeto.pais:
        lat, lon = obter_coordenadas_por_cidade_pais(
            projeto.cidade,
            projeto.pais
        )
        projeto.localizacao_lat = lat
        projeto.localizacao_lon = lon

    return projeto


def criar_projeto(form):
    projeto = form.save(commit=False)

    preparar_localizacao_projeto(projeto)

    projeto.save()
    form.save_m2m()

    return projeto


def atualizar_projeto(form):
    projeto = form.save(commit=False)

    preparar_localizacao_projeto(projeto)

    projeto.save()
    form.save_m2m()

    return projeto

