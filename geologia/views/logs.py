from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.utils import timezone

from core.permissions import geologia_operacional_required, geologo_required
from geologia.selectors.logs import (
    obter_alertas_geotecnicos,
    construir_resumo_executivo_geologico,
    obter_conflitos_intervalos_logs,
    construir_linhas_relatorio_geologico,
    obter_anexos_log,
    obter_furo_log_geologico,
    obter_log_geologico,
    obter_mapa_litologico_furo,
    obter_logs_pendentes_validacao,
    obter_logs_envolvidos_conflito,
    obter_planeamento_amostragem_geologo,
    obter_qualidade_dados_logs_geologo,
    obter_correlacoes_geologia_perfuracao,
    obter_mapa_furos_geologo,
)
from geologia.selectors.dashboard import obter_furos_geologia_hub_qs, obter_logs_geologia_hub_qs
from projetos.services.opcoes_exportacao import (
    normalizar_linhas_exportacao,
    renderizar_csv_exportacao,
    renderizar_pdf_exportacao,
    renderizar_xlsx_exportacao,
)
from geologia.services.logs import (
    processar_fluxo_anexo_log_create,
    processar_fluxo_log_create,
    processar_fluxo_log_update,
    validar_log_geologico,
)

from .common import obter_empresa_geologia_operacional


def _processar_post_form(
    *,
    request,
    resultado,
    mensagem_sucesso,
    mensagem_erro,
    redirect_name,
    redirect_kwargs,
):
    if request.method != "POST":
        return None
    if resultado.get("ok"):
        messages.success(request, mensagem_sucesso)
        return redirect(redirect_name, **redirect_kwargs)
    messages.error(request, mensagem_erro)
    return None


def _next_url_segura(request):
    next_url = request.POST.get("next") or request.GET.get("next")
    if not next_url:
        return ""
    if url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return ""


@login_required
@geologia_operacional_required
def log_geologico_create(request, furo_id):
    empresa, contexto_geologia, resposta_erro = obter_empresa_geologia_operacional(request)
    if resposta_erro:
        return resposta_erro

    furo = obter_furo_log_geologico(furo_id, empresa=empresa)

    fluxo = processar_fluxo_log_create(
        request_method=request.method,
        request_post=request.POST,
        request_files=request.FILES,
        furo=furo,
        empresa=empresa,
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        resposta_post = _processar_post_form(
            request=request,
            resultado=resultado,
            mensagem_sucesso=_("Log geológico registado com sucesso."),
            mensagem_erro=_("Não foi possível guardar o log geológico."),
            redirect_name="geologia:log_detail",
            redirect_kwargs={"pk": resultado["log"].pk} if resultado.get("ok") else {},
        )
        if resposta_post:
            return resposta_post

    return render(
        request,
        "geologia/log_form.html",
        {
            "form": form,
            "furo": furo,
            "titulo": _("Novo Log Geológico - %(nome)s") % {"nome": furo.nome},
        },
    )


@login_required
@geologia_operacional_required
def log_geologico_detail(request, pk):
    empresa, contexto_geologia, resposta_erro = obter_empresa_geologia_operacional(request)
    if resposta_erro:
        return resposta_erro

    log = obter_log_geologico(pk, empresa=empresa)
    anexos = obter_anexos_log(log)

    return render(
        request,
        "geologia/log_detail.html",
        {
            "log": log,
            "furo": log.furo,
            "anexos": anexos,
        },
    )


@login_required
@geologia_operacional_required
def log_geologico_update(request, pk):
    empresa, contexto_geologia, resposta_erro = obter_empresa_geologia_operacional(request)
    if resposta_erro:
        return resposta_erro

    log = obter_log_geologico(pk, empresa=empresa)

    fluxo = processar_fluxo_log_update(
        request_method=request.method,
        request_post=request.POST,
        request_files=request.FILES,
        log=log,
        empresa=empresa,
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        resposta_post = _processar_post_form(
            request=request,
            resultado=resultado,
            mensagem_sucesso=_("Log geológico atualizado com sucesso."),
            mensagem_erro=_("Não foi possível atualizar o log geológico."),
            redirect_name="geologia:log_detail",
            redirect_kwargs={"pk": log.pk},
        )
        if resposta_post:
            return resposta_post

    return render(
        request,
        "geologia/log_form.html",
        {
            "form": form,
            "furo": log.furo,
            "titulo": _("Editar Log Geológico - %(nome)s") % {"nome": log.furo.nome},
            "log": log,
        },
    )


@login_required
@geologia_operacional_required
def anexo_log_create(request, pk):
    empresa, contexto_geologia, resposta_erro = obter_empresa_geologia_operacional(request)
    if resposta_erro:
        return resposta_erro

    log = obter_log_geologico(pk, empresa=empresa)

    fluxo = processar_fluxo_anexo_log_create(
        request_method=request.method,
        request_post=request.POST,
        request_files=request.FILES,
        log=log,
    )
    form = fluxo["form"]
    resultado = fluxo["resultado"]
    if resultado:
        resposta_post = _processar_post_form(
            request=request,
            resultado=resultado,
            mensagem_sucesso=_("Anexo adicionado com sucesso."),
            mensagem_erro=_("Não foi possível adicionar o anexo."),
            redirect_name="geologia:log_detail",
            redirect_kwargs={"pk": log.pk},
        )
        if resposta_post:
            return resposta_post

    return render(
        request,
        "geologia/anexo_form.html",
        {
            "form": form,
            "log": log,
            "furo": log.furo,
            "titulo": _("Novo Anexo - %(titulo)s") % {"titulo": log.titulo},
        },
    )


@login_required
@geologia_operacional_required
def log_geologico_delete(request, pk):
    empresa, contexto_geologia, resposta_erro = obter_empresa_geologia_operacional(request)
    if resposta_erro:
        return resposta_erro

    log = obter_log_geologico(pk, empresa=empresa)
    furo_id = log.furo_id

    next_url = _next_url_segura(request)

    if request.method == "POST":
        log.delete()
        messages.success(request, _("Log geológico apagado com sucesso."))
        if next_url:
            return redirect(next_url)
        return redirect("geologia:furo_dashboard", furo_id=furo_id)

    messages.error(request, _("A eliminação de logs exige confirmação por formulário."))
    if next_url:
        return redirect(next_url)
    return redirect("geologia:log_detail", pk=pk)


@login_required
@geologia_operacional_required
def meus_logs_geologicos(request):
    empresa, contexto_geologia, resposta_erro = obter_empresa_geologia_operacional(request)
    if resposta_erro:
        return resposta_erro

    logs = obter_logs_geologia_hub_qs(empresa=empresa)
    return render(
        request,
        "geologia/meus_logs.html",
        {
            "logs": logs,
            "empresa_geologia": empresa,
        },
    )


@login_required
@geologo_required
def planeamento_amostragem_geologo(request):
    empresa, contexto_geologia, resposta_erro = obter_empresa_geologia_operacional(request)
    if resposta_erro:
        return resposta_erro

    intervalo_raw = (request.GET.get("intervalo") or "10").strip()
    try:
        intervalo_padrao = float(intervalo_raw.replace(",", "."))
    except (TypeError, ValueError):
        intervalo_padrao = 10.0

    if intervalo_padrao <= 0:
        intervalo_padrao = 10.0

    linhas = obter_planeamento_amostragem_geologo(
        empresa=empresa,
        intervalo_padrao=intervalo_padrao,
    )

    return render(
        request,
        "geologia/planeamento_amostragem.html",
        {
            "empresa_geologia": empresa,
            "linhas": linhas,
            "intervalo_padrao": intervalo_padrao,
        },
    )


@login_required
@geologo_required
def qualidade_dados_geologo(request):
    empresa, contexto_geologia, resposta_erro = obter_empresa_geologia_operacional(request)
    if resposta_erro:
        return resposta_erro

    linhas = obter_qualidade_dados_logs_geologo(empresa=empresa)
    return render(
        request,
        "geologia/qualidade_dados_logs.html",
        {
            "empresa_geologia": empresa,
            "linhas": linhas,
        },
    )


@login_required
@geologo_required
def correlacoes_geologia_perfuracao(request):
    empresa, contexto_geologia, resposta_erro = obter_empresa_geologia_operacional(request)
    if resposta_erro:
        return resposta_erro

    linhas = obter_correlacoes_geologia_perfuracao(empresa=empresa)
    return render(
        request,
        "geologia/correlacoes_geologia_perfuracao.html",
        {
            "empresa_geologia": empresa,
            "linhas": linhas,
        },
    )


@login_required
@geologo_required
def mapa_furos_2d_3d_geologo(request):
    empresa, contexto_geologia, resposta_erro = obter_empresa_geologia_operacional(request)
    if resposta_erro:
        return resposta_erro

    from .dashboard import _obter_fontes_cartograficas_contexto

    projeto_id = (request.GET.get("projeto") or "").strip()
    furos = obter_mapa_furos_geologo(empresa=empresa, projeto_id=projeto_id or None)
    projetos = obter_furos_geologia_hub_qs(empresa=empresa).values("projeto_id", "projeto__nome").distinct().order_by("projeto__nome")
    mapa_pontos = [
        {
            "furo_id": str(item["furo"].id),
            "furo_nome": item["furo"].nome,
            "projeto_nome": item["projeto"].nome,
            "estado": item["estado"],
            "profundidade_atual": item["profundidade_atual"],
            "lat": float(item["latitude"]),
            "lon": float(item["longitude"]),
            "url_3d": item["furo"].get_absolute_url().rstrip("/") + "/3d/",
            "url_geologia": f"/app/geologia/furos/{item['furo'].id}/",
            "url_detalhe": f"/app/furos/{item['furo'].id}/",
        }
        for item in furos
        if item.get("tem_coordenadas")
    ]
    fontes_cartograficas_mapa, _ = _obter_fontes_cartograficas_contexto(empresa=empresa)

    return render(
        request,
        "geologia/mapa_furos_2d_3d.html",
        {
            "empresa_geologia": empresa,
            "furos": furos,
            "projetos": projetos,
            "projeto_id_ativo": projeto_id,
            "mapa_pontos": mapa_pontos,
            "fontes_cartograficas_mapa": fontes_cartograficas_mapa,
        },
    )


@login_required
@geologo_required
def logs_pendentes_validacao(request):
    empresa, contexto_geologia, resposta_erro = obter_empresa_geologia_operacional(request)
    if resposta_erro:
        return resposta_erro

    if request.method == "POST":
        log_id = request.POST.get("log_id")
        acao = request.POST.get("acao")
        observacao = request.POST.get("observacao", "")
        if not log_id:
            messages.error(request, _("Log inválido para validação."))
            return redirect("geologia:logs_pendentes_validacao")

        log = obter_log_geologico(log_id, empresa=empresa)
        resultado = validar_log_geologico(log=log, user=request.user, acao=acao, observacao=observacao)
        if resultado.get("ok"):
            if acao == "aprovar":
                messages.success(request, _("Log aprovado com sucesso."))
            else:
                messages.success(request, _("Log rejeitado com sucesso."))
        else:
            messages.error(request, _("Não foi possível validar o log."))
        return redirect("geologia:logs_pendentes_validacao")

    logs = obter_logs_pendentes_validacao(empresa=empresa)
    return render(
        request,
        "geologia/logs_pendentes_validacao.html",
        {
            "logs": logs,
            "empresa_geologia": empresa,
        },
    )


@login_required
@geologo_required
def logs_intervalos_conflito(request):
    empresa, contexto_geologia, resposta_erro = obter_empresa_geologia_operacional(request)
    if resposta_erro:
        return resposta_erro
    conflitos = obter_conflitos_intervalos_logs(empresa=empresa)
    return render(
        request,
        "geologia/logs_intervalos_conflito.html",
        {
            "conflitos": conflitos,
            "empresa_geologia": empresa,
        },
    )


@login_required
@geologo_required
def resolver_intervalo_conflito(request):
    empresa, contexto_geologia, resposta_erro = obter_empresa_geologia_operacional(request)
    if resposta_erro:
        return resposta_erro

    furo_id = request.GET.get("furo")
    conflito_de_raw = request.GET.get("de")
    conflito_ate_raw = request.GET.get("ate")
    log_referencia_id = request.GET.get("log")

    if not (furo_id and conflito_de_raw and conflito_ate_raw):
        messages.error(request, _("Parâmetros do conflito em falta."))
        return redirect("geologia:logs_intervalos_conflito")

    try:
        conflito_de = float(str(conflito_de_raw).strip().replace(",", "."))
        conflito_ate = float(str(conflito_ate_raw).strip().replace(",", "."))
    except (TypeError, ValueError):
        messages.error(request, _("Intervalo de conflito inválido."))
        return redirect("geologia:logs_intervalos_conflito")

    if conflito_ate < conflito_de:
        conflito_de, conflito_ate = conflito_ate, conflito_de

    furo = obter_furo_log_geologico(furo_id, empresa=empresa)

    if request.method == "POST":
        log_id = request.POST.get("log_id")
        if not log_id:
            messages.error(request, _("Log inválido para seleção."))
            return redirect(
                f"{request.path}?furo={furo.id}&de={conflito_de}&ate={conflito_ate}"
            )

        log_escolhido = obter_log_geologico(log_id, empresa=empresa)
        logs_conflito = list(
            obter_logs_envolvidos_conflito(
                furo=furo,
                conflito_de=conflito_de,
                conflito_ate=conflito_ate,
                empresa=empresa,
            )
        )

        # Mantém apenas o log escolhido e remove os restantes logs envolvidos no mesmo conflito.
        logs_para_apagar = [item for item in logs_conflito if item.id != log_escolhido.id]
        total_apagados = len(logs_para_apagar)
        for item in logs_para_apagar:
            item.delete()

        log_escolhido.status_validacao = "aprovado"
        log_escolhido.validado_por = request.user
        log_escolhido.validado_em = timezone.now()
        if not log_escolhido.observacao_validacao:
            log_escolhido.observacao_validacao = _("Selecionado na resolução de conflito de intervalos.")
        log_escolhido.save(
            update_fields=[
                "status_validacao",
                "validado_por",
                "validado_em",
                "observacao_validacao",
                "atualizado_em",
            ]
        )

        messages.success(
            request,
            _("Log selecionado com sucesso. %(total)s log(s) em conflito foram apagados.") % {"total": total_apagados},
        )
        return redirect(
            f"{request.path}?furo={furo.id}&de={conflito_de}&ate={conflito_ate}&log={log_escolhido.id}"
        )

    logs = list(
        obter_logs_envolvidos_conflito(
            furo=furo,
            conflito_de=conflito_de,
            conflito_ate=conflito_ate,
            empresa=empresa,
        )
    )

    return render(
        request,
        "geologia/resolver_intervalo_conflito.html",
        {
            "empresa_geologia": empresa,
            "furo": furo,
            "logs": logs,
            "conflito_de": conflito_de,
            "conflito_ate": conflito_ate,
            "log_referencia_id": log_referencia_id,
        },
    )


@login_required
@geologo_required
def mapa_litologico_furo(request):
    empresa, contexto_geologia, resposta_erro = obter_empresa_geologia_operacional(request)
    if resposta_erro:
        return resposta_erro

    furos = list(obter_furos_geologia_hub_qs(empresa=empresa))
    furo_id = request.GET.get("furo")
    furo_ativo = None
    if furo_id:
        for item in furos:
            if str(item.id) == str(furo_id):
                furo_ativo = item
                break
    if furo_ativo is None and furos:
        furo_ativo = furos[0]

    mapa = obter_mapa_litologico_furo(furo=furo_ativo, empresa=empresa) if furo_ativo else None

    return render(
        request,
        "geologia/mapa_litologico_furo.html",
        {
            "empresa_geologia": empresa,
            "furos": furos,
            "furo_ativo": furo_ativo,
            "mapa": mapa,
        },
    )


@login_required
@geologo_required
def alertas_geotecnicos(request):
    empresa, contexto_geologia, resposta_erro = obter_empresa_geologia_operacional(request)
    if resposta_erro:
        return resposta_erro
    alertas = obter_alertas_geotecnicos(empresa=empresa)
    return render(
        request,
        "geologia/alertas_geotecnicos.html",
        {
            "empresa_geologia": empresa,
            "alertas": alertas,
        },
    )


@login_required
@geologo_required
def relatorio_geologico(request):
    empresa, contexto_geologia, resposta_erro = obter_empresa_geologia_operacional(request)
    if resposta_erro:
        return resposta_erro
    furos = list(obter_furos_geologia_hub_qs(empresa=empresa))
    furo_id = request.GET.get("furo")
    furo_ativo = None
    if furo_id:
        for item in furos:
            if str(item.id) == str(furo_id):
                furo_ativo = item
                break
    linhas = normalizar_linhas_exportacao(construir_linhas_relatorio_geologico(empresa=empresa, furo=furo_ativo))
    resumo = construir_resumo_executivo_geologico(linhas)
    return render(
        request,
        "geologia/relatorio_geologico.html",
        {
            "empresa_geologia": empresa,
            "furos": furos,
            "furo_ativo": furo_ativo,
            "linhas": linhas[:20],
            "total_linhas": len(linhas),
            "resumo": resumo,
            "gerado_em": timezone.localtime(),
        },
    )


@login_required
@geologo_required
def relatorio_geologico_export(request, formato):
    empresa, contexto_geologia, resposta_erro = obter_empresa_geologia_operacional(request)
    if resposta_erro:
        return resposta_erro
    if formato not in {"csv", "xlsx", "pdf"}:
        raise Http404("Formato inválido.")

    furo_id = request.GET.get("furo")
    furo_ativo = None
    if furo_id:
        furos = list(obter_furos_geologia_hub_qs(empresa=empresa))
        for item in furos:
            if str(item.id) == str(furo_id):
                furo_ativo = item
                break

    linhas = normalizar_linhas_exportacao(construir_linhas_relatorio_geologico(empresa=empresa, furo=furo_ativo))
    dataset_info = {
        "icone": "🪨",
        "titulo": _("Relatório Geológico"),
    }
    nome_base = "relatorio-geologico"
    if furo_ativo:
        nome_base += f"-{furo_ativo.nome}".replace(" ", "-").lower()

    if formato == "csv":
        conteudo = renderizar_csv_exportacao(linhas)
        response = HttpResponse(conteudo, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{nome_base}.csv"'
        return response

    if formato == "xlsx":
        conteudo = renderizar_xlsx_exportacao(dataset_info, linhas)
        response = HttpResponse(
            conteudo,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{nome_base}.xlsx"'
        return response

    conteudo = renderizar_pdf_exportacao(dataset_info, empresa, linhas)
    response = HttpResponse(conteudo, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{nome_base}.pdf"'
    return response


@login_required
@geologo_required
def relatorio_geologico_executivo_print(request):
    empresa, contexto_geologia, resposta_erro = obter_empresa_geologia_operacional(request)
    if resposta_erro:
        return resposta_erro

    furo_id = request.GET.get("furo")
    furo_ativo = None
    if furo_id:
        furos = list(obter_furos_geologia_hub_qs(empresa=empresa))
        for item in furos:
            if str(item.id) == str(furo_id):
                furo_ativo = item
                break

    linhas = normalizar_linhas_exportacao(construir_linhas_relatorio_geologico(empresa=empresa, furo=furo_ativo))
    resumo = construir_resumo_executivo_geologico(linhas)
    return render(
        request,
        "geologia/relatorio_geologico_print.html",
        {
            "empresa_geologia": empresa,
            "furo_ativo": furo_ativo,
            "linhas": linhas,
            "resumo": resumo,
            "gerado_em": timezone.localtime(),
        },
    )
