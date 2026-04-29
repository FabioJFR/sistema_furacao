from django.utils import timezone

from projetos.models import MaquinaAvaria
from projetos.services.maquina_avaria_notificacoes import (
    notificar_atribuicao_responsavel,
    notificar_mudanca_estado,
)


def criar_avaria_por_empregado(*, empregado, maquina, furo=None, descricao=""):
    projeto = furo.projeto if furo else maquina.projeto_atual

    avaria = MaquinaAvaria.objects.create(
        empresa_id=empregado.empresa_id,
        maquina=maquina,
        projeto=projeto,
        furo=furo,
        reportado_por=empregado,
        data_inicio=timezone.now(),
        status="aberta",
        descricao=descricao or "",
    )
    notificar_mudanca_estado(avaria=avaria, ator_nome=empregado.nome or empregado.user.username)
    return avaria


def criar_avaria_por_admin(*, empresa, maquina, furo=None, descricao=""):
    projeto = furo.projeto if furo else maquina.projeto_atual

    avaria = MaquinaAvaria.objects.create(
        empresa=empresa,
        maquina=maquina,
        projeto=projeto,
        furo=furo,
        reportado_por=None,
        data_inicio=timezone.now(),
        status="aberta",
        descricao=descricao or "",
    )
    notificar_mudanca_estado(avaria=avaria, ator_nome="Administrador")
    return avaria


def atualizar_avaria(*, avaria, status, solucao="", responsavel_empregado=None, ator_nome="Sistema"):
    mudou_responsavel = (avaria.responsavel_empregado_id or None) != (
        responsavel_empregado.id if responsavel_empregado else None
    )
    mudou_estado = avaria.status != status

    avaria.responsavel_empregado = responsavel_empregado
    avaria.status = status
    if solucao is not None:
        avaria.solucao = solucao

    if status == "resolvida" and not avaria.data_fim:
        avaria.data_fim = timezone.now()
    if status != "resolvida":
        avaria.data_fim = None

    avaria.save()
    if mudou_responsavel and avaria.responsavel_empregado_id:
        notificar_atribuicao_responsavel(avaria=avaria)
    if mudou_estado:
        notificar_mudanca_estado(avaria=avaria, ator_nome=ator_nome)
    return avaria
