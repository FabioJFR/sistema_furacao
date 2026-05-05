from django.shortcuts import get_object_or_404
from django.db.models import Case, F, FloatField, Sum, Value, When

from projetos.models import AssiduidadeRegisto


def listar_assiduidade_empresa(empresa):
    return (
        AssiduidadeRegisto.objects.filter(empresa=empresa)
        .select_related("empregado", "projeto")
        .order_by("-data_inicio", "-atualizado_em")
    )


def listar_assiduidade_empresa_filtro(empresa, *, estado="", tipo="", empregado_id="", mes="", ano=""):
    queryset = AssiduidadeRegisto.objects.filter(empresa=empresa).select_related("empregado", "projeto")
    if estado:
        queryset = queryset.filter(estado=estado)
    if tipo:
        queryset = queryset.filter(tipo=tipo)
    if empregado_id:
        queryset = queryset.filter(empregado_id=empregado_id)
    if mes:
        queryset = queryset.filter(data_inicio__month=mes)
    if ano:
        queryset = queryset.filter(data_inicio__year=ano)
    return queryset.order_by("-data_inicio", "-atualizado_em")


def obter_assiduidade_empresa(*, pk, empresa):
    return get_object_or_404(
        AssiduidadeRegisto.objects.select_related("empregado", "projeto"),
        pk=pk,
        empresa=empresa,
    )


def resumo_horas_por_empregado(empresa):
    return (
        AssiduidadeRegisto.objects.filter(empresa=empresa)
        .values(nome=F("empregado__nome"))
        .annotate(
            horas_aprovadas=Sum(
                Case(
                    When(estado="aprovado", then=F("horas")),
                    default=Value(0.0),
                    output_field=FloatField(),
                )
            ),
            horas_extras_aprovadas=Sum(
                Case(
                    When(estado="aprovado", tipo="hora_extra", then=F("horas")),
                    default=Value(0.0),
                    output_field=FloatField(),
                )
            ),
            faltas=Sum(
                Case(
                    When(tipo="falta", then=Value(1.0)),
                    default=Value(0.0),
                    output_field=FloatField(),
                )
            ),
        )
        .order_by("nome")
    )


def saldo_mensal_por_empregado(empresa, *, mes, ano):
    return (
        AssiduidadeRegisto.objects.filter(empresa=empresa, estado="aprovado", data_inicio__month=mes, data_inicio__year=ano)
        .values(nome=F("empregado__nome"))
        .annotate(
            horas_presenca=Sum(
                Case(
                    When(tipo="presenca", then=F("horas")),
                    default=Value(0.0),
                    output_field=FloatField(),
                )
            ),
            horas_extras=Sum(
                Case(
                    When(tipo="hora_extra", then=F("horas")),
                    default=Value(0.0),
                    output_field=FloatField(),
                )
            ),
            horas_falta=Sum(
                Case(
                    When(tipo="falta", then=F("horas")),
                    default=Value(0.0),
                    output_field=FloatField(),
                )
            ),
        )
        .order_by("nome")
    )
