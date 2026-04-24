from django.db.models import Count, Q, Sum

from projetos.models import Furo


def listar_furos_memoria_operacional_qs(empresa):
    return (
        Furo.objects.filter(empresa=empresa)
        .select_related("projeto")
        .annotate(
            total_despesas_diretas=Sum("despesas__valor"),
            total_medicoes_registadas=Count("medicoes", distinct=True),
        )
    )


def aplicar_filtros_memoria_qs(
    queryset,
    *,
    termo,
    estado,
    com_coordenadas,
    despesas_altas,
):
    if termo:
        queryset = queryset.filter(
            Q(nome__icontains=termo)
            | Q(localizacao__icontains=termo)
            | Q(local_sondagem__icontains=termo)
            | Q(projeto__nome__icontains=termo)
        )
    if estado:
        queryset = queryset.filter(estado=estado)
    if com_coordenadas:
        queryset = queryset.filter(latitude__isnull=False, longitude__isnull=False)
    if despesas_altas:
        queryset = queryset.filter(total_despesas_diretas__gte=1000)
    return queryset
