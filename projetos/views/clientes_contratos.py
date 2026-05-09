import logging
from urllib.parse import urlencode

from django.db.models import Sum
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from core.permissions import admin_required
from projetos.forms import ClienteComercialForm, ClienteContratoAdendaForm, ClienteContratoAnexoForm, ClienteContratoForm
from projetos.models import ClienteContrato, ClienteContratoAdenda, ClienteContratoAnexo, ClienteContratoWorkflowHistorico, Projeto
from projetos.selectors.clientes_contratos import (
    listar_adendas_cliente_contrato,
    listar_anexos_cliente_contrato,
    listar_clientes_contratos_empresa,
    obter_cliente_contrato_empresa,
)
from projetos.services.acesso_contexto import obter_empresa_admin_contexto
from projetos.services.clientes_contratos import (
    apagar_cliente_contrato,
    apagar_cliente_contrato_adenda,
    apagar_cliente_contrato_anexo,
    aplicar_sugestao_workflow_cliente_contrato,
    atualizar_ficha_cliente_comercial,
    atualizar_cliente_contrato,
    atualizar_cliente_contrato_adenda,
    construir_ficha_cliente_comercial,
    construir_painel_comercial_clientes,
    construir_timeline_cliente_contrato,
    criar_cliente_contrato,
    criar_cliente_contrato_adenda,
    criar_cliente_contrato_anexo,
    gerar_pdf_ficha_cliente_comercial,
    gerar_zip_dossier_cliente_contrato,
    obter_alertas_operacionais_cliente_contrato,
    obter_data_fim_efetiva_cliente_contrato,
    obter_ou_criar_ficha_cliente_comercial,
    obter_sugestoes_workflow_cliente_contrato,
    obter_total_adendas_cliente_contrato,
    processar_renovacao_automatica_cliente_contrato,
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
        "workflow": (request.GET.get("workflow") or "").strip(),
        "projeto_id": (request.GET.get("projeto_id") or "").strip(),
        "termo": (request.GET.get("termo") or "").strip(),
        "vencimento": (request.GET.get("vencimento") or "").strip(),
    }

    if leitura_global:
        items_qs = ClienteContrato.objects.select_related("projeto", "empresa").order_by("empresa__nome", "nome_cliente")
        if filtros["status"]:
            items_qs = items_qs.filter(status=filtros["status"])
        if filtros["workflow"]:
            items_qs = items_qs.filter(workflow_comercial=filtros["workflow"])
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
        processar_renovacao_automatica_cliente_contrato(cliente_contrato=item)
        data_fim_efetiva = obter_data_fim_efetiva_cliente_contrato(cliente_contrato=item)
        total_adendas = obter_total_adendas_cliente_contrato(cliente_contrato=item)
        alertas_operacionais = obter_alertas_operacionais_cliente_contrato(cliente_contrato=item)
        sugestoes_workflow = obter_sugestoes_workflow_cliente_contrato(cliente_contrato=item)
        dias_para_fim = None
        alerta_vencimento = ""
        em_alerta_configurado = False
        if data_fim_efetiva:
            dias_para_fim = (data_fim_efetiva - hoje).days
            if dias_para_fim < 0:
                alerta_vencimento = "vencido"
            elif dias_para_fim <= 7:
                alerta_vencimento = "7d"
            elif dias_para_fim <= 30:
                alerta_vencimento = "30d"
            else:
                alerta_vencimento = "ok"
            em_alerta_configurado = dias_para_fim <= item.dias_alerta_vencimento

        if filtros["vencimento"] and filtros["vencimento"] != alerta_vencimento:
            continue

        itens.append(
            {
                "obj": item,
                "data_fim_efetiva": data_fim_efetiva,
                "dias_para_fim": dias_para_fim,
                "alerta_vencimento": alerta_vencimento,
                "em_alerta_configurado": em_alerta_configurado,
                "total_adendas": total_adendas,
                "valor_total_estimado": (item.valor_contratado or 0.0) + total_adendas,
                "renovacoes_total": item.adendas.filter(origem="renovacao_automatica").count(),
                "alertas_operacionais": alertas_operacionais,
                "sugestao_workflow_principal": sugestoes_workflow[0] if sugestoes_workflow else None,
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
            "workflow_choices": [("", _("Todos"))] + list(ClienteContrato.WORKFLOW_COMERCIAL_CHOICES),
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
def cliente_contrato_painel_clientes(request):
    leitura_global = bool(request.user.is_superuser)
    filtros = {
        "status": (request.GET.get("status") or "").strip(),
        "workflow": (request.GET.get("workflow") or "").strip(),
        "projeto_id": (request.GET.get("projeto_id") or "").strip(),
        "termo": (request.GET.get("termo") or "").strip(),
    }

    if leitura_global:
        contratos_qs = ClienteContrato.objects.select_related("projeto", "empresa").order_by("empresa__nome", "nome_cliente")
        if filtros["status"]:
            contratos_qs = contratos_qs.filter(status=filtros["status"])
        if filtros["workflow"]:
            contratos_qs = contratos_qs.filter(workflow_comercial=filtros["workflow"])
        if filtros["projeto_id"]:
            contratos_qs = contratos_qs.filter(projeto_id=filtros["projeto_id"])
        if filtros["termo"]:
            contratos_qs = contratos_qs.filter(nome_cliente__icontains=filtros["termo"])
    else:
        empresa, resposta_erro = _resolver_empresa_admin_clientes(request)
        if resposta_erro:
            return resposta_erro
        contratos_qs = listar_clientes_contratos_empresa(empresa, filtros=filtros)

    painel_clientes = construir_painel_comercial_clientes(
        contratos=list(contratos_qs),
        incluir_empresa=leitura_global,
    )
    projeto_choices = []
    if not leitura_global:
        projeto_choices = Projeto.objects.filter(empresa=empresa).order_by("nome").values("id", "nome")

    total_contratos = sum(item["total_contratos"] for item in painel_clientes)
    total_alertas = sum(item["contratos_com_alerta"] for item in painel_clientes)
    total_followups_atrasados = sum(item["followups_atrasados"] for item in painel_clientes)
    valor_total_estimado = sum(item["valor_total_estimado"] for item in painel_clientes)

    return render(
        request,
        "projetos/cliente_contrato_painel_clientes.html",
        {
            "painel_clientes": painel_clientes,
            "somente_leitura": leitura_global,
            "filtros": filtros,
            "status_choices": [("", _("Todos"))] + list(ClienteContrato.STATUS_CHOICES),
            "workflow_choices": [("", _("Todos"))] + list(ClienteContrato.WORKFLOW_COMERCIAL_CHOICES),
            "projeto_choices": projeto_choices,
            "total_clientes": len(painel_clientes),
            "total_contratos": total_contratos,
            "total_alertas": total_alertas,
            "total_followups_atrasados": total_followups_atrasados,
            "valor_total_estimado": valor_total_estimado,
        },
    )


@login_required
@admin_required
def cliente_comercial_detail(request):
    leitura_global = bool(request.user.is_superuser)
    nome_cliente = (request.GET.get("cliente") or "").strip()
    if not nome_cliente:
        messages.error(request, "Cliente inválido.")
        return redirect("projetos:cliente_contrato_painel_clientes")

    filtros = {
        "status": "",
        "workflow": "",
        "projeto_id": "",
        "termo": nome_cliente,
    }

    empresa_nome = ""
    if leitura_global:
        contratos_qs = ClienteContrato.objects.select_related("projeto", "empresa").filter(nome_cliente__iexact=nome_cliente)
        empresa_id = (request.GET.get("empresa_id") or "").strip()
        if empresa_id:
            contratos_qs = contratos_qs.filter(empresa_id=empresa_id)
        contratos_qs = contratos_qs.order_by("empresa__nome", "nome_cliente", "numero_contrato")
        primeiro = contratos_qs.first()
        empresa_nome = getattr(getattr(primeiro, "empresa", None), "nome", "") if primeiro else ""
        empresa_ficha = getattr(primeiro, "empresa", None) if primeiro else None
    else:
        empresa, resposta_erro = _resolver_empresa_admin_clientes(request)
        if resposta_erro:
            return resposta_erro
        contratos_qs = listar_clientes_contratos_empresa(empresa, filtros=filtros).order_by("nome_cliente", "numero_contrato")
        empresa_nome = empresa.nome
        empresa_ficha = empresa

    contratos = list(contratos_qs)
    ficha_cliente_model = None
    if empresa_ficha is not None:
        ficha_cliente_model, _ = obter_ou_criar_ficha_cliente_comercial(
            empresa=empresa_ficha,
            nome_cliente=nome_cliente,
            create_if_missing=not leitura_global,
        )
    ficha_cliente = construir_ficha_cliente_comercial(
        contratos=contratos,
        nome_cliente=nome_cliente,
        empresa_nome=empresa_nome,
        ficha_cliente_model=ficha_cliente_model,
    )
    if not ficha_cliente:
        messages.error(request, "Cliente não encontrado.")
        return redirect("projetos:cliente_contrato_painel_clientes")

    return render(
        request,
        "projetos/cliente_comercial_detail.html",
        {
            "ficha_cliente": ficha_cliente,
            "somente_leitura": leitura_global,
        },
    )


@login_required
@admin_required
def cliente_comercial_exportar_pdf(request):
    leitura_global = bool(request.user.is_superuser)
    nome_cliente = (request.GET.get("cliente") or "").strip()
    if not nome_cliente:
        messages.error(request, "Cliente inválido.")
        return redirect("projetos:cliente_contrato_painel_clientes")

    filtros = {
        "status": "",
        "workflow": "",
        "projeto_id": "",
        "termo": nome_cliente,
    }

    empresa_nome = ""
    if leitura_global:
        contratos_qs = ClienteContrato.objects.select_related("projeto", "empresa").filter(nome_cliente__iexact=nome_cliente)
        empresa_id = (request.GET.get("empresa_id") or "").strip()
        if empresa_id:
            contratos_qs = contratos_qs.filter(empresa_id=empresa_id)
        contratos_qs = contratos_qs.order_by("empresa__nome", "nome_cliente", "numero_contrato")
        primeiro = contratos_qs.first()
        empresa_nome = getattr(getattr(primeiro, "empresa", None), "nome", "") if primeiro else ""
        empresa_ficha = getattr(primeiro, "empresa", None) if primeiro else None
    else:
        empresa, resposta_erro = _resolver_empresa_admin_clientes(request)
        if resposta_erro:
            return resposta_erro
        contratos_qs = listar_clientes_contratos_empresa(empresa, filtros=filtros).order_by("nome_cliente", "numero_contrato")
        empresa_nome = empresa.nome
        empresa_ficha = empresa

    contratos = list(contratos_qs)
    ficha_cliente_model = None
    if empresa_ficha is not None:
        ficha_cliente_model, _ = obter_ou_criar_ficha_cliente_comercial(
            empresa=empresa_ficha,
            nome_cliente=nome_cliente,
            create_if_missing=not leitura_global,
        )
    ficha_cliente = construir_ficha_cliente_comercial(
        contratos=contratos,
        nome_cliente=nome_cliente,
        empresa_nome=empresa_nome,
        ficha_cliente_model=ficha_cliente_model,
    )
    if not ficha_cliente:
        messages.error(request, "Cliente não encontrado.")
        return redirect("projetos:cliente_contrato_painel_clientes")

    pdf_bytes, nome_pdf = gerar_pdf_ficha_cliente_comercial(ficha_cliente=ficha_cliente)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{nome_pdf}"'
    return response


@login_required
@admin_required
def cliente_comercial_update(request):
    if request.user.is_superuser:
        messages.error(request, "Conta de plataforma em modo auditoria: edição desativada nesta área.")
        return redirect("projetos:cliente_contrato_painel_clientes")

    nome_cliente = (request.GET.get("cliente") or request.POST.get("cliente") or "").strip()
    if not nome_cliente:
        messages.error(request, "Cliente inválido.")
        return redirect("projetos:cliente_contrato_painel_clientes")

    empresa, resposta_erro = _resolver_empresa_admin_clientes(request)
    if resposta_erro:
        return resposta_erro

    ficha_cliente, _ = obter_ou_criar_ficha_cliente_comercial(empresa=empresa, nome_cliente=nome_cliente)
    form = ClienteComercialForm(request.POST or None, instance=ficha_cliente)
    if request.method == "POST" and form.is_valid():
        atualizar_ficha_cliente_comercial(form=form, ficha_cliente=ficha_cliente)
        messages.success(request, "Ficha comercial do cliente atualizada com sucesso.")
        return redirect(
            f"{reverse('projetos:cliente_comercial_detail')}?{urlencode({'cliente': nome_cliente})}"
        )

    return render(
        request,
        "projetos/cliente_comercial_form.html",
        {
            "form": form,
            "nome_cliente": nome_cliente,
            "empresa": empresa,
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
        criar_cliente_contrato(form=form, empresa=empresa, user=request.user)
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
        item = get_object_or_404(
            ClienteContrato.objects.select_related("projeto", "empresa").prefetch_related("anexos", "adendas", "historico_workflow__alterado_por"),
            pk=pk,
        )
    else:
        empresa, resposta_erro = _resolver_empresa_admin_clientes(request)
        if resposta_erro:
            return resposta_erro
        item = obter_cliente_contrato_empresa(pk=pk, empresa=empresa)
    processar_renovacao_automatica_cliente_contrato(cliente_contrato=item)
    item.refresh_from_db()
    anexos = listar_anexos_cliente_contrato(cliente_contrato=item)
    adendas = listar_adendas_cliente_contrato(cliente_contrato=item)
    total_adendas = adendas.aggregate(total=Sum("valor_adicional")).get("total") or 0.0
    hoje = timezone.localdate()
    data_fim_efetiva = obter_data_fim_efetiva_cliente_contrato(cliente_contrato=item)
    dias_para_fim = (data_fim_efetiva - hoje).days if data_fim_efetiva else None
    renovacoes = adendas.filter(origem="renovacao_automatica")
    alertas_operacionais = obter_alertas_operacionais_cliente_contrato(cliente_contrato=item)
    sugestoes_workflow = obter_sugestoes_workflow_cliente_contrato(cliente_contrato=item)
    historico_workflow = ClienteContratoWorkflowHistorico.objects.filter(contrato=item).select_related("alterado_por")
    timeline = construir_timeline_cliente_contrato(
        cliente_contrato=item,
        anexos=anexos,
        adendas=adendas,
        workflow_historico=historico_workflow,
    )
    return render(
        request,
        "projetos/cliente_contrato_detail.html",
        {
            "item": item,
            "somente_leitura": leitura_global,
            "anexos": anexos,
            "adendas": adendas,
            "total_adendas": total_adendas,
            "valor_total_estimado": (item.valor_contratado or 0.0) + total_adendas,
            "data_fim_efetiva": data_fim_efetiva,
            "dias_para_fim": dias_para_fim,
            "renovacao_em_alerta": bool(dias_para_fim is not None and dias_para_fim <= item.dias_alerta_vencimento),
            "renovacoes": renovacoes,
            "alertas_operacionais": alertas_operacionais,
            "sugestoes_workflow": sugestoes_workflow,
            "historico_workflow": historico_workflow,
            "timeline": timeline,
        },
    )


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
        atualizar_cliente_contrato(form=form, user=request.user)
        messages.success(request, "Cliente/Contrato atualizado com sucesso.")
        return redirect("projetos:cliente_contrato_detail", pk=item.pk)
    return render(
        request,
        "projetos/cliente_contrato_form.html",
        {"form": form, "item": item, "is_create": False},
    )


@login_required
@admin_required
def cliente_contrato_aplicar_sugestao_workflow(request, pk):
    if request.user.is_superuser:
        messages.error(request, "Conta de plataforma em modo auditoria: ação desativada nesta área.")
        return redirect("projetos:cliente_contrato_detail", pk=pk)

    if request.method != "POST":
        return redirect("projetos:cliente_contrato_detail", pk=pk)

    empresa, resposta_erro = _resolver_empresa_admin_clientes(request)
    if resposta_erro:
        return resposta_erro

    item = obter_cliente_contrato_empresa(pk=pk, empresa=empresa)
    workflow_novo = (request.POST.get("workflow_novo") or "").strip()
    observacao = (request.POST.get("observacao") or "").strip()

    try:
        alterado = aplicar_sugestao_workflow_cliente_contrato(
            cliente_contrato=item,
            workflow_novo=workflow_novo,
            user=request.user,
            observacao=observacao,
        )
    except ValueError:
        messages.error(request, "Sugestão de workflow inválida.")
        return redirect("projetos:cliente_contrato_detail", pk=item.pk)

    if alterado:
        messages.success(request, "Sugestão de workflow aplicada com sucesso.")
    else:
        messages.info(request, "O contrato já estava nesse workflow.")
    return redirect("projetos:cliente_contrato_detail", pk=item.pk)


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


@login_required
@admin_required
def cliente_contrato_exportar_dossier(request, pk):
    leitura_global = bool(request.user.is_superuser)
    if leitura_global:
        item = get_object_or_404(
            ClienteContrato.objects.select_related("projeto", "empresa").prefetch_related("anexos", "adendas"),
            pk=pk,
        )
    else:
        empresa, resposta_erro = _resolver_empresa_admin_clientes(request)
        if resposta_erro:
            return resposta_erro
        item = obter_cliente_contrato_empresa(pk=pk, empresa=empresa)

    processar_renovacao_automatica_cliente_contrato(cliente_contrato=item)
    anexos = listar_anexos_cliente_contrato(cliente_contrato=item)
    adendas = listar_adendas_cliente_contrato(cliente_contrato=item)
    conteudo_zip, nome_zip = gerar_zip_dossier_cliente_contrato(cliente_contrato=item, anexos=anexos, adendas=adendas)
    response = HttpResponse(conteudo_zip, content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{nome_zip}"'
    return response


@login_required
@admin_required
def cliente_contrato_anexo_create(request, pk):
    if request.user.is_superuser:
        messages.error(request, "Conta de plataforma em modo auditoria: criação desativada nesta área.")
        return redirect("projetos:cliente_contrato_detail", pk=pk)

    empresa, resposta_erro = _resolver_empresa_admin_clientes(request)
    if resposta_erro:
        return resposta_erro

    item = obter_cliente_contrato_empresa(pk=pk, empresa=empresa)
    form = ClienteContratoAnexoForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        criar_cliente_contrato_anexo(form=form, cliente_contrato=item)
        messages.success(request, "Anexo do contrato adicionado com sucesso.")
        return redirect("projetos:cliente_contrato_detail", pk=item.pk)
    return render(
        request,
        "projetos/cliente_contrato_anexo_form.html",
        {"form": form, "item": item},
    )


@login_required
@admin_required
def cliente_contrato_anexo_delete(request, contrato_pk, pk):
    if request.user.is_superuser:
        messages.error(request, "Conta de plataforma em modo auditoria: remoção desativada nesta área.")
        return redirect("projetos:cliente_contrato_detail", pk=contrato_pk)

    empresa, resposta_erro = _resolver_empresa_admin_clientes(request)
    if resposta_erro:
        return resposta_erro

    item = obter_cliente_contrato_empresa(pk=contrato_pk, empresa=empresa)
    anexo = get_object_or_404(ClienteContratoAnexo, pk=pk, contrato=item, empresa=empresa)
    if request.method == "POST":
        apagar_cliente_contrato_anexo(anexo=anexo)
        messages.success(request, "Anexo do contrato apagado com sucesso.")
        return redirect("projetos:cliente_contrato_detail", pk=item.pk)
    return render(
        request,
        "projetos/cliente_contrato_anexo_confirm_delete.html",
        {"item": item, "anexo": anexo},
    )


@login_required
@admin_required
def cliente_contrato_adenda_create(request, pk):
    if request.user.is_superuser:
        messages.error(request, "Conta de plataforma em modo auditoria: criação desativada nesta área.")
        return redirect("projetos:cliente_contrato_detail", pk=pk)

    empresa, resposta_erro = _resolver_empresa_admin_clientes(request)
    if resposta_erro:
        return resposta_erro

    item = obter_cliente_contrato_empresa(pk=pk, empresa=empresa)
    form = ClienteContratoAdendaForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        criar_cliente_contrato_adenda(form=form, cliente_contrato=item)
        messages.success(request, "Adenda registada com sucesso.")
        return redirect("projetos:cliente_contrato_detail", pk=item.pk)
    return render(
        request,
        "projetos/cliente_contrato_adenda_form.html",
        {"form": form, "item": item, "is_update": False},
    )


@login_required
@admin_required
def cliente_contrato_adenda_update(request, contrato_pk, pk):
    if request.user.is_superuser:
        messages.error(request, "Conta de plataforma em modo auditoria: edição desativada nesta área.")
        return redirect("projetos:cliente_contrato_detail", pk=contrato_pk)

    empresa, resposta_erro = _resolver_empresa_admin_clientes(request)
    if resposta_erro:
        return resposta_erro

    item = obter_cliente_contrato_empresa(pk=contrato_pk, empresa=empresa)
    adenda = get_object_or_404(ClienteContratoAdenda, pk=pk, contrato=item, empresa=empresa)
    form = ClienteContratoAdendaForm(request.POST or None, request.FILES or None, instance=adenda)
    if request.method == "POST" and form.is_valid():
        atualizar_cliente_contrato_adenda(form=form, cliente_contrato=item)
        messages.success(request, "Adenda atualizada com sucesso.")
        return redirect("projetos:cliente_contrato_detail", pk=item.pk)
    return render(
        request,
        "projetos/cliente_contrato_adenda_form.html",
        {"form": form, "item": item, "adenda": adenda, "is_update": True},
    )


@login_required
@admin_required
def cliente_contrato_adenda_delete(request, contrato_pk, pk):
    if request.user.is_superuser:
        messages.error(request, "Conta de plataforma em modo auditoria: remoção desativada nesta área.")
        return redirect("projetos:cliente_contrato_detail", pk=contrato_pk)

    empresa, resposta_erro = _resolver_empresa_admin_clientes(request)
    if resposta_erro:
        return resposta_erro

    item = obter_cliente_contrato_empresa(pk=contrato_pk, empresa=empresa)
    adenda = get_object_or_404(ClienteContratoAdenda, pk=pk, contrato=item, empresa=empresa)
    if request.method == "POST":
        apagar_cliente_contrato_adenda(adenda=adenda)
        messages.success(request, "Adenda apagada com sucesso.")
        return redirect("projetos:cliente_contrato_detail", pk=item.pk)
    return render(
        request,
        "projetos/cliente_contrato_adenda_confirm_delete.html",
        {"item": item, "adenda": adenda},
    )
