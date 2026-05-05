from projetos.forms.furo import FuroCreateForm, FuroForm
from projetos.selectors.acesso import obter_perfil_ativo_por_user
from projetos.selectors.forms import listar_furos_empregado_qs, listar_projetos_empregado_qs
from projetos.selectors.furos import (
    empregado_trabalhou_no_furo,
    obter_contexto_detalhe_furo,
    obter_equipa_e_configuracao_por_furo,
    obter_furo,
    obter_furo_opcional,
    obter_lista_furos,
    obter_medicoes_furo_para_empregado,
    obter_registos_furo_para_empregado,
)
from projetos.services.furo_memoria import obter_memoria_zona_furos, parse_float_or_none
from projetos.services.furo_3d_io import guardar_importacao_externa_3d
from projetos.services.furos import apagar_furo, atualizar_furo, criar_furo
from geologia.selectors.logs import obter_logs_geologicos_recentes_furo
from geologia.selectors.drone import obter_missoes_drone_recentes_furo
from core.permissions import user_is_geologo, user_is_encarregado_obra


def preparar_form_furo_create(*, request_post=None, empresa_id=None, empregado_contexto=None):
    if request_post is not None:
        form = FuroCreateForm(request_post, empresa=empresa_id)
    else:
        form = FuroCreateForm(empresa=empresa_id)

    if empregado_contexto is not None:
        form.fields["projeto"].queryset = listar_projetos_empregado_qs(
            empregado_contexto,
            empresa=empresa_id,
        )
    return form


def obter_memoria_alerta_create(*, request_post, empresa_id):
    return obter_memoria_zona_furos(
        empresa_id=empresa_id,
        latitude=parse_float_or_none(request_post.get("latitude")),
        longitude=parse_float_or_none(request_post.get("longitude")),
        localizacao=request_post.get("localizacao") or request_post.get("local_sondagem"),
    )


def processar_submissao_furo_create(*, request_post, empresa_id=None, empregado_contexto=None):
    form = preparar_form_furo_create(
        request_post=request_post,
        empresa_id=empresa_id,
        empregado_contexto=empregado_contexto,
    )
    memoria_zona_alerta = obter_memoria_alerta_create(request_post=request_post, empresa_id=empresa_id)
    if form.is_valid():
        furo = criar_furo(form, empresa=empresa_id)
        return {
            "ok": True,
            "furo": furo,
            "form": form,
            "memoria_zona_alerta": memoria_zona_alerta,
        }
    return {
        "ok": False,
        "furo": None,
        "form": form,
        "memoria_zona_alerta": memoria_zona_alerta,
    }


def processar_fluxo_furo_create(*, request_post, empresa_id=None, empregado_contexto=None):
    resultado = processar_submissao_furo_create(
        request_post=request_post,
        empresa_id=empresa_id,
        empregado_contexto=empregado_contexto,
    )
    if resultado["ok"]:
        return {
            **resultado,
            "mensagem_sucesso": "Furo criado com sucesso.",
            "mensagem_erro": None,
            "erros_form": None,
        }
    return {
        **resultado,
        "mensagem_sucesso": None,
        "mensagem_erro": "Erro ao criar o furo. Verifique os dados.",
        "erros_form": resultado["form"].errors,
    }


def processar_fluxo_form_furo_create(
    *,
    request_method,
    request_post,
    empresa_id=None,
    empregado_contexto=None,
):
    if request_method == "POST":
        resultado = processar_fluxo_furo_create(
            request_post=request_post,
            empresa_id=empresa_id,
            empregado_contexto=empregado_contexto,
        )
        return {
            "form": resultado["form"],
            "resultado": resultado,
            "memoria_zona_alerta": resultado["memoria_zona_alerta"],
        }

    form = preparar_form_furo_create(
        empresa_id=empresa_id,
        empregado_contexto=empregado_contexto,
    )
    return {
        "form": form,
        "resultado": None,
        "memoria_zona_alerta": [],
    }


def listar_furos_para_utilizador(*, empresa_id=None, empregado_contexto=None, is_admin=False):
    if is_admin:
        return obter_lista_furos(empresa=empresa_id)
    return listar_furos_empregado_qs(empregado_contexto, empresa=empresa_id)


def preparar_form_furo_update(*, request_post=None, furo, empresa_id=None):
    if request_post is not None:
        return FuroForm(request_post, instance=furo, empresa=empresa_id)
    return FuroForm(instance=furo, empresa=empresa_id)


def processar_submissao_furo_update(*, request_post, pk, empresa_id=None):
    furo = obter_furo(pk, empresa=empresa_id)
    form = preparar_form_furo_update(request_post=request_post, furo=furo, empresa_id=empresa_id)
    if form.is_valid():
        furo = atualizar_furo(form, empresa=empresa_id)
        return {"ok": True, "furo": furo, "form": form}
    return {"ok": False, "furo": furo, "form": form}


def processar_fluxo_furo_update(*, request_post, pk, empresa_id=None):
    resultado = processar_submissao_furo_update(
        request_post=request_post,
        pk=pk,
        empresa_id=empresa_id,
    )
    if resultado["ok"]:
        return {
            **resultado,
            "mensagem_sucesso": "Furo atualizado com sucesso.",
            "mensagem_erro": None,
            "erros_form": None,
        }
    return {
        **resultado,
        "mensagem_sucesso": None,
        "mensagem_erro": "Erro ao atualizar o furo. Verifique os dados.",
        "erros_form": resultado["form"].errors,
    }


def processar_fluxo_form_furo_update(
    *,
    request_method,
    request_post,
    pk,
    empresa_id=None,
):
    if request_method == "POST":
        resultado = processar_fluxo_furo_update(
            request_post=request_post,
            pk=pk,
            empresa_id=empresa_id,
        )
        return {
            "form": resultado["form"],
            "furo": resultado["furo"],
            "resultado": resultado,
        }

    furo = obter_furo(pk, empresa=empresa_id)
    form = preparar_form_furo_update(
        furo=furo,
        empresa_id=empresa_id,
    )
    return {
        "form": form,
        "furo": furo,
        "resultado": None,
    }


def construir_contexto_furo_detail(*, pk, empresa_id=None):
    context = obter_contexto_detalhe_furo(pk, empresa=empresa_id)
    furo = context["furo"]
    context["configuracoes"] = obter_equipa_e_configuracao_por_furo(furo, empresa=empresa_id)
    context["logs_geologicos_recentes"] = obter_logs_geologicos_recentes_furo(
        furo,
        empresa=empresa_id,
        limit=5,
    )
    context["missoes_drone_recentes"] = obter_missoes_drone_recentes_furo(
        furo,
        empresa=empresa_id,
        limit=3,
    )
    context["memoria_zona_alerta"] = obter_memoria_zona_furos(
        empresa_id=empresa_id,
        latitude=furo.latitude,
        longitude=furo.longitude,
        localizacao=furo.localizacao or furo.local_sondagem,
        excluir_furo_id=furo.pk,
    )
    context["page_title"] = f"Furo · {furo.nome}"
    return context


def construir_contexto_furo_detail_empregado(*, empregado, furo):
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

    return {
        "registos_furo": registos_furo,
        "medicoes_furo": medicoes_furo,
        "data_inicio_real_furo": data_inicio_real,
        "dias_com_registo_furo": dias_com_registo,
        "total_metros_registos": total_metros_registos,
        "media_metros_por_dia_furo": media_metros_por_dia,
    }


def resolver_furo_para_3d(
    *,
    request,
    furo_id,
    user_is_global_admin_fn,
    user_is_empresa_admin_fn,
    obter_empresa_contexto_fn,
    resolver_empresa_id_fn,
    obter_empregado_contexto_fn,
):
    perfil = obter_perfil_ativo_por_user(request.user)
    acesso_individual = bool(perfil and perfil.tipo_acesso == "individual")

    if user_is_global_admin_fn(request.user):
        return {"furo": obter_furo(furo_id, empresa=None), "erro": None, "sem_permissao": False}

    if user_is_empresa_admin_fn(request.user) or acesso_individual:
        empresa, _acesso_individual_resolvido, resposta_erro = obter_empresa_contexto_fn(request)
        if resposta_erro:
            return {"furo": None, "erro": resposta_erro, "sem_permissao": False}
        empresa_id = resolver_empresa_id_fn(empresa)
        return {"furo": obter_furo(furo_id, empresa=empresa_id), "erro": None, "sem_permissao": False}

    empregado, resposta_erro = obter_empregado_contexto_fn(request)
    if resposta_erro:
        return {"furo": None, "erro": resposta_erro, "sem_permissao": False}

    furo = obter_furo(furo_id, empresa=empregado.empresa_id)
    # Geólogo e encarregado podem consultar o 3D de qualquer furo da empresa.
    if user_is_geologo(request.user) or user_is_encarregado_obra(request.user):
        return {"furo": furo, "erro": None, "sem_permissao": False}

    trabalhou_no_furo = empregado_trabalhou_no_furo(empregado, furo)
    tem_furo_nos_projetos = listar_furos_empregado_qs(
        empregado,
        empresa=empregado.empresa_id,
    ).filter(pk=furo.pk).exists()
    if not (trabalhou_no_furo or tem_furo_nos_projetos):
        return {"furo": None, "erro": None, "sem_permissao": True}
    return {"furo": furo, "erro": None, "sem_permissao": False}


def processar_delete_furo(*, pk, empresa_id=None):
    furo = obter_furo(pk, empresa=empresa_id)
    furo_id = apagar_furo(furo=furo, empresa=empresa_id)
    return {"furo_id": furo_id}


def processar_importacao_3d_externa(
    *,
    request_post,
    request_files,
    empresa,
    parse_imported_file_fn,
):
    imported_trace = None
    trace_name = ""
    total_pontos = 0
    origem_aplicacao = ""
    furo_destino_id = ""
    observacoes = ""
    sucesso = None
    erro = None

    uploaded = request_files.get("ficheiro_3d")
    if uploaded:
        try:
            imported_trace = parse_imported_file_fn(uploaded)
            trace_name = imported_trace.get("name") or uploaded.name
            total_pontos = len(imported_trace.get("x") or [])
            origem_aplicacao = (request_post.get("origem_aplicacao") or "").strip()
            furo_destino_id = (request_post.get("furo_destino") or "").strip()
            observacoes = (request_post.get("observacoes") or "").strip()

            if "guardar_importacao" in request_post:
                furo_destino = obter_furo_opcional(empresa, furo_destino_id) if furo_destino_id else None
                guardar_importacao_externa_3d(
                    empresa=empresa,
                    uploaded_filename=uploaded.name or "",
                    imported_trace=imported_trace,
                    trace_name=trace_name,
                    origem_aplicacao=origem_aplicacao,
                    furo_destino=furo_destino,
                    observacoes=observacoes,
                )
                sucesso = "Importação 3D guardada na base de dados com origem externa."
            else:
                sucesso = "Trajetória externa carregada com sucesso."
        except ValueError as exc:
            erro = str(exc)

    return {
        "imported_trace": imported_trace,
        "trace_name": trace_name,
        "total_pontos": total_pontos,
        "origem_aplicacao": origem_aplicacao,
        "furo_destino_id": furo_destino_id,
        "observacoes": observacoes,
        "mensagem_sucesso": sucesso,
        "mensagem_erro": erro,
    }
