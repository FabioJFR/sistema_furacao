import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from core.permissions import admin_required
from projetos.forms import ClienteContratoForm
from projetos.models import ClienteContrato, Projeto
from projetos.selectors.clientes_contratos import (
    listar_clientes_contratos_empresa,
    obter_cliente_contrato_empresa,
)
from projetos.services.acesso_contexto import obter_empresa_admin_contexto
from projetos.services.clientes_contratos import (
    apagar_cliente_contrato,
    atualizar_cliente_contrato,
    criar_cliente_contrato,
)

logger = logging.getLogger("core")


def _resolver_empresa_admin_clientes(request):
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
def cliente_contrato_list(request):
    leitura_global = bool(request.user.is_superuser)
    filtros = {
        "status": (request.GET.get("status") or "").strip(),
        "projeto_id": (request.GET.get("projeto_id") or "").strip(),
        "termo": (request.GET.get("termo") or "").strip(),
        "vencimento": (request.GET.get("vencimento") or "").strip(),
    }

    if leitura_global:
        items_qs = ClienteContrato.objects.select_related("projeto", "empresa").order_by("empresa__nome", "nome_cliente")
        if filtros["status"]:
            items_qs = items_qs.filter(status=filtros["status"])
        if filtros["projeto_id"]:
            items_qs = items_qs.filter(projeto_id=filtros["projeto_id"])
        if filtros["termo"]:
            items_qs = items_qs.filter(nome_cliente__icontains=filtros["termo"])
    else:
        empresa, resposta_erro = _resolver_empresa_admin_clientes(request)
        if resposta_erro:
            return resposta_erro
        items_qs = listar_clientes_contratos_empresa(empresa, filtros=filtros)

    hoje = timezone.localdate()
    # Regra visual de vencimento para gestão comercial.
    itens = []
    for item in items_qs:
        dias_para_fim = None
        alerta_vencimento = ""
        if item.data_fim:
            dias_para_fim = (item.data_fim - hoje).days
            if dias_para_fim < 0:
                alerta_vencimento = "vencido"
            elif dias_para_fim <= 7:
                alerta_vencimento = "7d"
            elif dias_para_fim <= 30:
                alerta_vencimento = "30d"
            else:
                alerta_vencimento = "ok"

        if filtros["vencimento"] and filtros["vencimento"] != alerta_vencimento:
            continue

        itens.append(
            {
                "obj": item,
                "dias_para_fim": dias_para_fim,
                "alerta_vencimento": alerta_vencimento,
            }
        )

    kpi_total = len(itens)
    kpi_vencidos = sum(1 for it in itens if it["alerta_vencimento"] == "vencido")
    kpi_7d = sum(1 for it in itens if it["alerta_vencimento"] == "7d")
    kpi_30d = sum(1 for it in itens if it["alerta_vencimento"] == "30d")

    projeto_choices = []
    if not leitura_global:
        projeto_choices = Projeto.objects.filter(empresa=empresa).order_by("nome").values("id", "nome")
    return render(
        request,
        "projetos/cliente_contrato_list.html",
        {
            "items": itens,
            "somente_leitura": leitura_global,
            "filtros": filtros,
            "status_choices": [("", _("Todos"))] + list(ClienteContrato.STATUS_CHOICES),
            "vencimento_choices": [
                ("", _("Todos")),
                ("vencido", _("Vencidos")),
                ("7d", _("Vence em 7 dias")),
                ("30d", _("Vence em 30 dias")),
                ("ok", _("Sem alerta")),
            ],
            "projeto_choices": projeto_choices,
            "kpi_total": kpi_total,
            "kpi_vencidos": kpi_vencidos,
            "kpi_7d": kpi_7d,
            "kpi_30d": kpi_30d,
        },
    )


@login_required
@admin_required
def cliente_contrato_create(request):
    if request.user.is_superuser:
        messages.error(request, "Conta de plataforma em modo auditoria: criação desativada nesta área.")
        return redirect("projetos:cliente_contrato_list")

    empresa, resposta_erro = _resolver_empresa_admin_clientes(request)
    if resposta_erro:
        return resposta_erro

    form = ClienteContratoForm(request.POST or None, empresa=empresa)
    if request.method == "POST" and form.is_valid():
        criar_cliente_contrato(form=form, empresa=empresa)
        messages.success(request, "Cliente/Contrato criado com sucesso.")
        return redirect("projetos:cliente_contrato_list")
    return render(
        request,
        "projetos/cliente_contrato_form.html",
        {"form": form, "is_create": True},
    )


@login_required
@admin_required
def cliente_contrato_detail(request, pk):
    leitura_global = bool(request.user.is_superuser)
    if leitura_global:
        from django.shortcuts import get_object_or_404
        from projetos.models import ClienteContrato
        item = get_object_or_404(ClienteContrato.objects.select_related("projeto", "empresa"), pk=pk)
    else:
        empresa, resposta_erro = _resolver_empresa_admin_clientes(request)
        if resposta_erro:
            return resposta_erro
        item = obter_cliente_contrato_empresa(pk=pk, empresa=empresa)
    return render(request, "projetos/cliente_contrato_detail.html", {"item": item, "somente_leitura": leitura_global})


@login_required
@admin_required
def cliente_contrato_update(request, pk):
    if request.user.is_superuser:
        messages.error(request, "Conta de plataforma em modo auditoria: edição desativada nesta área.")
        return redirect("projetos:cliente_contrato_detail", pk=pk)

    empresa, resposta_erro = _resolver_empresa_admin_clientes(request)
    if resposta_erro:
        return resposta_erro

    item = obter_cliente_contrato_empresa(pk=pk, empresa=empresa)
    form = ClienteContratoForm(request.POST or None, instance=item, empresa=empresa)
    if request.method == "POST" and form.is_valid():
        atualizar_cliente_contrato(form=form)
        messages.success(request, "Cliente/Contrato atualizado com sucesso.")
        return redirect("projetos:cliente_contrato_detail", pk=item.pk)
    return render(
        request,
        "projetos/cliente_contrato_form.html",
        {"form": form, "item": item, "is_create": False},
    )


@login_required
@admin_required
def cliente_contrato_delete(request, pk):
    if request.user.is_superuser:
        messages.error(request, "Conta de plataforma em modo auditoria: remoção desativada nesta área.")
        return redirect("projetos:cliente_contrato_detail", pk=pk)

    empresa, resposta_erro = _resolver_empresa_admin_clientes(request)
    if resposta_erro:
        return resposta_erro

    item = obter_cliente_contrato_empresa(pk=pk, empresa=empresa)
    if request.method == "POST":
        apagar_cliente_contrato(cliente_contrato=item)
        messages.success(request, "Cliente/Contrato apagado com sucesso.")
        return redirect("projetos:cliente_contrato_list")
    return render(request, "projetos/cliente_contrato_confirm_delete.html", {"item": item})
