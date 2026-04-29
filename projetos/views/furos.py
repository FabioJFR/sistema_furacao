import logging
import io
import json
import zipfile

from django.contrib import messages
from django.http import Http404, HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from core.permissions import user_is_empresa_admin
from core.permissions import user_is_global_admin
from ..decorators import admin_required, empregado_required
from projetos.selectors.furos import (
    empregado_trabalhou_no_furo,
    obter_furo,
    obter_lista_furos,
    obter_medicoes_furo_para_empregado,
    obter_registos_furo_para_empregado,
)
from projetos.services.furo_3d_io import (
    dados_completos_furo as dados_completos_furo_service,
    dados_exportacao_furo_3d as dados_exportacao_furo_3d_service,
    parse_imported_3d_file as parse_imported_3d_file_service,
    renderizar_furo_3d_csv as renderizar_furo_3d_csv_service,
    renderizar_furo_3d_geojson as renderizar_furo_3d_geojson_service,
)
from projetos.services.furo_3d_chart import construir_contexto_furo_3d
from projetos.services.furo_fluxos import (
    construir_contexto_furo_detail,
    processar_delete_furo,
    processar_importacao_3d_externa,
    resolver_furo_para_3d,
    listar_furos_para_utilizador,
    preparar_form_furo_create,
    preparar_form_furo_update,
    processar_submissao_furo_create,
    processar_submissao_furo_update,
)
from projetos.services.acesso_contexto import obter_empresa_admin_contexto
from projetos.services.acesso_contexto import obter_empregado_autenticado_contexto
from projetos.services.acesso_contexto import obter_empresa_contexto_gestao_furos
from projetos.services.furos import terminar_furo, reativar_furo

logger = logging.getLogger("core")


def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


def _dados_exportacao_furo_3d(furo):
    return dados_exportacao_furo_3d_service(furo)


def _renderizar_furo_3d_csv(payload):
    return renderizar_furo_3d_csv_service(payload)


def _renderizar_furo_3d_geojson(payload):
    return renderizar_furo_3d_geojson_service(payload)


def _dados_completos_furo(furo):
    return dados_completos_furo_service(furo)


def _parse_imported_3d_file(uploaded_file):
    return parse_imported_3d_file_service(uploaded_file)


def _obter_empresa_admin_furos(request):
    empresa, resposta_erro = obter_empresa_admin_contexto(
        request=request,
        mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
        mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa.",
        redirect_sem_permissao="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:dashboard",
    )
    if resposta_erro:
        logger.warning(
            "Falha ao resolver empresa administrativa em furos.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro
    return empresa, None



def _obter_empregado_autenticado_furos(request):
    logger.debug(
        "A resolver empregado autenticado em furos.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    empregado, _ligado_por_fallback, resposta_erro = obter_empregado_autenticado_contexto(
        request=request,
        mensagem_sem_empregado="A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        mensagem_sem_empresa="A tua conta não está associada a uma empresa. Contacta o administrador.",
        redirect_sem_empregado="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:redirect_after_login",
        vincular_por_email=True,
    )
    if resposta_erro:
        logger.warning(
            "Utilizador autenticado sem registo em Empregados em furos.py. user_id=%s",
            request.user.id,
        )
        return None, resposta_erro

    return empregado, None


def _obter_empresa_contexto_gestao_furos(request):
    return obter_empresa_contexto_gestao_furos(request=request)



# ---------------- FUROS ----------------
@login_required
@empregado_required
def furo_detail_empregado(request, pk):
    logger.info(
        "Entrada na view furo_detail_empregado. user_id=%s, username='%s', furo_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_furos(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_detail_empregado. user_id=%s", request.user.id)
        return resposta_erro

    furo = obter_furo(pk, empresa=empregado.empresa_id)
    trabalhou_no_furo = empregado_trabalhou_no_furo(empregado, furo)
    if not trabalhou_no_furo:
        logger.warning(
            "Empregado sem permissão para furo_detail_empregado em furos.py. user_id=%s, empregado_id=%s, furo_id=%s",
            request.user.id,
            empregado.id,
            furo.id,
        )
        messages.error(request, "Não tens permissão para ver os detalhes deste furo.")
        return redirect("projetos:area_empregado")

    registos_furo = obter_registos_furo_para_empregado(empregado, furo)
    medicoes_furo = obter_medicoes_furo_para_empregado(empregado, furo)
    registos_lista = list(registos_furo)
    datas_registo = [
        registo.data or (registo.criado_em.date() if registo.criado_em else None)
        for registo in registos_lista
    ]
    datas_registo = [d for d in datas_registo if d is not None]
    data_inicio_real = min(datas_registo) if datas_registo else (furo.data_inicio_operacao or None)
    dias_com_registo = len(set(datas_registo))
    total_metros_registos = round(sum(float(r.metros_furados or 0) for r in registos_lista), 2)
    media_metros_por_dia = round(total_metros_registos / dias_com_registo, 2) if dias_com_registo else 0.0

    logger.info(
        "View furo_detail_empregado carregada com sucesso em furos.py. user_id=%s, empregado_id=%s, furo_id=%s",
        request.user.id,
        empregado.id,
        furo.id,
    )
    return render(request, "projetos/furo_detail_empregado.html", {
        "empregado": empregado,
        "furo": furo,
        "registos_furo": registos_furo,
        "medicoes_furo": medicoes_furo,
        "data_inicio_real_furo": data_inicio_real,
        "dias_com_registo_furo": dias_com_registo,
        "total_metros_registos": total_metros_registos,
        "media_metros_por_dia_furo": media_metros_por_dia,
    })



@login_required
def furo_create(request):
    logger.info(
        "Entrada na view furo_create. user_id=%s, username='%s', method=%s",
        request.user.id,
        request.user.username,
        request.method,
    )
    empresa, _acesso_individual, resposta_erro = _obter_empresa_contexto_gestao_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_create. user_id=%s", request.user.id)
        return resposta_erro

    empregado_contexto = None
    if not user_is_empresa_admin(request.user):
        empregado_contexto, resposta_empregado = _obter_empregado_autenticado_furos(request)
        if resposta_empregado:
            logger.warning("Acesso bloqueado por contexto de empregado na view furo_create. user_id=%s", request.user.id)
            return resposta_empregado

    memoria_zona_alerta = []
    if request.method == "POST":
        resultado = processar_submissao_furo_create(
            request_post=request.POST,
            empresa_id=empresa_id,
            empregado_contexto=empregado_contexto,
        )
        form = resultado["form"]
        memoria_zona_alerta = resultado["memoria_zona_alerta"]
        if resultado["ok"]:
            furo = resultado["furo"]
            logger.info(
                "Furo criado com sucesso. user_id=%s, empresa_id=%s, furo_id=%s",
                request.user.id,
                empresa.id,
                furo.pk,
            )
            messages.success(request, "Furo criado com sucesso.")
            return redirect(furo)

        logger.warning(
            "Erro ao criar furo. user_id=%s, erros=%s",
            request.user.id,
            form.errors,
        )
        messages.error(request, "Erro ao criar o furo. Verifique os dados.")
    else:
        form = preparar_form_furo_create(
            empresa_id=empresa_id,
            empregado_contexto=empregado_contexto,
        )

    return render(request, "projetos/form.html", {
        "form": form,
        "titulo": "Criar Novo Furo",
        "memoria_zona_alerta": memoria_zona_alerta,
    })


@login_required
def furo_detail_legacy(request, pk):
    empresa, _acesso_individual, resposta_erro = _obter_empresa_contexto_gestao_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        return resposta_erro

    furo = obter_furo(pk, empresa=empresa_id)
    return redirect(furo)


@login_required
def furo_detail(request, pk, slug):
    logger.info(
        "Entrada na view furo_detail. user_id=%s, username='%s', furo_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empresa, _acesso_individual, resposta_erro = _obter_empresa_contexto_gestao_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_detail. user_id=%s", request.user.id)
        return resposta_erro

    context = construir_contexto_furo_detail(pk=pk, empresa_id=empresa_id)
    furo = context["furo"]
    if slug != furo.slug_url:
        return redirect(furo)

    logger.info(
        "View furo_detail carregada com sucesso. user_id=%s, empresa_id=%s, furo_id=%s",
        request.user.id,
        empresa.id,
        furo.pk,
    )
    return render(request, "projetos/furo_detail.html", context)


@login_required
def furo_terminar(request, pk):
    if request.method != "POST":
        return redirect("projetos:furo_detail_legacy", pk=pk)

    empresa, _acesso_individual, resposta_erro = _obter_empresa_contexto_gestao_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        return resposta_erro

    furo = obter_furo(pk, empresa=empresa_id)
    terminar_furo(furo=furo, empresa=empresa_id, terminado_por=request.user)
    messages.success(request, "Furo terminado com sucesso.")
    return redirect(furo)


@login_required
def furo_reativar(request, pk):
    if request.method != "POST":
        return redirect("projetos:furo_detail_legacy", pk=pk)

    empresa, _acesso_individual, resposta_erro = _obter_empresa_contexto_gestao_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        return resposta_erro

    furo = obter_furo(pk, empresa=empresa_id)
    reativar_furo(furo=furo, empresa=empresa_id)
    messages.success(request, "Furo reativado com sucesso.")
    return redirect(furo)

# Multiempresa: o administrador só pode listar e gerir furos da sua própria empresa.
@login_required
def furo_list(request):
    logger.info(
        "Entrada na view furo_list. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empresa, _acesso_individual, resposta_erro = _obter_empresa_contexto_gestao_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_list. user_id=%s", request.user.id)
        return resposta_erro

    is_admin = user_is_empresa_admin(request.user)
    if not is_admin:
        empregado_contexto, resposta_empregado = _obter_empregado_autenticado_furos(request)
        if resposta_empregado:
            logger.warning("Acesso bloqueado por contexto de empregado na view furo_list. user_id=%s", request.user.id)
            return resposta_empregado

    furos = listar_furos_para_utilizador(
        empresa_id=empresa_id,
        empregado_contexto=empregado_contexto if not is_admin else None,
        is_admin=is_admin,
    )
    logger.info(
        "View furo_list carregada com sucesso. user_id=%s, empresa_id=%s, total_furos=%s",
        request.user.id,
        empresa.id,
        furos.count() if hasattr(furos, "count") else "n/a",
    )
    return render(request, "projetos/furo_list.html", {"furos": furos})




@login_required
def furo_update(request, pk):
    logger.info(
        "Entrada na view furo_update. user_id=%s, username='%s', furo_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, _acesso_individual, resposta_erro = _obter_empresa_contexto_gestao_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_update. user_id=%s", request.user.id)
        return resposta_erro

    if request.method == "POST":
        resultado = processar_submissao_furo_update(
            request_post=request.POST,
            pk=pk,
            empresa_id=empresa_id,
        )
        form = resultado["form"]
        furo = resultado["furo"]
        if resultado["ok"]:

            logger.info(
                "Furo atualizado com sucesso. user_id=%s, empresa_id=%s, furo_id=%s",
                request.user.id,
                empresa.id,
                furo.pk,
            )
            messages.success(request, "Furo atualizado com sucesso.")
            return redirect(furo)

        logger.warning(
            "Erro ao atualizar furo. user_id=%s, furo_pk=%s, erros=%s",
            request.user.id,
            pk,
            form.errors,
        )
        messages.error(request, "Erro ao atualizar o furo. Verifique os dados.")
    else:
        furo = obter_furo(pk, empresa=empresa_id)
        form = preparar_form_furo_update(
            furo=furo,
            empresa_id=empresa_id,
        )

    return render(request, "projetos/furo_update.html", {
        "form": form,
        "furo": furo,
    })



@login_required
def furo_delete(request, pk):
    logger.info(
        "Entrada na view furo_delete. user_id=%s, username='%s', furo_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, _acesso_individual, resposta_erro = _obter_empresa_contexto_gestao_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_delete. user_id=%s", request.user.id)
        return resposta_erro

    furo = obter_furo(pk, empresa=empresa_id)
    if request.method == "POST":
        resultado = processar_delete_furo(pk=pk, empresa_id=empresa_id)
        furo_id = resultado["furo_id"]
        logger.info(
            "Furo apagado com sucesso. user_id=%s, empresa_id=%s, furo_id=%s",
            request.user.id,
            empresa.id,
            furo_id,
        )
        messages.success(request, "Furo apagado com sucesso.")
        return redirect(reverse("projetos:furo_list"))

    return render(request, "projetos/furo_confirm_delete.html", {"furo": furo})



@login_required
def furo_3d_geologico(request, furo_id=None, pk=None, slug=None):
    furo_id = furo_id or pk
    logger.info(
        "Entrada na view furo_3d_geologico. user_id=%s, username='%s', furo_id=%s",
        request.user.id,
        request.user.username,
        furo_id,
    )
    acesso = resolver_furo_para_3d(
        request=request,
        furo_id=furo_id,
        user_is_global_admin_fn=user_is_global_admin,
        user_is_empresa_admin_fn=user_is_empresa_admin,
        obter_empresa_contexto_fn=_obter_empresa_contexto_gestao_furos,
        resolver_empresa_id_fn=_resolver_empresa_id,
        obter_empregado_contexto_fn=_obter_empregado_autenticado_furos,
    )
    if acesso["erro"]:
        logger.warning("Acesso bloqueado na view furo_3d_geologico. user_id=%s", request.user.id)
        return acesso["erro"]
    if acesso["sem_permissao"]:
        logger.warning("Empregado sem permissão para furo_3d_geologico. user_id=%s, furo_id=%s", request.user.id, furo_id)
        messages.error(request, "Não tens permissão para ver o 3D deste furo.")
        return redirect("projetos:area_empregado")
    furo = acesso["furo"]

    contexto_3d = construir_contexto_furo_3d(furo)
    if contexto_3d.get("sem_medicoes"):
        logger.info(
            "Furo sem medições em furo_3d_geologico. user_id=%s, furo_id=%s",
            request.user.id,
            furo.id,
        )
        messages.warning(request, "Este furo ainda não possui medições.")

    logger.info(
        "View furo_3d_geologico carregada com sucesso. user_id=%s, furo_id=%s, numero_medicoes=%s, estado_max=%s",
        request.user.id,
        furo.id,
        contexto_3d.get("numero_medicoes", 0),
        contexto_3d.get("estado_max", "OK"),
    )
    contexto_3d.pop("sem_medicoes", None)
    return render(request, "projetos/furo_3d.html", {"furo": furo, **contexto_3d})


@login_required
@admin_required
def furo_3d_importar_externo(request):
    empresa, resposta_erro = _obter_empresa_admin_furos(request)
    if resposta_erro:
        return resposta_erro

    resultado_importacao = {
        "imported_trace": None,
        "trace_name": "",
        "total_pontos": 0,
        "origem_aplicacao": "",
        "furo_destino_id": "",
        "observacoes": "",
        "mensagem_sucesso": None,
        "mensagem_erro": None,
    }
    if request.method == "POST":
        resultado_importacao = processar_importacao_3d_externa(
            request_post=request.POST,
            request_files=request.FILES,
            empresa=empresa,
            parse_imported_file_fn=_parse_imported_3d_file,
        )
        if resultado_importacao["mensagem_sucesso"]:
            messages.success(request, resultado_importacao["mensagem_sucesso"])
        if resultado_importacao["mensagem_erro"]:
            messages.error(request, resultado_importacao["mensagem_erro"])

    return render(
        request,
        "projetos/furo_3d_importar_externo.html",
        {
            "empresa": empresa,
            "imported_trace": resultado_importacao["imported_trace"],
            "trace_name": resultado_importacao["trace_name"],
            "total_pontos": resultado_importacao["total_pontos"],
            "furos_empresa": obter_lista_furos(empresa=empresa),
            "origem_aplicacao": resultado_importacao["origem_aplicacao"],
            "furo_destino_id": resultado_importacao["furo_destino_id"],
            "observacoes": resultado_importacao["observacoes"],
        },
    )


@login_required
def furo_3d_export(request, furo_id, formato):
    empresa, _acesso_individual, resposta_erro = _obter_empresa_contexto_gestao_furos(request)
    empresa_id = _resolver_empresa_id(empresa) if empresa is not None else None
    if resposta_erro:
        return resposta_erro

    furo = obter_furo(furo_id, empresa=empresa_id)
    payload = _dados_exportacao_furo_3d(furo)
    nome_base = f"furo-{furo.pk}-3d"

    if formato == "json":
        response = HttpResponse(
            json.dumps(payload, ensure_ascii=False, indent=2),
            content_type="application/json; charset=utf-8",
        )
        response["Content-Disposition"] = f'attachment; filename="{nome_base}.json"'
        return response

    if formato == "csv":
        response = HttpResponse(_renderizar_furo_3d_csv(payload), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{nome_base}.csv"'
        return response

    if formato == "geojson":
        response = HttpResponse(_renderizar_furo_3d_geojson(payload), content_type="application/geo+json; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{nome_base}.geojson"'
        return response

    if formato == "zip":
        dados = _dados_completos_furo(furo)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(f"{nome_base}-completo.json", json.dumps(dados, ensure_ascii=False, indent=2))
            zip_file.writestr(f"{nome_base}-3d.json", json.dumps(payload, ensure_ascii=False, indent=2))
            zip_file.writestr(f"{nome_base}-3d.csv", _renderizar_furo_3d_csv(payload))
            zip_file.writestr(f"{nome_base}-3d.geojson", _renderizar_furo_3d_geojson(payload))
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{nome_base}-completo.zip"'
        return response

    raise Http404("Formato 3D não suportado.")
