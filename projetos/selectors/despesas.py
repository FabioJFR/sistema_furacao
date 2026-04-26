from django.db.models import Q

from projetos.models import Despesa, EmpregadoProjeto


def obter_lista_despesas_admin(*, empresa):
    return (
        Despesa.objects.filter(empresa=empresa)
        .select_related("projeto", "furo", "maquina")
        .order_by("-data", "-criado_em")
    )


def obter_lista_despesas_empregado(*, empregado):
    projetos_ligacoes_ativas = EmpregadoProjeto.objects.filter(
        empregado=empregado,
        ativo=True,
    ).values_list("projeto_id", flat=True)
    projetos_registos = empregado.registos_diarios.filter(
        projeto__isnull=False,
        empresa=empregado.empresa,
    ).values_list("projeto_id", flat=True)
    projetos_ids = set(projetos_ligacoes_ativas).union(set(projetos_registos))

    return (
        Despesa.objects.filter(empresa=empregado.empresa)
        .filter(
            Q(projeto_id__in=projetos_ids)
            | Q(furo__projeto_id__in=projetos_ids)
            | Q(tipo="geral")
        )
        .select_related("projeto", "furo", "maquina")
        .distinct()
        .order_by("-data", "-criado_em")
    )
