from datetime import date, time

from django.contrib.auth.models import User

from plataforma.models import Empresa, PerfilPlataforma
from projetos.models import EmpregadoProjeto, Empregados, Furo, PlaneamentoTurno, Projeto


def criar_empresa(*, nome="Empresa Teste"):
    return Empresa.objects.create(
        nome=nome,
        nome_comercial=nome,
        status="ativa",
        ativo=True,
    )


def criar_user(*, username, password="testpass123", email=""):
    return User.objects.create_user(
        username=username,
        password=password,
        email=email or f"{username}@example.com",
    )


def criar_perfil(*, user, tipo_acesso, empresa=None):
    return PerfilPlataforma.objects.create(
        user=user,
        tipo_acesso=tipo_acesso,
        empresa=empresa,
        ativo=True,
    )


def criar_empregado(*, empresa, nome="Empregado Teste", user=None, aprovado=True, funcao="outro", email=""):
    return Empregados.objects.create(
        empresa=empresa,
        nome=nome,
        user=user,
        aprovado=aprovado,
        funcao=funcao,
        email=email or (getattr(user, "email", "") if user else ""),
    )


def criar_projeto(*, empresa, nome="Projeto Teste", cliente="Cliente Teste"):
    return Projeto.objects.create(
        empresa=empresa,
        nome=nome,
        cliente=cliente,
    )


def criar_ligacao_empregado_projeto(*, empregado, projeto, ativo=True):
    return EmpregadoProjeto.objects.create(
        empregado=empregado,
        projeto=projeto,
        ativo=ativo,
    )


def criar_furo(
    *,
    empresa,
    projeto,
    nome="Furo Teste",
    tipo="fundo",
    profundidade_inicial=0.0,
    profundidade_alvo_inicial=10.0,
    profundidade_alvo_atual=10.0,
):
    return Furo.objects.create(
        empresa=empresa,
        projeto=projeto,
        nome=nome,
        tipo=tipo,
        profundidade_inicial=profundidade_inicial,
        profundidade_alvo_inicial=profundidade_alvo_inicial,
        profundidade_alvo_atual=profundidade_alvo_atual,
        profundidade_atual=profundidade_inicial,
    )


def criar_planeamento_turno(
    *,
    empresa,
    projeto,
    empregado=None,
    furo=None,
    nome="Turno Teste",
    data_inicio=date(2026, 5, 5),
    data_fim=None,
    turno="tarde",
    estado="confirmado",
    hora_inicio=time(14, 0),
    hora_fim=time(22, 0),
):
    return PlaneamentoTurno.objects.create(
        empresa=empresa,
        projeto=projeto,
        empregado=empregado,
        furo=furo,
        nome=nome,
        data_inicio=data_inicio,
        data_fim=data_fim,
        turno=turno,
        estado=estado,
        hora_inicio=hora_inicio,
        hora_fim=hora_fim,
    )
