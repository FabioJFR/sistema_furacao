from plataforma.models import Plano


def listar_planos_ativos_nome_qs():
    return Plano.objects.filter(ativo=True).order_by("nome")
