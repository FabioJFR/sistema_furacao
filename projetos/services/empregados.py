from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils import timezone

from projetos.models import EmpregadoProjeto


# TODO futuro:
# - centralizar validações multiempresa num helper/base service reutilizável
# - substituir password temporária hardcoded por geração segura + fluxo de ativação
# - adicionar auditoria para aprovações, criação de utilizadores e encerramento de ligações



def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)



def _obter_ou_criar_grupo_empregados():
    grupo, _ = Group.objects.get_or_create(name="Empregados")
    return grupo



def _gerar_username_empregado(empregado):
    return empregado.email or empregado.nome.replace(" ", "").lower()



def _validar_ligacao_empresa(ligacao, empresa=None):
    if empresa is None:
        return

    empresa_id = _resolver_empresa_id(empresa)

    if ligacao.empresa_id and ligacao.empresa_id != empresa_id:
        raise ValidationError("A ligação não pertence à empresa atual.")
    if ligacao.empregado.empresa_id and ligacao.empregado.empresa_id != empresa_id:
        raise ValidationError("O empregado da ligação não pertence à empresa atual.")
    if ligacao.projeto.empresa_id and ligacao.projeto.empresa_id != empresa_id:
        raise ValidationError("O projeto da ligação não pertence à empresa atual.")



def validar_empregado_empresa(empregado, empresa=None):
    if not empregado:
        raise ValidationError("Empregado inválido.")

    if empresa is not None and empregado.empresa_id != _resolver_empresa_id(empresa):
        raise ValidationError("O empregado não pertence à empresa atual.")



def recalcular_resumo_empregado(empregado, empresa=None):
    validar_empregado_empresa(empregado, empresa=empresa)

    hoje = timezone.now().date()
    inicio_mes = hoje.replace(day=1)

    registos = empregado.registos_diarios.all()

    if empresa is not None:
        registos = registos.filter(empresa_id=_resolver_empresa_id(empresa))

    total_horas = registos.aggregate(total=Sum("horas_trabalhadas"))["total"] or 0
    horas_mes = registos.filter(data__gte=inicio_mes, data__lte=hoje).aggregate(
        total=Sum("horas_trabalhadas")
    )["total"] or 0
    horas_hoje = registos.filter(data=hoje).aggregate(total=Sum("horas_trabalhadas"))["total"] or 0

    total_metros = registos.aggregate(total=Sum("metros_furados"))["total"] or 0
    metros_mes = registos.filter(data__gte=inicio_mes, data__lte=hoje).aggregate(
        total=Sum("metros_furados")
    )["total"] or 0
    metros_hoje = registos.filter(data=hoje).aggregate(total=Sum("metros_furados"))["total"] or 0

    total_furos = registos.exclude(furo__isnull=True).values("furo").distinct().count()
    total_dias_com_registo = registos.values("data").distinct().count()

    media_m_h = total_metros / total_horas if total_horas > 0 else 0
    media_m_d = total_metros / total_dias_com_registo if total_dias_com_registo > 0 else 0

    empregado.horas_total = total_horas
    empregado.horas_trabalhadas_mes = horas_mes
    empregado.horas_diarias = horas_hoje

    empregado.total_metros_furados = total_metros
    empregado.metros_furados_mes = metros_mes
    empregado.metros_furados_hoje = metros_hoje
    empregado.total_furos_trabalhados = total_furos
    empregado.media_metros_por_hora = round(media_m_h, 2)
    empregado.media_metros_por_dia = round(media_m_d, 2)

    empregado.save(
        update_fields=[
            "horas_total",
            "horas_trabalhadas_mes",
            "horas_diarias",
            "total_metros_furados",
            "metros_furados_mes",
            "metros_furados_hoje",
            "total_furos_trabalhados",
            "media_metros_por_hora",
            "media_metros_por_dia",
        ]
    )



def criar_utilizador_para_empregado(empregado, empresa=None):
    validar_empregado_empresa(empregado, empresa=empresa)

    username = _gerar_username_empregado(empregado)
    password = "123456"

    if empregado.user_id:
        raise ValidationError("Este empregado já tem um utilizador associado.")

    if User.objects.filter(username__iexact=username).exists():
        raise ValidationError("Já existe um utilizador com este nome de utilizador.")

    user = User.objects.create_user(
        username=username,
        password=password,
        email=empregado.email,
    )

    empregado.user = user
    empregado.save(update_fields=["user"])

    grupo = _obter_ou_criar_grupo_empregados()
    user.groups.add(grupo)

    return empregado



def criar_empregado_com_utilizador(empregado, empresa=None):
    return criar_utilizador_para_empregado(empregado, empresa=empresa)



def aprovar_empregado(empregado, empresa=None):
    validar_empregado_empresa(empregado, empresa=empresa)

    empregado.aprovado = True
    empregado.data_aprovacao = timezone.now()
    empregado.save(update_fields=["aprovado", "data_aprovacao"])

    if empregado.user:
        empregado.user.is_active = True
        empregado.user.save(update_fields=["is_active"])

        grupo = _obter_ou_criar_grupo_empregados()
        empregado.user.groups.add(grupo)

    return empregado



def terminar_ligacao_projeto_empregado(ligacao, empresa=None):
    _validar_ligacao_empresa(ligacao, empresa=empresa)

    ligacao.ativo = False
    if not ligacao.data_fim:
        ligacao.data_fim = timezone.now().date()
    ligacao.save(update_fields=["ativo", "data_fim"])
    return ligacao



def terminar_projeto_empregado(ligacao, empresa=None):
    return terminar_ligacao_projeto_empregado(ligacao, empresa=empresa)



def empregado_ja_tem_projeto_ativo(empregado, projeto, excluir_ligacao_id=None, empresa=None):
    validar_empregado_empresa(empregado, empresa=empresa)

    if empresa is not None and projeto.empresa_id != _resolver_empresa_id(empresa):
        raise ValidationError("O projeto não pertence à empresa atual.")

    qs = EmpregadoProjeto.objects.filter(
        empregado=empregado,
        projeto=projeto,
        ativo=True,
    )

    if empresa is not None:
        qs = qs.filter(empresa_id=_resolver_empresa_id(empresa))

    if excluir_ligacao_id:
        qs = qs.exclude(id=excluir_ligacao_id)

    return qs.exists()