from django.contrib.auth.models import User
from django.db.models import Case, IntegerField, Q, Value, When

from plataforma.models import Empresa
from projetos.models import EmpregadoFuro, Empregados, Furo, Material, PlaneamentoTurno, Projeto, RegistoDiarioEmpregado


def resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


def listar_empregados_empresa_qs(empresa):
    if empresa is None:
        return Empregados.objects.none()
    return Empregados.objects.filter(empresa_id=resolver_empresa_id(empresa)).order_by("nome")


def listar_projetos_empresa_qs(empresa):
    if empresa is None:
        return Projeto.objects.none()
    return Projeto.objects.filter(empresa_id=resolver_empresa_id(empresa)).order_by("nome")


def listar_furos_empresa_qs(empresa):
    if empresa is None:
        return Furo.objects.none()
    return Furo.objects.filter(empresa_id=resolver_empresa_id(empresa)).order_by("nome")


def listar_furos_por_projeto_qs(projeto_id, *, empresa=None):
    queryset = Furo.objects.filter(projeto_id=projeto_id)
    if empresa is not None:
        queryset = queryset.filter(empresa_id=resolver_empresa_id(empresa))
    return queryset.order_by("nome")


def listar_projetos_empregado_qs(empregado, *, empresa=None):
    if not empregado:
        return Projeto.objects.none()
    queryset = empregado.projetos_atuais
    if empresa is not None:
        queryset = queryset.filter(empresa_id=resolver_empresa_id(empresa))
    return queryset


def listar_furos_empregado_qs(empregado, *, empresa=None):
    if not empregado:
        return Furo.objects.none()
    projetos_atuais = listar_projetos_empregado_qs(empregado, empresa=empresa)
    if empresa is not None:
        return Furo.objects.filter(
            empresa_id=resolver_empresa_id(empresa),
            projeto__in=projetos_atuais,
        ).distinct().order_by("nome")
    return Furo.objects.filter(projeto__in=projetos_atuais).distinct().order_by("nome")


def listar_planeamentos_empregado_qs(empregado, *, empresa=None, data=None):
    if not empregado:
        return PlaneamentoTurno.objects.none()
    queryset = (
        PlaneamentoTurno.objects.filter(Q(empregado=empregado) | Q(empregado__isnull=True))
        .exclude(estado="cancelado")
        .annotate(
            disponibilidade_ordem=Case(
                When(empregado=empregado, then=Value(0)),
                When(empregado__isnull=True, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        )
    )
    if empresa is not None:
        queryset = queryset.filter(empresa_id=resolver_empresa_id(empresa))
    if data is not None:
        queryset = queryset.filter(data_inicio__lte=data).filter(Q(data_fim__isnull=True, data_inicio=data) | Q(data_fim__gte=data))
    return queryset.select_related("projeto", "furo", "maquina").order_by("disponibilidade_ordem", "data_inicio", "hora_inicio", "turno", "nome")


def listar_planeamentos_empresa_qs(empresa):
    if empresa is None:
        return PlaneamentoTurno.objects.none()
    return (
        PlaneamentoTurno.objects.filter(empresa_id=resolver_empresa_id(empresa))
        .select_related("empregado", "projeto", "furo", "maquina")
        .order_by("-data_inicio", "turno", "nome")
    )


def listar_materiais_ativos_com_stock_qs(empresa):
    if empresa is None:
        return Material.objects.none()
    return (
        Material.objects.filter(
            ativo=True,
            quantidade__gt=0,
            empresa_id=resolver_empresa_id(empresa),
        )
        .order_by("nome")
    )


def listar_materiais_ativos_qs(empresa):
    if empresa is None:
        return Material.objects.none()
    return Material.objects.filter(ativo=True, empresa_id=resolver_empresa_id(empresa)).order_by("nome")


def listar_empresas_por_nome(valor):
    return Empresa.objects.filter(Q(nome__iexact=valor) | Q(nome_comercial__iexact=valor)).order_by("nome")


def existe_user_por_email(email):
    return User.objects.filter(email__iexact=email).exists()


def existe_user_por_username(username):
    return User.objects.filter(username__iexact=username).exists()


def existe_empregado_por_email(email, *, exclude_pk=None):
    queryset = Empregados.objects.filter(email__iexact=email)
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)
    return queryset.exists()


def listar_users_disponiveis_para_empregado(*, empregado_pk=None):
    users_ocupados = (
        Empregados.objects.exclude(pk=empregado_pk if empregado_pk else None)
        .exclude(user__isnull=True)
        .values_list("user_id", flat=True)
    )
    return User.objects.exclude(id__in=users_ocupados).order_by("username")


def listar_empregados_furo_form_qs(*, empresa=None, furo=None, is_edicao=False):
    queryset = listar_empregados_empresa_qs(empresa)
    queryset = queryset.filter(ativo=True) if hasattr(Empregados, "ativo") else queryset
    if furo is not None and not is_edicao:
        empregados_ja_ligados = EmpregadoFuro.objects.filter(furo=furo).values_list("empregado_id", flat=True)
        queryset = queryset.exclude(id__in=empregados_ja_ligados)
    return queryset


def listar_furos_configuracao_perfuracao_qs(*, empregado=None, empresa=None):
    if empregado is None:
        queryset = Furo.objects.all()
        if empresa is not None:
            queryset = queryset.filter(empresa_id=resolver_empresa_id(empresa))
        return queryset.order_by("nome")

    furo_ids_associados = EmpregadoFuro.objects.filter(empregado=empregado).values_list("furo_id", flat=True)
    furo_ids_registos = RegistoDiarioEmpregado.objects.filter(
        empregado=empregado,
        furo__isnull=False,
    ).values_list("furo_id", flat=True)

    queryset = Furo.objects.filter(id__in=list(furo_ids_associados) + list(furo_ids_registos))
    if empresa is not None:
        queryset = queryset.filter(empresa_id=resolver_empresa_id(empresa))
    return queryset.distinct().order_by("nome")


def existe_projeto_nome_empresa(nome, empresa, *, exclude_pk=None):
    queryset = Projeto.objects.filter(
        nome__iexact=nome,
        empresa_id=resolver_empresa_id(empresa),
    )
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)
    return queryset.exists()
