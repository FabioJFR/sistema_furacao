import csv
import io
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.db.utils import OperationalError, ProgrammingError
from openpyxl import Workbook

from core.permissions import admin_required
from projetos.forms import (
    AgendamentoRelatorioExecutivoForm,
    ChecklistHSEForm,
    IncidenteSegurancaForm,
    NotificacaoGestaoForm,
    PedidoCompraForm,
    RelatorioExecutivoEmailForm,
)
from projetos.models import (
    AssiduidadeRegisto,
    AgendamentoRelatorioExecutivo,
    ChecklistHSE,
    Despesa,
    Empregados,
    Furo,
    IncidenteSeguranca,
    MaquinaAvaria,
    NotificacaoGestao,
    PedidoCompra,
    PlaneamentoTurno,
    Projeto,
    RegistoDiarioEmpregado,
)
from projetos.services.acesso_contexto import obter_empresa_admin_contexto
from projetos.services.gestao_relatorios import (
    calcular_proximo_envio_agendado,
    construir_url_relatorio_com_filtros,
    enviar_relatorio_executivo_email,
    normalizar_destinos,
    resolver_destinos_relatorio,
)

logger = logging.getLogger("core")


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


def _obter_ou_criar_agendamento_relatorio(empresa):
    agendamento, _ = AgendamentoRelatorioExecutivo.objects.get_or_create(
        empresa=empresa,
        defaults={
            "ativo": False,
            "frequencia": "semanal",
            "dia_semana": 0,
            "dia_mes": 1,
            "incluir_csv": True,
            "incluir_xlsx": True,
        },
    )
    return agendamento


def _obter_filtros_compras(request):
    return {
        "estado": (request.GET.get("estado") or "").strip(),
        "prioridade": (request.GET.get("prioridade") or "").strip(),
        "projeto_id": (request.GET.get("projeto_id") or "").strip(),
        "categoria": (request.GET.get("categoria") or "").strip(),
        "q": (request.GET.get("q") or "").strip(),
    }


def _filtrar_pedidos_compra(*, empresa, filtros):
    qs = PedidoCompra.objects.filter(empresa=empresa).select_related("projeto", "solicitado_por")

    if filtros.get("estado"):
        qs = qs.filter(estado=filtros["estado"])
    if filtros.get("prioridade"):
        qs = qs.filter(prioridade=filtros["prioridade"])
    if filtros.get("projeto_id"):
        qs = qs.filter(projeto_id=filtros["projeto_id"])
    if filtros.get("categoria"):
        qs = qs.filter(categoria__icontains=filtros["categoria"])
    if filtros.get("q"):
        qs = qs.filter(descricao__icontains=filtros["q"])

    return qs.order_by("-criado_em")


def _render_secao(request, *, slug, titulo, descricao, proximos_passos, kpis=None, linhas=None):
    return render(
        request,
        "projetos/gestao_secao.html",
        {
            "slug": slug,
            "titulo": titulo,
            "descricao": descricao,
            "proximos_passos": proximos_passos,
            "kpis": kpis or [],
            "linhas": linhas or [],
        },
    )


@login_required
@admin_required
def gestao_hub(request):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro

    agora = timezone.now()
    sla_vencido = NotificacaoGestao.objects.filter(
        empresa=empresa,
        estado__in=["aberta", "em_andamento"],
        prazo__lt=agora,
    ).count()
    pedidos_pendentes = PedidoCompra.objects.filter(empresa=empresa, estado="pendente").count()
    avarias_abertas = MaquinaAvaria.objects.filter(empresa=empresa).exclude(status="resolvida").count()

    secoes = [
        {
            "titulo": _("Clientes & Contratos"),
            "descricao": _("Gestão de clientes, condições comerciais, SLA e documentos contratuais."),
            "url_name": "projetos:cliente_contrato_list",
            "icone": "🤝",
        },
        {
            "titulo": _("Planeamento"),
            "descricao": _("Planeamento de equipas, turnos, furos e máquinas com deteção de conflitos."),
            "url_name": "projetos:gestao_planeamento",
            "icone": "🗓️",
        },
        {
            "titulo": _("RH & Assiduidade"),
            "descricao": _("Férias, faltas, horas extra, banco de horas e validação de presença."),
            "url_name": "projetos:gestao_rh_assiduidade",
            "icone": "👥",
        },
        {
            "titulo": _("Compras & Fornecedores"),
            "descricao": _("Pedidos de compra, fornecedores, comparação de preço e histórico."),
            "url_name": "projetos:gestao_compras_fornecedores",
            "icone": "🛒",
        },
        {
            "titulo": _("Compliance & Segurança"),
            "descricao": _("Checklist HSE, incidentes, auditorias e validade documental."),
            "url_name": "projetos:gestao_compliance_seguranca",
            "icone": "🛡️",
        },
        {
            "titulo": _("Centro de Notificações"),
            "descricao": _("Fila de alertas e ações pendentes por prioridade operacional."),
            "url_name": "projetos:gestao_notificacoes",
            "icone": "🔔",
        },
        {
            "titulo": _("Relatórios Executivos"),
            "descricao": _("KPIs executivos semanais/mensais com exportação para gestão."),
            "url_name": "projetos:gestao_relatorios_executivos",
            "icone": "📑",
        },
    ]
    return render(
        request,
        "projetos/gestao_hub.html",
        {
            "secoes": secoes,
            "kpis": [
                {"titulo": _("SLA vencido"), "valor": str(sla_vencido)},
                {"titulo": _("Pedidos pendentes"), "valor": str(pedidos_pendentes)},
                {"titulo": _("Avarias em aberto"), "valor": str(avarias_abertas)},
            ],
        },
    )


@login_required
@admin_required
def gestao_clientes_contratos(request):
    return redirect("projetos:cliente_contrato_list")


@login_required
@admin_required
def gestao_planeamento(request):
    return redirect("projetos:planeamento_turno_list")


@login_required
@admin_required
def gestao_rh_assiduidade(request):
    return redirect("projetos:assiduidade_list")


@login_required
@admin_required
def gestao_compras_fornecedores(request):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro

    hoje = timezone.localdate()
    filtros = _obter_filtros_compras(request)
    despesas = Despesa.objects.filter(empresa=empresa)
    total = despesas.aggregate(total=Sum("valor"))["total"] or 0
    total_mes = despesas.filter(data__year=hoje.year, data__month=hoje.month).aggregate(total=Sum("valor"))["total"] or 0
    categorias = (
        despesas.values("categoria")
        .annotate(total=Sum("valor"), qtd=Count("id"))
        .order_by("-total")[:8]
    )
    recentes = despesas.select_related("projeto", "furo", "maquina").order_by("-data", "-criado_em")[:8]
    pedidos_qs = _filtrar_pedidos_compra(empresa=empresa, filtros=filtros)
    pedidos = pedidos_qs[:20]
    projetos_choices = Projeto.objects.filter(empresa=empresa).order_by("nome").values("id", "nome")
    kpi_pedidos_total = PedidoCompra.objects.filter(empresa=empresa).count()
    kpi_pedidos_filtrados = pedidos_qs.count()

    return render(
        request,
        "projetos/gestao_compras_fornecedores.html",
        {
            "titulo": _("Compras & Fornecedores"),
            "descricao": _("Resumo financeiro de compras e despesas com foco operacional."),
            "kpis": [
                {"titulo": _("Despesa total"), "valor": f"{total:,.2f} €"},
                {"titulo": _("Despesa do mês"), "valor": f"{total_mes:,.2f} €"},
                {"titulo": _("Registos"), "valor": str(despesas.count())},
            ],
            "categorias": categorias,
            "pedidos": pedidos,
            "filtros": filtros,
            "projetos_choices": projetos_choices,
            "estado_choices": [("", _("Todos"))] + list(PedidoCompra.ESTADO_CHOICES),
            "prioridade_choices": [("", _("Todos"))] + list(PedidoCompra.PRIORIDADE_CHOICES),
            "kpi_pedidos_total": kpi_pedidos_total,
            "kpi_pedidos_filtrados": kpi_pedidos_filtrados,
            "despesas_recentes": recentes,
            "proximos_passos": [
                _("Adicionar cadastro de fornecedores com SLA e avaliação."),
                _("Criar pedidos de compra com fluxo de aprovação."),
                _("Comparar propostas por preço e prazo automaticamente."),
            ],
        },
    )


@login_required
@admin_required
def gestao_compras_export_csv(request):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro

    filtros = _obter_filtros_compras(request)
    pedidos = _filtrar_pedidos_compra(empresa=empresa, filtros=filtros)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="pedidos_compra.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            "Data",
            "Descricao",
            "Projeto",
            "Solicitado por",
            "Categoria",
            "Fornecedor",
            "Prioridade",
            "Estado",
            "Valor estimado",
            "Data necessidade",
        ]
    )
    for p in pedidos:
        writer.writerow(
            [
                p.criado_em.strftime("%d/%m/%Y"),
                p.descricao,
                p.projeto.nome if p.projeto else "",
                p.solicitado_por.nome if p.solicitado_por else "",
                p.categoria or "",
                p.fornecedor_sugerido or "",
                p.get_prioridade_display(),
                p.get_estado_display(),
                f"{(p.valor_estimado or 0):.2f}",
                p.data_necessidade.strftime("%d/%m/%Y") if p.data_necessidade else "",
            ]
        )
    return response


@login_required
@admin_required
def gestao_compras_export_xlsx(request):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro

    filtros = _obter_filtros_compras(request)
    pedidos = _filtrar_pedidos_compra(empresa=empresa, filtros=filtros)

    wb = Workbook()
    ws = wb.active
    ws.title = "Pedidos Compra"
    ws.append(
        [
            "Data",
            "Descricao",
            "Projeto",
            "Solicitado por",
            "Categoria",
            "Fornecedor",
            "Prioridade",
            "Estado",
            "Valor estimado",
            "Data necessidade",
        ]
    )
    for p in pedidos:
        ws.append(
            [
                p.criado_em.strftime("%d/%m/%Y"),
                p.descricao,
                p.projeto.nome if p.projeto else "",
                p.solicitado_por.nome if p.solicitado_por else "",
                p.categoria or "",
                p.fornecedor_sugerido or "",
                p.get_prioridade_display(),
                p.get_estado_display(),
                float(f"{(p.valor_estimado or 0):.2f}"),
                p.data_necessidade.strftime("%d/%m/%Y") if p.data_necessidade else "",
            ]
        )

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="pedidos_compra.xlsx"'
    wb.save(response)
    return response


@login_required
@admin_required
def gestao_pedido_compra_create(request):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    form = PedidoCompraForm(request.POST or None, empresa=empresa)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.empresa = empresa
        obj.save()
        messages.success(request, "Pedido de compra criado com sucesso.")
        return redirect("projetos:gestao_compras_fornecedores")
    return render(request, "projetos/gestao_pedido_compra_form.html", {"form": form, "is_create": True})


@login_required
@admin_required
def gestao_pedido_compra_update(request, pk):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    item = PedidoCompra.objects.filter(empresa=empresa, pk=pk).first()
    if not item:
        messages.error(request, "Pedido não encontrado.")
        return redirect("projetos:gestao_compras_fornecedores")
    form = PedidoCompraForm(request.POST or None, instance=item, empresa=empresa)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Pedido atualizado com sucesso.")
        return redirect("projetos:gestao_compras_fornecedores")
    return render(
        request,
        "projetos/gestao_pedido_compra_form.html",
        {"form": form, "is_create": False, "item": item},
    )


@login_required
@admin_required
def gestao_pedido_compra_delete(request, pk):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    item = PedidoCompra.objects.filter(empresa=empresa, pk=pk).first()
    if not item:
        messages.error(request, "Pedido não encontrado.")
        return redirect("projetos:gestao_compras_fornecedores")
    if request.method == "POST":
        item.delete()
        messages.success(request, "Pedido apagado com sucesso.")
        return redirect("projetos:gestao_compras_fornecedores")
    return render(request, "projetos/gestao_pedido_compra_confirm_delete.html", {"item": item})


@login_required
@admin_required
def gestao_pedido_compra_estado(request, pk, estado):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    item = PedidoCompra.objects.filter(empresa=empresa, pk=pk).first()
    if not item:
        messages.error(request, "Pedido não encontrado.")
        return redirect("projetos:gestao_compras_fornecedores")
    if estado not in {"aprovado", "rejeitado"}:
        messages.error(request, "Estado inválido.")
        return redirect("projetos:gestao_compras_fornecedores")
    item.estado = estado
    item.aprovado_em = timezone.now()
    item.save(update_fields=["estado", "aprovado_em", "atualizado_em"])
    messages.success(request, f"Pedido {item.get_estado_display().lower()} com sucesso.")
    return redirect("projetos:gestao_compras_fornecedores")


@login_required
@admin_required
def gestao_compliance_seguranca(request):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro

    hoje = timezone.localdate()
    avarias = MaquinaAvaria.objects.filter(empresa=empresa)
    avarias_abertas = avarias.exclude(status="resolvida").count()
    avarias_resolvidas_30d = avarias.filter(
        status="resolvida",
        atualizado_em__date__gte=hoje - timedelta(days=30),
    ).count()
    empregados = Empregados.objects.filter(empresa=empresa)
    sem_contrato = empregados.filter(contrato__isnull=True).count()
    sem_curriculo = empregados.filter(curriculo__isnull=True).count()
    filtro_check = (request.GET.get("check_status") or "").strip()
    filtro_inc = (request.GET.get("inc_status") or "").strip()
    checklists = []
    incidentes = []
    checklists_nao_conformes = 0
    incidentes_abertos = 0

    try:
        checklists_qs = ChecklistHSE.objects.filter(empresa=empresa).select_related("projeto", "responsavel")
        if filtro_check:
            checklists_qs = checklists_qs.filter(status=filtro_check)
        checklists = list(checklists_qs.order_by("-data_check", "-criado_em")[:25])
        checklists_nao_conformes = ChecklistHSE.objects.filter(empresa=empresa, status="nao_conforme").count()

        incidentes_qs = IncidenteSeguranca.objects.filter(empresa=empresa).select_related("projeto", "reportado_por", "responsavel")
        if filtro_inc:
            incidentes_qs = incidentes_qs.filter(status=filtro_inc)
        incidentes = list(incidentes_qs.order_by("status", "-data_incidente", "-criado_em")[:25])
        incidentes_abertos = IncidenteSeguranca.objects.filter(empresa=empresa).exclude(status="fechado").count()
    except (ProgrammingError, OperationalError):
        messages.warning(
            request,
            _("Módulo de Compliance ainda sem migração aplicada. Executa `python manage.py migrate` para ativar todos os dados."),
        )

    return render(
        request,
        "projetos/gestao_compliance_seguranca.html",
        {
            "titulo": _("Compliance & Segurança"),
            "descricao": _("Monitorização de risco operacional e conformidade documental."),
            "kpis": [
                {"titulo": _("Avarias em aberto"), "valor": str(avarias_abertas)},
                {"titulo": _("Avarias resolvidas (30d)"), "valor": str(avarias_resolvidas_30d)},
                {"titulo": _("Empregados sem contrato"), "valor": str(sem_contrato)},
                {"titulo": _("Empregados sem currículo"), "valor": str(sem_curriculo)},
                {"titulo": _("Checklists não conformes"), "valor": str(checklists_nao_conformes)},
                {"titulo": _("Incidentes abertos"), "valor": str(incidentes_abertos)},
            ],
            "checklists": checklists,
            "incidentes": incidentes,
            "check_status_choices": [("", _("Todos"))] + list(ChecklistHSE.STATUS_CHOICES),
            "inc_status_choices": [("", _("Todos"))] + list(IncidenteSeguranca.STATUS_CHOICES),
            "filtros": {"check_status": filtro_check, "inc_status": filtro_inc},
        },
    )


@login_required
@admin_required
def gestao_checklist_hse_create(request):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    form = ChecklistHSEForm(request.POST or None, empresa=empresa)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.empresa = empresa
        item.save()
        messages.success(request, _("Checklist HSE criada com sucesso."))
        return redirect("projetos:gestao_compliance_seguranca")
    return render(request, "projetos/gestao_checklist_hse_form.html", {"form": form, "is_create": True})


@login_required
@admin_required
def gestao_checklist_hse_update(request, pk):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    item = ChecklistHSE.objects.filter(empresa=empresa, pk=pk).first()
    if not item:
        messages.error(request, _("Checklist HSE não encontrada."))
        return redirect("projetos:gestao_compliance_seguranca")
    form = ChecklistHSEForm(request.POST or None, instance=item, empresa=empresa)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Checklist HSE atualizada com sucesso."))
        return redirect("projetos:gestao_compliance_seguranca")
    return render(request, "projetos/gestao_checklist_hse_form.html", {"form": form, "is_create": False, "item": item})


@login_required
@admin_required
def gestao_checklist_hse_delete(request, pk):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    item = ChecklistHSE.objects.filter(empresa=empresa, pk=pk).first()
    if not item:
        messages.error(request, _("Checklist HSE não encontrada."))
        return redirect("projetos:gestao_compliance_seguranca")
    if request.method == "POST":
        item.delete()
        messages.success(request, _("Checklist HSE apagada com sucesso."))
        return redirect("projetos:gestao_compliance_seguranca")
    return render(request, "projetos/gestao_checklist_hse_confirm_delete.html", {"item": item})


@login_required
@admin_required
def gestao_incidente_create(request):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    form = IncidenteSegurancaForm(request.POST or None, empresa=empresa)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.empresa = empresa
        item.save()
        messages.success(request, _("Incidente registado com sucesso."))
        return redirect("projetos:gestao_compliance_seguranca")
    return render(request, "projetos/gestao_incidente_form.html", {"form": form, "is_create": True})


@login_required
@admin_required
def gestao_incidente_update(request, pk):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    item = IncidenteSeguranca.objects.filter(empresa=empresa, pk=pk).first()
    if not item:
        messages.error(request, _("Incidente não encontrado."))
        return redirect("projetos:gestao_compliance_seguranca")
    form = IncidenteSegurancaForm(request.POST or None, instance=item, empresa=empresa)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Incidente atualizado com sucesso."))
        return redirect("projetos:gestao_compliance_seguranca")
    return render(request, "projetos/gestao_incidente_form.html", {"form": form, "is_create": False, "item": item})


@login_required
@admin_required
def gestao_incidente_delete(request, pk):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    item = IncidenteSeguranca.objects.filter(empresa=empresa, pk=pk).first()
    if not item:
        messages.error(request, _("Incidente não encontrado."))
        return redirect("projetos:gestao_compliance_seguranca")
    if request.method == "POST":
        item.delete()
        messages.success(request, _("Incidente apagado com sucesso."))
        return redirect("projetos:gestao_compliance_seguranca")
    return render(request, "projetos/gestao_incidente_confirm_delete.html", {"item": item})


@login_required
@admin_required
def gestao_incidente_estado(request, pk, estado):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    item = IncidenteSeguranca.objects.filter(empresa=empresa, pk=pk).first()
    if not item:
        messages.error(request, _("Incidente não encontrado."))
        return redirect("projetos:gestao_compliance_seguranca")
    if estado not in {"aberto", "investigacao", "fechado"}:
        messages.error(request, _("Estado inválido."))
        return redirect("projetos:gestao_compliance_seguranca")
    item.status = estado
    item.save(update_fields=["status", "atualizado_em"])
    messages.success(request, _("Estado do incidente atualizado."))
    return redirect("projetos:gestao_compliance_seguranca")


@login_required
@admin_required
def gestao_notificacoes(request):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro

    pendentes_empregado = Empregados.objects.filter(empresa=empresa, aprovado=False).count()
    assiduidade_pendente = AssiduidadeRegisto.objects.filter(empresa=empresa, estado="pendente").count()
    avarias_abertas = MaquinaAvaria.objects.filter(empresa=empresa).exclude(status="resolvida").count()
    planeamentos_pendentes = PlaneamentoTurno.objects.filter(empresa=empresa, estado="planeado").count()

    fila = []
    if pendentes_empregado:
        fila.append([_("Alta"), _("Empregados pendentes"), str(pendentes_empregado)])
    if avarias_abertas:
        fila.append([_("Alta"), _("Avarias em aberto"), str(avarias_abertas)])
    if assiduidade_pendente:
        fila.append([_("Média"), _("Assiduidade pendente"), str(assiduidade_pendente)])
    if planeamentos_pendentes:
        fila.append([_("Média"), _("Planeamentos por confirmar"), str(planeamentos_pendentes)])
    estado_filtro = request.GET.get("estado", "").strip()
    prioridade_filtro = request.GET.get("prioridade", "").strip()
    notificacoes_qs = NotificacaoGestao.objects.filter(empresa=empresa)
    if estado_filtro:
        notificacoes_qs = notificacoes_qs.filter(estado=estado_filtro)
    if prioridade_filtro:
        notificacoes_qs = notificacoes_qs.filter(prioridade=prioridade_filtro)
    notificacoes = (
        notificacoes_qs
        .select_related("responsavel")
        .order_by("estado", "prazo", "-criado_em")[:20]
    )

    agora = timezone.now()
    linhas_notificacoes = []
    for n in notificacoes:
        if n.prazo is None or n.estado == "resolvida":
            sla = _("OK")
        elif n.prazo < agora:
            sla = _("Atrasado")
        elif (n.prazo - agora).total_seconds() <= 24 * 3600:
            sla = _("Em risco")
        else:
            sla = _("OK")
        linhas_notificacoes.append(
            {
                "id": n.id,
                "titulo": n.titulo,
                "prioridade": n.get_prioridade_display(),
                "estado": n.get_estado_display(),
                "responsavel": n.responsavel.nome if n.responsavel else "-",
                "prazo": n.prazo.strftime("%d/%m/%Y %H:%M") if n.prazo else "-",
                "sla": sla,
            }
        )

    return render(
        request,
        "projetos/gestao_notificacoes.html",
        {
            "titulo": _("Centro de Notificações"),
            "descricao": _("Fila operacional de pendências com prioridade."),
            "kpis": [
                {"titulo": _("Pendências críticas"), "valor": str(pendentes_empregado + avarias_abertas)},
                {"titulo": _("Pendências médias"), "valor": str(assiduidade_pendente + planeamentos_pendentes)},
            ],
            "fila": fila,
            "notificacoes": linhas_notificacoes,
            "filtros": {"estado": estado_filtro, "prioridade": prioridade_filtro},
            "estado_choices": [("", _("Todos"))] + list(NotificacaoGestao.ESTADO_CHOICES),
            "prioridade_choices": [("", _("Todos"))] + list(NotificacaoGestao.PRIORIDADE_CHOICES),
            "proximos_passos": [
                _("Adicionar atribuição por responsável e prazo limite."),
                _("Enviar alertas automáticos por email."),
                _("Criar histórico de resolução com SLA."),
            ],
        },
    )


@login_required
@admin_required
def gestao_notificacoes_export_csv(request):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro

    estado_filtro = request.GET.get("estado", "").strip()
    prioridade_filtro = request.GET.get("prioridade", "").strip()
    queryset = NotificacaoGestao.objects.filter(empresa=empresa)
    if estado_filtro:
        queryset = queryset.filter(estado=estado_filtro)
    if prioridade_filtro:
        queryset = queryset.filter(prioridade=prioridade_filtro)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="notificacoes_gestao.csv"'
    writer = csv.writer(response)
    writer.writerow(["Título", "Tipo", "Prioridade", "Estado", "Responsável", "Prazo", "SLA", "Detalhes"])

    agora = timezone.now()
    for n in queryset.select_related("responsavel").order_by("estado", "prazo", "-criado_em"):
        if n.prazo is None or n.estado == "resolvida":
            sla = "OK"
        elif n.prazo < agora:
            sla = "Atrasado"
        elif (n.prazo - agora).total_seconds() <= 24 * 3600:
            sla = "Em risco"
        else:
            sla = "OK"
        writer.writerow(
            [
                n.titulo,
                n.tipo or "",
                n.get_prioridade_display(),
                n.get_estado_display(),
                n.responsavel.nome if n.responsavel else "",
                n.prazo.strftime("%d/%m/%Y %H:%M") if n.prazo else "",
                sla,
                n.detalhes or "",
            ]
        )
    return response


@login_required
@admin_required
def gestao_notificacao_create(request):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    form = NotificacaoGestaoForm(request.POST or None, empresa=empresa)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.empresa = empresa
        obj.save()
        messages.success(request, "Notificação criada com sucesso.")
        return redirect("projetos:gestao_notificacoes")
    return render(request, "projetos/gestao_notificacao_form.html", {"form": form, "is_create": True})


@login_required
@admin_required
def gestao_notificacao_update(request, pk):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    item = NotificacaoGestao.objects.filter(empresa=empresa, pk=pk).first()
    if not item:
        messages.error(request, "Notificação não encontrada.")
        return redirect("projetos:gestao_notificacoes")
    form = NotificacaoGestaoForm(request.POST or None, instance=item, empresa=empresa)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Notificação atualizada com sucesso.")
        return redirect("projetos:gestao_notificacoes")
    return render(
        request,
        "projetos/gestao_notificacao_form.html",
        {"form": form, "is_create": False, "item": item},
    )


@login_required
@admin_required
def gestao_notificacao_delete(request, pk):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    item = NotificacaoGestao.objects.filter(empresa=empresa, pk=pk).first()
    if not item:
        messages.error(request, "Notificação não encontrada.")
        return redirect("projetos:gestao_notificacoes")
    if request.method == "POST":
        item.delete()
        messages.success(request, "Notificação apagada com sucesso.")
        return redirect("projetos:gestao_notificacoes")
    return render(request, "projetos/gestao_notificacao_confirm_delete.html", {"item": item})


@login_required
@admin_required
def gestao_notificacao_estado(request, pk, estado):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    item = NotificacaoGestao.objects.filter(empresa=empresa, pk=pk).first()
    if not item:
        messages.error(request, "Notificação não encontrada.")
        return redirect("projetos:gestao_notificacoes")
    if estado not in {"aberta", "em_andamento", "resolvida"}:
        messages.error(request, "Estado inválido.")
        return redirect("projetos:gestao_notificacoes")
    item.estado = estado
    item.save(update_fields=["estado", "atualizado_em"])
    messages.success(request, f"Notificação atualizada para {item.get_estado_display().lower()}.")
    return redirect("projetos:gestao_notificacoes")


@login_required
@admin_required
def gestao_relatorios_executivos(request):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro

    filtros = _obter_filtros_relatorio_executivo(request)
    relatorio = _montar_relatorio_executivo(empresa=empresa, filtros=filtros)
    default_email = (empresa.responsavel_email or empresa.email or "").strip()
    form_email = RelatorioExecutivoEmailForm(
        initial={
            "assunto": _("Relatório Executivo - %(empresa)s") % {"empresa": empresa.nome},
            "destinos": default_email,
            "incluir_csv": True,
            "incluir_xlsx": True,
        }
    )
    agendamento = _obter_ou_criar_agendamento_relatorio(empresa)
    form_agendamento = AgendamentoRelatorioExecutivoForm(instance=agendamento)
    proximo_envio = agendamento.proximo_envio_em
    if agendamento.ativo and not proximo_envio:
        proximo_envio = calcular_proximo_envio_agendado(agendamento=agendamento)

    return render(
        request,
        "projetos/gestao_relatorios_executivos.html",
        {
            "titulo": _("Relatórios Executivos"),
            "descricao": _("KPIs de alto nível para decisões de gestão, com período configurável."),
            "filtros": filtros,
            "kpis": relatorio["kpis"],
            "tendencia": relatorio["tendencia"],
            "financeiro": relatorio["financeiro"],
            "projetos_financeiro": relatorio["projetos_financeiro"],
            "rh": relatorio["rh"],
            "compliance": relatorio["compliance"],
            "form_email": form_email,
            "form_agendamento": form_agendamento,
            "agendamento": agendamento,
            "proximo_envio": proximo_envio,
        },
    )


@login_required
@admin_required
def gestao_relatorios_agendamento(request):
    if request.method != "POST":
        return redirect("projetos:gestao_relatorios_executivos")

    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro

    agendamento = _obter_ou_criar_agendamento_relatorio(empresa)
    form = AgendamentoRelatorioExecutivoForm(request.POST, instance=agendamento)
    if not form.is_valid():
        for erros in form.errors.values():
            for erro in erros:
                messages.error(request, erro)
        return redirect("projetos:gestao_relatorios_executivos")

    agendamento = form.save(commit=False)
    if agendamento.ativo:
        agendamento.proximo_envio_em = calcular_proximo_envio_agendado(agendamento=agendamento)
    else:
        agendamento.proximo_envio_em = None
    agendamento.save()

    messages.success(request, _("Agendamento do relatório executivo guardado com sucesso."))
    return redirect("projetos:gestao_relatorios_executivos")


@login_required
@admin_required
def gestao_relatorios_agendamento_executar_agora(request):
    if request.method != "POST":
        return redirect("projetos:gestao_relatorios_executivos")

    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro

    agendamento = _obter_ou_criar_agendamento_relatorio(empresa)
    try:
        _executar_envio_agendado_empresa(empresa=empresa, agendamento=agendamento, referencia=timezone.now())
    except Exception as exc:
        logger.exception("Falha ao executar envio agendado manual. empresa_id=%s", empresa.id)
        messages.error(request, _("Erro ao executar envio imediato: %(erro)s") % {"erro": str(exc)})
        return redirect("projetos:gestao_relatorios_executivos")

    if agendamento.ativo:
        agendamento.proximo_envio_em = calcular_proximo_envio_agendado(agendamento=agendamento)
    agendamento.ultimo_envio_em = timezone.now()
    agendamento.save(update_fields=["ultimo_envio_em", "proximo_envio_em", "atualizado_em"])
    messages.success(request, _("Relatório agendado enviado com sucesso."))
    return redirect("projetos:gestao_relatorios_executivos")


@login_required
@admin_required
def gestao_relatorios_export_csv(request):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    filtros = _obter_filtros_relatorio_executivo(request)
    relatorio = _montar_relatorio_executivo(empresa=empresa, filtros=filtros)
    csv_bytes = _gerar_relatorio_csv_bytes(filtros=filtros, relatorio=relatorio)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="relatorio_executivo.csv"'
    response.write(csv_bytes)
    return response


@login_required
@admin_required
def gestao_relatorios_export_xlsx(request):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    filtros = _obter_filtros_relatorio_executivo(request)
    relatorio = _montar_relatorio_executivo(empresa=empresa, filtros=filtros)
    xlsx_bytes = _gerar_relatorio_xlsx_bytes(filtros=filtros, relatorio=relatorio)

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="relatorio_executivo.xlsx"'
    response.write(xlsx_bytes)
    return response


@login_required
@admin_required
def gestao_relatorios_enviar_email(request):
    if request.method != "POST":
        return redirect("projetos:gestao_relatorios_executivos")

    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro

    filtros = _obter_filtros_relatorio_executivo(request)
    relatorio = _montar_relatorio_executivo(empresa=empresa, filtros=filtros)

    form = RelatorioExecutivoEmailForm(request.POST)
    if not form.is_valid():
        for erros in form.errors.values():
            for erro in erros:
                messages.error(request, erro)
        return redirect(construir_url_relatorio_com_filtros(filtros=filtros))

    destinos_form = form.cleaned_data.get("destinos_lista") or []
    destinos = resolver_destinos_relatorio(empresa=empresa, destinos_form=destinos_form)

    if not destinos:
        messages.error(request, _("Define pelo menos um destinatário de email."))
        return redirect(construir_url_relatorio_com_filtros(filtros=filtros))

    assunto = (form.cleaned_data.get("assunto") or "").strip()
    if not assunto:
        assunto = _("Relatório Executivo - %(empresa)s") % {"empresa": empresa.nome}
    incluir_csv = bool(form.cleaned_data.get("incluir_csv"))
    incluir_xlsx = bool(form.cleaned_data.get("incluir_xlsx"))

    try:
        resultado = enviar_relatorio_executivo_email(
            empresa=empresa,
            filtros=filtros,
            relatorio=relatorio,
            assunto=assunto,
            destinos=destinos,
            incluir_csv=incluir_csv,
            incluir_xlsx=incluir_xlsx,
            csv_bytes=_gerar_relatorio_csv_bytes(filtros=filtros, relatorio=relatorio),
            xlsx_bytes=_gerar_relatorio_xlsx_bytes(filtros=filtros, relatorio=relatorio),
        )
    except Exception as exc:
        messages.error(request, _("Erro ao enviar email: %(erro)s") % {"erro": str(exc)})
        return redirect(construir_url_relatorio_com_filtros(filtros=filtros))

    if resultado.enviados:
        messages.success(request, _("Relatório enviado por email com sucesso."))
    else:
        messages.warning(request, _("O envio foi processado mas nenhum email foi confirmado como enviado."))
    return redirect(construir_url_relatorio_com_filtros(filtros=filtros))


def _obter_filtros_relatorio_executivo(request):
    return {
        "data_inicio": (request.GET.get("data_inicio") or "").strip(),
        "data_fim": (request.GET.get("data_fim") or "").strip(),
    }


def _filtros_periodo_agendamento(*, agendamento, referencia=None):
    referencia = referencia or timezone.now()
    hoje = timezone.localtime(referencia).date()
    if agendamento.frequencia == "diario":
        inicio = hoje - timedelta(days=1)
        fim = inicio
    elif agendamento.frequencia == "semanal":
        fim = hoje
        inicio = hoje - timedelta(days=6)
    else:  # mensal
        inicio = hoje.replace(day=1)
        fim = hoje
    return {
        "data_inicio": inicio.isoformat(),
        "data_fim": fim.isoformat(),
    }


def _executar_envio_agendado_empresa(*, empresa, agendamento, referencia=None):
    filtros = _filtros_periodo_agendamento(agendamento=agendamento, referencia=referencia)
    relatorio = _montar_relatorio_executivo(empresa=empresa, filtros=filtros)
    destinos_agendamento = normalizar_destinos(agendamento.destinos or "")
    destinos = resolver_destinos_relatorio(empresa=empresa, destinos_form=destinos_agendamento)
    if not destinos:
        raise ValueError("Não existem destinatários válidos para o agendamento.")

    assunto = _("Relatório Executivo Agendado - %(empresa)s") % {"empresa": empresa.nome}
    enviar_relatorio_executivo_email(
        empresa=empresa,
        filtros=filtros,
        relatorio=relatorio,
        assunto=assunto,
        destinos=destinos,
        incluir_csv=bool(agendamento.incluir_csv),
        incluir_xlsx=bool(agendamento.incluir_xlsx),
        csv_bytes=_gerar_relatorio_csv_bytes(filtros=filtros, relatorio=relatorio),
        xlsx_bytes=_gerar_relatorio_xlsx_bytes(filtros=filtros, relatorio=relatorio),
    )


def _gerar_relatorio_csv_bytes(*, filtros, relatorio):
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow(["Periodo inicio", filtros["data_inicio"] or "-"])
    writer.writerow(["Periodo fim", filtros["data_fim"] or "-"])
    writer.writerow([])

    writer.writerow(["Metrica", "Valor"])
    for item in relatorio["kpis"]:
        writer.writerow([item["titulo"], item["valor"]])

    writer.writerow([])
    writer.writerow(["Financeiro", "Valor"])
    writer.writerow(["Despesas total (€)", f'{relatorio["financeiro"]["despesas_total"]:.2f}'])
    writer.writerow(["Despesas quantidade", relatorio["financeiro"]["despesas_qtd"]])
    writer.writerow(["Receita estimada por projeto (€)", f'{relatorio["projetos_financeiro"]["totais"]["receita_estimada"]:.2f}'])
    writer.writerow(["Margem estimada por projeto (€)", f'{relatorio["projetos_financeiro"]["totais"]["margem_estimada"]:.2f}'])

    writer.writerow([])
    writer.writerow(["Comparativo por projeto", "", "", "", "", "", ""])
    writer.writerow(
        [
            "Projeto",
            "Metros no período",
            "Registos",
            "Custo total (€)",
            "Receita estimada (€)",
            "Margem estimada (€)",
            "Custo/m",
        ]
    )
    for item in relatorio["projetos_financeiro"]["linhas"]:
        writer.writerow(
            [
                item["projeto_nome"],
                f'{item["metros"]:.2f}',
                item["registos"],
                f'{item["custo_total"]:.2f}',
                f'{item["receita_estimada"]:.2f}',
                f'{item["margem_estimada"]:.2f}',
                f'{item["custo_por_metro"]:.2f}',
            ]
        )

    writer.writerow([])
    writer.writerow(["RH", "Valor"])
    writer.writerow(["Horas presenca aprovadas", f'{relatorio["rh"]["horas_presenca"]:.2f}'])
    writer.writerow(["Horas extra aprovadas", f'{relatorio["rh"]["horas_extra"]:.2f}'])
    writer.writerow(["Horas falta aprovadas", f'{relatorio["rh"]["horas_falta"]:.2f}'])

    writer.writerow([])
    writer.writerow(["Compliance", "Valor"])
    writer.writerow(["Checklists total", relatorio["compliance"]["checklists_total"]])
    writer.writerow(["Checklists nao conformes", relatorio["compliance"]["checklists_nao_conformes"]])
    writer.writerow(["Incidentes total", relatorio["compliance"]["incidentes_total"]])
    writer.writerow(["Incidentes abertos", relatorio["compliance"]["incidentes_abertos"]])

    writer.writerow([])
    writer.writerow(["Tendencia despesas", "", ""])
    writer.writerow(["Mes", "Total (€)", "Registos"])
    for item in relatorio["tendencia"]:
        writer.writerow([item["mes"], f'{item["total"]:.2f}', item["qtd"]])

    return buffer.getvalue().encode("utf-8-sig")


def _gerar_relatorio_xlsx_bytes(*, filtros, relatorio):
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumo"
    ws.append(["Período início", filtros["data_inicio"] or "-"])
    ws.append(["Período fim", filtros["data_fim"] or "-"])
    ws.append([])
    ws.append(["Métrica", "Valor"])
    for item in relatorio["kpis"]:
        ws.append([item["titulo"], item["valor"]])

    ws2 = wb.create_sheet("Financeiro")
    ws2.append(["Indicador", "Valor"])
    ws2.append(["Despesas total (€)", float(f'{relatorio["financeiro"]["despesas_total"]:.2f}')])
    ws2.append(["Despesas quantidade", relatorio["financeiro"]["despesas_qtd"]])
    ws2.append(["Receita estimada por projeto (€)", float(f'{relatorio["projetos_financeiro"]["totais"]["receita_estimada"]:.2f}')])
    ws2.append(["Margem estimada por projeto (€)", float(f'{relatorio["projetos_financeiro"]["totais"]["margem_estimada"]:.2f}')])

    ws3 = wb.create_sheet("RH")
    ws3.append(["Indicador", "Valor"])
    ws3.append(["Horas presenca aprovadas", float(f'{relatorio["rh"]["horas_presenca"]:.2f}')])
    ws3.append(["Horas extra aprovadas", float(f'{relatorio["rh"]["horas_extra"]:.2f}')])
    ws3.append(["Horas falta aprovadas", float(f'{relatorio["rh"]["horas_falta"]:.2f}')])

    ws4 = wb.create_sheet("Compliance")
    ws4.append(["Indicador", "Valor"])
    ws4.append(["Checklists total", relatorio["compliance"]["checklists_total"]])
    ws4.append(["Checklists nao conformes", relatorio["compliance"]["checklists_nao_conformes"]])
    ws4.append(["Incidentes total", relatorio["compliance"]["incidentes_total"]])
    ws4.append(["Incidentes abertos", relatorio["compliance"]["incidentes_abertos"]])

    ws5 = wb.create_sheet("Tendencia")
    ws5.append(["Mes", "Total (€)", "Registos"])
    for item in relatorio["tendencia"]:
        ws5.append([item["mes"], float(f'{item["total"]:.2f}'), item["qtd"]])

    ws6 = wb.create_sheet("Projetos")
    ws6.append(["Projeto", "Metros no período", "Registos", "Custo total (€)", "Receita estimada (€)", "Margem estimada (€)", "Custo/m"])
    for item in relatorio["projetos_financeiro"]["linhas"]:
        ws6.append(
            [
                item["projeto_nome"],
                float(f'{item["metros"]:.2f}'),
                item["registos"],
                float(f'{item["custo_total"]:.2f}'),
                float(f'{item["receita_estimada"]:.2f}'),
                float(f'{item["margem_estimada"]:.2f}'),
                float(f'{item["custo_por_metro"]:.2f}'),
            ]
        )

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


def _montar_relatorio_executivo(*, empresa, filtros):
    despesas_qs = Despesa.objects.filter(empresa=empresa)
    assiduidade_qs = AssiduidadeRegisto.objects.filter(empresa=empresa, estado="aprovado")
    checklists_qs = ChecklistHSE.objects.filter(empresa=empresa)
    incidentes_qs = IncidenteSeguranca.objects.filter(empresa=empresa)
    registos_qs = RegistoDiarioEmpregado.objects.filter(empresa=empresa)

    data_inicio = filtros.get("data_inicio")
    data_fim = filtros.get("data_fim")
    if data_inicio:
        despesas_qs = despesas_qs.filter(data__gte=data_inicio)
        assiduidade_qs = assiduidade_qs.filter(data_inicio__gte=data_inicio)
        checklists_qs = checklists_qs.filter(data_check__gte=data_inicio)
        incidentes_qs = incidentes_qs.filter(data_incidente__gte=data_inicio)
        registos_qs = registos_qs.filter(data__gte=data_inicio)
    if data_fim:
        despesas_qs = despesas_qs.filter(data__lte=data_fim)
        assiduidade_qs = assiduidade_qs.filter(data_inicio__lte=data_fim)
        checklists_qs = checklists_qs.filter(data_check__lte=data_fim)
        incidentes_qs = incidentes_qs.filter(data_incidente__lte=data_fim)
        registos_qs = registos_qs.filter(data__lte=data_fim)

    projetos_qtd = Projeto.objects.filter(empresa=empresa).count()
    furos_qtd = Furo.objects.filter(empresa=empresa).count()
    empregados_qtd = Empregados.objects.filter(empresa=empresa).count()
    despesas_total = despesas_qs.aggregate(total=Sum("valor"))["total"] or 0

    horas_presenca = assiduidade_qs.filter(tipo="presenca").aggregate(total=Sum("horas"))["total"] or 0
    horas_extra = assiduidade_qs.filter(tipo="hora_extra").aggregate(total=Sum("horas"))["total"] or 0
    horas_falta = assiduidade_qs.filter(tipo="falta").aggregate(total=Sum("horas"))["total"] or 0

    checklists_total = 0
    checklists_nao_conformes = 0
    incidentes_total = 0
    incidentes_abertos = 0
    try:
        checklists_total = checklists_qs.count()
        checklists_nao_conformes = checklists_qs.filter(status="nao_conforme").count()
        incidentes_total = incidentes_qs.count()
        incidentes_abertos = incidentes_qs.exclude(status="fechado").count()
    except (ProgrammingError, OperationalError):
        pass

    tendencia_qs = (
        despesas_qs
        .annotate(mes=TruncMonth("data"))
        .values("mes")
        .annotate(total=Sum("valor"), qtd=Count("id"))
        .order_by("-mes")[:6]
    )
    tendencia = [
        {
            "mes": item["mes"].strftime("%m/%Y") if item["mes"] else "-",
            "total": float(item["total"] or 0),
            "qtd": int(item["qtd"] or 0),
        }
        for item in tendencia_qs
    ]

    despesas_por_projeto = {
        item["projeto_id"]: float(item["total"] or 0)
        for item in despesas_qs.filter(projeto__isnull=False).values("projeto_id").annotate(total=Sum("valor"))
    }
    registos_por_projeto = {
        item["projeto_id"]: {
            "metros": float(item["metros"] or 0),
            "registos": int(item["qtd"] or 0),
        }
        for item in registos_qs.filter(projeto__isnull=False).values("projeto_id").annotate(
            metros=Sum("metros_furados"),
            qtd=Count("id"),
        )
    }

    projetos_financeiro_linhas = []
    total_receita_estimada = 0.0
    total_margem_estimada = 0.0
    custo_por_metro_global = float(getattr(empresa, "custo_por_metro_cliente", 0) or 0)
    for projeto in Projeto.objects.filter(empresa=empresa).order_by("nome"):
        registo_info = registos_por_projeto.get(projeto.pk, {"metros": 0.0, "registos": 0})
        metros = float(registo_info["metros"] or 0)
        registos_total = int(registo_info["registos"] or 0)
        despesa_projeto = float(despesas_por_projeto.get(projeto.pk, 0) or 0)
        outros_gastos = float(projeto.outros_valores_gastos_associados or 0)
        custo_total = round(despesa_projeto + outros_gastos, 2)
        custo_por_metro_projeto = float(projeto.custo_por_metro_cliente_override or custo_por_metro_global)
        receita_estimada = round(metros * custo_por_metro_projeto, 2)
        margem_estimada = round(receita_estimada - custo_total, 2)
        total_receita_estimada += receita_estimada
        total_margem_estimada += margem_estimada

        projetos_financeiro_linhas.append(
            {
                "projeto_id": str(projeto.pk),
                "projeto_nome": projeto.nome,
                "metros": round(metros, 2),
                "registos": registos_total,
                "custo_total": custo_total,
                "receita_estimada": receita_estimada,
                "margem_estimada": margem_estimada,
                "custo_por_metro": round((custo_total / metros), 2) if metros > 0 else 0.0,
            }
        )

    return {
        "kpis": [
            {"titulo": _("Projetos ativos"), "valor": str(projetos_qtd)},
            {"titulo": _("Furos registados"), "valor": str(furos_qtd)},
            {"titulo": _("Empregados"), "valor": str(empregados_qtd)},
            {"titulo": _("Despesa no período"), "valor": f"{despesas_total:,.2f} €"},
        ],
        "financeiro": {
            "despesas_total": float(despesas_total),
            "despesas_qtd": despesas_qs.count(),
        },
        "projetos_financeiro": {
            "linhas": projetos_financeiro_linhas,
            "totais": {
                "receita_estimada": round(total_receita_estimada, 2),
                "margem_estimada": round(total_margem_estimada, 2),
            },
        },
        "rh": {
            "horas_presenca": float(horas_presenca),
            "horas_extra": float(horas_extra),
            "horas_falta": float(horas_falta),
        },
        "compliance": {
            "checklists_total": checklists_total,
            "checklists_nao_conformes": checklists_nao_conformes,
            "incidentes_total": incidentes_total,
            "incidentes_abertos": incidentes_abertos,
        },
        "tendencia": tendencia,
    }
