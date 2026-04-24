from plataforma.models import Plano


def listar_planos_ativos():
    return Plano.objects.filter(ativo=True).order_by("preco_mensal")


def obter_plano_ativo_por_id(plano_id):
    return Plano.objects.filter(pk=plano_id, ativo=True).first()


def construir_planos_contexto(planos_qs):
    return {
        str(plano.pk): {
            "nome": plano.nome,
            "tipo": plano.tipo,
            "periodos": plano.periodos_cobranca_disponiveis_normalizados,
            "preco_mensal": str(plano.preco_mensal or 0),
            "preco_anual": str(plano.preco_anual or 0),
        }
        for plano in planos_qs
    }

