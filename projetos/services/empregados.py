from django.utils import timezone
from django.db.models import Sum
from django.contrib.auth.models import Group, User
from django.utils import timezone
from django.contrib.auth.models import Group, User
from django.utils import timezone
from projetos.models import EmpregadoProjeto
from projetos.models import Empregados, EmpregadoProjeto, EmpregadoFicheiro

# ------ RECALCULAR RESUMO EMPREGADO ---- ####
def recalcular_resumo_empregado(empregado):
    hoje = timezone.now().date()
    inicio_mes = hoje.replace(day=1)

    total_horas = empregado.registos_diarios.aggregate(
        total=Sum('horas_trabalhadas')
    )['total'] or 0

    horas_mes = empregado.registos_diarios.filter(
        data__gte=inicio_mes,
        data__lte=hoje
    ).aggregate(total=Sum('horas_trabalhadas'))['total'] or 0

    horas_hoje = empregado.registos_diarios.filter(
        data=hoje
    ).aggregate(total=Sum('horas_trabalhadas'))['total'] or 0

    total_metros = empregado.registos_diarios.aggregate(
        total=Sum('metros_furados')
    )['total'] or 0

    metros_mes = empregado.registos_diarios.filter(
        data__gte=inicio_mes,
        data__lte=hoje
    ).aggregate(total=Sum('metros_furados'))['total'] or 0

    metros_hoje = empregado.registos_diarios.filter(
        data=hoje
    ).aggregate(total=Sum('metros_furados'))['total'] or 0

    total_furos = empregado.registos_diarios.exclude(
        furo__isnull=True
    ).values('furo').distinct().count()

    total_dias_com_registo = empregado.registos_diarios.values('data').distinct().count()

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

    empregado.save(update_fields=[
        'horas_total',
        'horas_trabalhadas_mes',
        'horas_diarias',
        'total_metros_furados',
        'metros_furados_mes',
        'metros_furados_hoje',
        'total_furos_trabalhados',
        'media_metros_por_hora',
        'media_metros_por_dia',
    ])


def criar_empregado_com_utilizador(empregado):
    username = empregado.email or empregado.nome.replace(" ", "").lower()
    password = "123456"

    user = User.objects.create_user(
        username=username,
        password=password,
        email=empregado.email
    )

    empregado.user = user
    empregado.save()

    grupo, _ = Group.objects.get_or_create(name="Empregados")
    user.groups.add(grupo)

    return empregado


def aprovar_empregado(empregado):
    empregado.aprovado = True
    empregado.data_aprovacao = timezone.now()
    empregado.save()

    if empregado.user:
        empregado.user.is_active = True
        empregado.user.save()

        grupo, _ = Group.objects.get_or_create(name="Empregados")
        empregado.user.groups.add(grupo)

    return empregado


def terminar_projeto_empregado(ligacao):
    ligacao.ativo = False
    if not ligacao.data_fim:
        ligacao.data_fim = timezone.now().date()
    ligacao.save()
    return ligacao


def criar_utilizador_para_empregado(empregado):
    username = empregado.email or empregado.nome.replace(" ", "").lower()
    password = "123456"

    user = User.objects.create_user(
        username=username,
        password=password,
        email=empregado.email
    )

    empregado.user = user
    empregado.save()

    grupo, _ = Group.objects.get_or_create(name="Empregados")
    user.groups.add(grupo)

    return empregado


def aprovar_empregado(empregado):
    empregado.aprovado = True
    empregado.data_aprovacao = timezone.now()
    empregado.save()

    if empregado.user:
        empregado.user.is_active = True
        empregado.user.save()

        grupo, _ = Group.objects.get_or_create(name="Empregados")
        empregado.user.groups.add(grupo)

    return empregado


def terminar_ligacao_projeto_empregado(ligacao):
    ligacao.ativo = False
    if not ligacao.data_fim:
        ligacao.data_fim = timezone.now().date()
    ligacao.save()
    return ligacao


def empregado_ja_tem_projeto_ativo(empregado, projeto, excluir_ligacao_id=None):
    qs = EmpregadoProjeto.objects.filter(
        empregado=empregado,
        projeto=projeto,
        ativo=True
    )

    if excluir_ligacao_id:
        qs = qs.exclude(id=excluir_ligacao_id)

    return qs.exists()