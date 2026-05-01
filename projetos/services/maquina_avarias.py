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


def processar_fluxo_create_avaria_form(
    *,
    method,
    post_data,
    form_class,
    empresa_id,
    on_success,
):
    if method == "POST":
        form = form_class(post_data, empresa_id=empresa_id)
        if not form.is_valid():
            return {
                "ok": False,
                "form": form,
                "maquina": None,
            }
        maquina = form.cleaned_data["maquina"]
        furo = form.cleaned_data.get("furo")
        descricao = form.cleaned_data.get("descricao")
        on_success(maquina=maquina, furo=furo, descricao=descricao)
        return {
            "ok": True,
            "form": form,
            "maquina": maquina,
        }

    return {
        "ok": None,
        "form": form_class(empresa_id=empresa_id),
        "maquina": None,
    }


def processar_fluxo_update_avaria_form(
    *,
    method,
    post_data,
    form_class,
    avaria,
    ator_nome,
    responsavel_empregado,
    empresa_id=None,
):
    if method == "POST":
        if empresa_id is not None:
            form = form_class(post_data, instance=avaria, empresa_id=empresa_id)
        else:
            form = form_class(post_data, instance=avaria)
        if not form.is_valid():
            return {
                "ok": False,
                "form": form,
            }
        atualizar_avaria(
            avaria=avaria,
            status=form.cleaned_data["status"],
            solucao=form.cleaned_data.get("solucao", ""),
            responsavel_empregado=responsavel_empregado(form),
            ator_nome=ator_nome,
        )
        return {
            "ok": True,
            "form": form,
        }

    if empresa_id is not None:
        form = form_class(instance=avaria, empresa_id=empresa_id)
    else:
        form = form_class(instance=avaria)
    return {
        "ok": None,
        "form": form,
    }
