from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from core.permissions import admin_required
from projetos.forms import PlaneamentoTurnoForm
from projetos.models import PlaneamentoTurno
from projetos.selectors.planeamento_turnos import (
    listar_planeamentos_empresa,
    obter_planeamento_empresa,
    resumir_capacidade_por_turno,
)
from projetos.services.acesso_contexto import obter_empresa_admin_contexto
from projetos.services.planeamento_analise import detetar_conflitos_planeamento
from projetos.services.planeamento_analise import escolher_planeamento_cancelar_automatico
from projetos.services.planeamento_turnos import (
    apagar_planeamento_turno,
    atualizar_planeamento_turno,
    criar_planeamento_turno,
)


def _resolver_empresa_admin(request):
    empresa, resposta_erro = obter_empresa_admin_contexto(
        request=request,
        mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
        mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa válida.",
        redirect_sem_permissao="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:dashboard",
    )
    if resposta_erro:
        return None, resposta_erro
    return empresa, None


@login_required
@admin_required
def planeamento_turno_list(request):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    filtros = {
        "estado": (request.GET.get("estado") or "").strip(),
        "turno": (request.GET.get("turno") or "").strip(),
        "data_inicio": (request.GET.get("data_inicio") or "").strip(),
        "data_fim": (request.GET.get("data_fim") or "").strip(),
    }
    items_qs = listar_planeamentos_empresa(empresa, filtros=filtros)
    items = list(items_qs)
    conflitos = detetar_conflitos_planeamento(items=items)
    resumo_bruto = resumir_capacidade_por_turno(queryset=items_qs)
    turno_map = dict(PlaneamentoTurno.TURNO_CHOICES)
    estado_map = dict(PlaneamentoTurno.ESTADO_CHOICES)
    resumo_turno = [
        {
            "turno": turno_map.get(row["turno"], row["turno"]),
            "estado": estado_map.get(row["estado"], row["estado"]),
            "total": row["total"],
        }
        for row in resumo_bruto
    ]
    return render(
        request,
        "projetos/planeamento_turno_list.html",
        {
            "items": items,
            "filtros": filtros,
            "estado_choices": [("", _("Todos"))] + list(PlaneamentoTurno.ESTADO_CHOICES),
            "turno_choices": [("", _("Todos"))] + list(PlaneamentoTurno.TURNO_CHOICES),
            "conflitos": conflitos,
            "resumo_turno": resumo_turno,
        },
    )


@login_required
@admin_required
def planeamento_turno_create(request):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    form = PlaneamentoTurnoForm(request.POST or None, empresa=empresa)
    if request.method == "POST" and form.is_valid():
        criar_planeamento_turno(form=form, empresa=empresa)
        messages.success(request, "Planeamento criado com sucesso.")
        return redirect("projetos:planeamento_turno_list")
    return render(request, "projetos/planeamento_turno_form.html", {"form": form, "is_create": True})


@login_required
@admin_required
def planeamento_turno_update(request, pk):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    item = obter_planeamento_empresa(pk=pk, empresa=empresa)
    form = PlaneamentoTurnoForm(request.POST or None, instance=item, empresa=empresa)
    if request.method == "POST" and form.is_valid():
        atualizar_planeamento_turno(form=form)
        messages.success(request, "Planeamento atualizado com sucesso.")
        return redirect("projetos:planeamento_turno_list")
    return render(request, "projetos/planeamento_turno_form.html", {"form": form, "item": item, "is_create": False})


@login_required
@admin_required
def planeamento_turno_delete(request, pk):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    item = obter_planeamento_empresa(pk=pk, empresa=empresa)
    if request.method == "POST":
        apagar_planeamento_turno(obj=item)
        messages.success(request, "Planeamento apagado com sucesso.")
        return redirect("projetos:planeamento_turno_list")
    return render(request, "projetos/planeamento_turno_confirm_delete.html", {"item": item})


@login_required
@admin_required
def planeamento_turno_resolver_conflito(request, a_pk, b_pk):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro

    item_a = obter_planeamento_empresa(pk=a_pk, empresa=empresa)
    item_b = obter_planeamento_empresa(pk=b_pk, empresa=empresa)

    a_inicio = item_a.data_inicio
    a_fim = item_a.data_fim or item_a.data_inicio
    b_inicio = item_b.data_inicio
    b_fim = item_b.data_fim or item_b.data_inicio
    conflito_inicio = max(a_inicio, b_inicio)
    conflito_fim = min(a_fim, b_fim)
    existe_sobreposicao = conflito_inicio <= conflito_fim

    if request.method == "POST":
        acao = request.POST.get("acao")
        if acao == "auto_resolver":
            alvo_item, motivo = escolher_planeamento_cancelar_automatico(item_a=item_a, item_b=item_b)
            alvo_item.estado = "cancelado"
            alvo_item.save(update_fields=["estado", "atualizado_em"])
            messages.success(
                request,
                _("Conflito resolvido automaticamente: foi cancelado '%(nome)s' (%(motivo)s).")
                % {"nome": str(alvo_item), "motivo": motivo},
            )
            return redirect("projetos:planeamento_turno_resolver_conflito", a_pk=a_pk, b_pk=b_pk)

        alvo = request.POST.get("alvo")
        novo_estado = request.POST.get("estado")
        alvo_item = item_a if alvo == "a" else item_b if alvo == "b" else None
        if alvo_item is None:
            messages.error(request, _("Alvo de atualização inválido."))
            return redirect("projetos:planeamento_turno_resolver_conflito", a_pk=a_pk, b_pk=b_pk)
        if novo_estado not in {"planeado", "confirmado", "concluido", "cancelado"}:
            messages.error(request, _("Estado inválido."))
            return redirect("projetos:planeamento_turno_resolver_conflito", a_pk=a_pk, b_pk=b_pk)
        alvo_item.estado = novo_estado
        alvo_item.save(update_fields=["estado", "atualizado_em"])
        messages.success(request, _("Estado atualizado com sucesso."))
        return redirect("projetos:planeamento_turno_resolver_conflito", a_pk=a_pk, b_pk=b_pk)

    return render(
        request,
        "projetos/planeamento_turno_resolver_conflito.html",
        {
            "item_a": item_a,
            "item_b": item_b,
            "existe_sobreposicao": existe_sobreposicao,
            "conflito_inicio": conflito_inicio,
            "conflito_fim": conflito_fim,
        },
    )
