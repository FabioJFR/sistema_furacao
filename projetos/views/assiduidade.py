from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
import csv
from openpyxl import Workbook

from core.permissions import admin_required
from projetos.forms import AssiduidadeRegistoForm
from projetos.models import AssiduidadeRegisto, Empregados
from projetos.selectors.assiduidade import (
    construir_contexto_calendario_equipa_empresa,
    listar_assiduidade_empresa_filtro,
    obter_assiduidade_empresa,
    resumo_horas_por_empregado,
    saldo_mensal_por_empregado,
)
from projetos.services.acesso_contexto import obter_empresa_admin_contexto
from projetos.services.assiduidade import (
    apagar_assiduidade,
    aprovar_assiduidade,
    atualizar_assiduidade,
    criar_assiduidade,
    rejeitar_assiduidade,
)


def _validation_error_message(exc):
    if hasattr(exc, "messages"):
        return " ".join(str(message) for message in exc.messages)
    return str(exc)


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


def _ler_filtros_assiduidade(request):
    hoje = timezone.localdate()
    return {
        "estado": request.GET.get("estado", "").strip(),
        "tipo": request.GET.get("tipo", "").strip(),
        "empregado_id": request.GET.get("empregado", "").strip(),
        "mes": request.GET.get("mes", str(hoje.month)).strip(),
        "ano": request.GET.get("ano", str(hoje.year)).strip(),
    }


def _query_assiduidade_filtrada(empresa, filtros):
    return listar_assiduidade_empresa_filtro(
        empresa,
        estado=filtros["estado"],
        tipo=filtros["tipo"],
        empregado_id=filtros["empregado_id"],
        mes=filtros["mes"],
        ano=filtros["ano"],
    )


@login_required
@admin_required
def assiduidade_list(request):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    hoje = timezone.localdate()
    filtros_query = _ler_filtros_assiduidade(request)
    items = _query_assiduidade_filtrada(empresa, filtros_query)
    resumo_horas = resumo_horas_por_empregado(empresa)
    saldo_mes_raw = saldo_mensal_por_empregado(
        empresa,
        mes=filtros_query["mes"] or hoje.month,
        ano=filtros_query["ano"] or hoje.year,
    )
    saldo_mes = []
    for row in saldo_mes_raw:
        horas_presenca = row.get("horas_presenca") or 0.0
        horas_extras = row.get("horas_extras") or 0.0
        horas_falta = row.get("horas_falta") or 0.0
        row["saldo_horas"] = horas_presenca + horas_extras - horas_falta
        saldo_mes.append(row)
    calendario_equipa = construir_contexto_calendario_equipa_empresa(
        empresa,
        ano=filtros_query["ano"] or hoje.year,
        mes=filtros_query["mes"] or hoje.month,
        empregado_id=filtros_query["empregado_id"],
    )
    empregados_filtro = Empregados.objects.filter(empresa=empresa).order_by("nome")
    filtros = {
        "estado": filtros_query["estado"],
        "tipo": filtros_query["tipo"],
        "empregado": filtros_query["empregado_id"],
        "mes": str(filtros_query["mes"]),
        "ano": str(filtros_query["ano"]),
    }
    return render(
        request,
        "projetos/assiduidade_list.html",
        {
            "items": items,
            "resumo_horas": resumo_horas,
            "saldo_mes": saldo_mes,
            "calendario_equipa": calendario_equipa,
            "filtros": filtros,
            "empregados_filtro": empregados_filtro,
            "estado_choices": [("", "Todos")] + list(AssiduidadeRegisto.ESTADO_CHOICES),
            "tipo_choices": [("", "Todos")] + list(AssiduidadeRegisto.TIPO_CHOICES),
        },
    )


@login_required
@admin_required
def assiduidade_create(request):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    form = AssiduidadeRegistoForm(request.POST or None, empresa=empresa)
    if request.method == "POST" and form.is_valid():
        try:
            criar_assiduidade(form=form, empresa=empresa)
        except ValidationError as exc:
            form.add_error(None, exc)
            messages.error(request, _validation_error_message(exc))
        else:
            messages.success(request, "Registo de assiduidade criado com sucesso.")
            return redirect("projetos:assiduidade_list")
    return render(request, "projetos/assiduidade_form.html", {"form": form, "is_create": True})


@login_required
@admin_required
def assiduidade_update(request, pk):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    item = obter_assiduidade_empresa(pk=pk, empresa=empresa)
    form = AssiduidadeRegistoForm(request.POST or None, instance=item, empresa=empresa)
    if request.method == "POST" and form.is_valid():
        try:
            atualizar_assiduidade(form=form)
        except ValidationError as exc:
            form.add_error(None, exc)
            messages.error(request, _validation_error_message(exc))
        else:
            messages.success(request, "Registo de assiduidade atualizado com sucesso.")
            return redirect("projetos:assiduidade_list")
    return render(request, "projetos/assiduidade_form.html", {"form": form, "item": item, "is_create": False})


@login_required
@admin_required
def assiduidade_delete(request, pk):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    item = obter_assiduidade_empresa(pk=pk, empresa=empresa)
    if request.method == "POST":
        apagar_assiduidade(obj=item)
        messages.success(request, "Registo de assiduidade apagado com sucesso.")
        return redirect("projetos:assiduidade_list")
    return render(request, "projetos/assiduidade_confirm_delete.html", {"item": item})


@login_required
@admin_required
def assiduidade_aprovar(request, pk):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    item = obter_assiduidade_empresa(pk=pk, empresa=empresa)
    if request.method == "POST":
        try:
            aprovar_assiduidade(obj=item)
        except ValidationError as exc:
            messages.error(request, _validation_error_message(exc))
        else:
            messages.success(request, "Registo aprovado.")
    return redirect("projetos:assiduidade_list")


@login_required
@admin_required
def assiduidade_export_csv(request):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro

    filtros = _ler_filtros_assiduidade(request)
    items = _query_assiduidade_filtrada(empresa, filtros)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="assiduidade_filtrada.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            "Empregado",
            "Projeto",
            "Tipo",
            "Estado",
            "Data inicio",
            "Data fim",
            "Horas",
            "Motivo",
            "Notas",
        ]
    )
    for item in items:
        writer.writerow(
            [
                item.empregado.nome,
                item.projeto.nome if item.projeto else "",
                item.get_tipo_display(),
                item.get_estado_display(),
                item.data_inicio.strftime("%d/%m/%Y") if item.data_inicio else "",
                item.data_fim.strftime("%d/%m/%Y") if item.data_fim else "",
                f"{item.horas:.2f}",
                item.motivo or "",
                item.notas or "",
            ]
        )
    return response


@login_required
@admin_required
def assiduidade_export_excel(request):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro

    filtros = _ler_filtros_assiduidade(request)
    items = _query_assiduidade_filtrada(empresa, filtros)
    response = HttpResponse(content_type="application/vnd.ms-excel; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="assiduidade_filtrada.xls"'

    writer = csv.writer(response, delimiter="\t")
    writer.writerow(
        [
            "Empregado",
            "Projeto",
            "Tipo",
            "Estado",
            "Data inicio",
            "Data fim",
            "Horas",
            "Motivo",
            "Notas",
        ]
    )
    for item in items:
        writer.writerow(
            [
                item.empregado.nome,
                item.projeto.nome if item.projeto else "",
                item.get_tipo_display(),
                item.get_estado_display(),
                item.data_inicio.strftime("%d/%m/%Y") if item.data_inicio else "",
                item.data_fim.strftime("%d/%m/%Y") if item.data_fim else "",
                f"{item.horas:.2f}",
                item.motivo or "",
                item.notas or "",
            ]
        )
    return response


@login_required
@admin_required
def assiduidade_export_xlsx(request):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro

    filtros = _ler_filtros_assiduidade(request)
    items = _query_assiduidade_filtrada(empresa, filtros)
    wb = Workbook()
    ws = wb.active
    ws.title = "Assiduidade"
    ws.append(
        [
            "Empregado",
            "Projeto",
            "Tipo",
            "Estado",
            "Data inicio",
            "Data fim",
            "Horas",
            "Motivo",
            "Notas",
        ]
    )
    for item in items:
        ws.append(
            [
                item.empregado.nome,
                item.projeto.nome if item.projeto else "",
                item.get_tipo_display(),
                item.get_estado_display(),
                item.data_inicio.strftime("%d/%m/%Y") if item.data_inicio else "",
                item.data_fim.strftime("%d/%m/%Y") if item.data_fim else "",
                float(f"{item.horas:.2f}"),
                item.motivo or "",
                item.notas or "",
            ]
        )

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="assiduidade_filtrada.xlsx"'
    wb.save(response)
    return response


@login_required
@admin_required
def assiduidade_rejeitar(request, pk):
    empresa, resposta_erro = _resolver_empresa_admin(request)
    if resposta_erro:
        return resposta_erro
    item = obter_assiduidade_empresa(pk=pk, empresa=empresa)
    if request.method == "POST":
        rejeitar_assiduidade(obj=item)
        messages.success(request, "Registo rejeitado.")
    return redirect("projetos:assiduidade_list")
