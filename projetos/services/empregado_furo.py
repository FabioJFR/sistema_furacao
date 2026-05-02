from projetos.models import EmpregadoFuro
from projetos.services.empregados import garantir_ligacao_projeto_por_furo


def criar_ligacao_empregado_furo(
    *,
    empregado,
    furo,
    empresa,
    funcao,
    data_inicio=None,
    data_fim=None,
    ativo=True,
    observacoes="",
):
    return EmpregadoFuro.objects.create(
        empregado=empregado,
        furo=furo,
        funcao=funcao,
        data_inicio=data_inicio,
        data_fim=data_fim,
        ativo=ativo,
        observacoes=observacoes,
        empresa=empresa,
    )


def atualizar_ligacao_empregado_furo(
    *,
    ligacao,
    empregado,
    empresa,
    funcao,
    data_inicio=None,
    data_fim=None,
    ativo=True,
    observacoes="",
):
    ligacao.empregado = empregado
    ligacao.funcao = funcao
    ligacao.data_inicio = data_inicio
    ligacao.data_fim = data_fim
    ligacao.ativo = ativo
    ligacao.observacoes = observacoes
    ligacao.empresa = empresa
    ligacao.save()
    return ligacao


def preparar_form_empregado_furo(
    *,
    method,
    post_data,
    form_class,
    empresa,
    furo,
    instance=None,
):
    form = form_class(
        post_data if method == "POST" else None,
        instance=instance,
        empresa=empresa,
        furo=furo,
    )
    form.instance.furo = furo
    form.instance.empresa = empresa
    empregado_id = post_data.get("empregado") if method == "POST" else None
    if empregado_id:
        form.instance.empregado_id = empregado_id
    return form


def processar_submissao_form_empregado_furo_create(
    *,
    form,
    empresa,
    furo,
):
    if not form.is_valid():
        return {
            "ok": False,
            "ligacao": None,
            "ligacao_projeto": None,
            "projeto_criado": False,
            "mensagem_sucesso": None,
            "mensagem_erro": "Erro ao associar trabalhador ao furo. Verifique os dados.",
        }

    empregado = form.cleaned_data["empregado"]
    ligacao = criar_ligacao_empregado_furo(
        empregado=empregado,
        furo=furo,
        empresa=empresa,
        funcao=form.cleaned_data["funcao"],
        data_inicio=form.cleaned_data.get("data_inicio"),
        data_fim=form.cleaned_data.get("data_fim"),
        ativo=form.cleaned_data.get("ativo", True),
        observacoes=form.cleaned_data.get("observacoes"),
    )
    ligacao_projeto, projeto_criado = garantir_ligacao_projeto_por_furo(
        empregado=empregado,
        furo=furo,
        empresa=empresa,
        data_inicio=form.cleaned_data.get("data_inicio"),
    )
    return {
        "ok": True,
        "ligacao": ligacao,
        "ligacao_projeto": ligacao_projeto,
        "projeto_criado": projeto_criado,
        "mensagem_sucesso": (
            "Trabalhador associado ao furo e automaticamente ligado ao projeto."
            if projeto_criado
            else "Trabalhador associado ao furo com sucesso."
        ),
        "mensagem_erro": None,
    }


def processar_submissao_form_empregado_furo_update(
    *,
    form,
    empresa,
    ligacao,
):
    if not form.is_valid():
        return {
            "ok": False,
            "ligacao": None,
            "ligacao_projeto": None,
            "projeto_criado": False,
            "mensagem_sucesso": None,
            "mensagem_erro": "Erro ao atualizar ligação trabalhador/furo. Verifique os dados.",
        }

    empregado = form.cleaned_data["empregado"]
    ligacao_atualizada = atualizar_ligacao_empregado_furo(
        ligacao=ligacao,
        empregado=empregado,
        empresa=empresa,
        funcao=form.cleaned_data["funcao"],
        data_inicio=form.cleaned_data.get("data_inicio"),
        data_fim=form.cleaned_data.get("data_fim"),
        ativo=form.cleaned_data.get("ativo", ligacao.ativo),
        observacoes=form.cleaned_data.get("observacoes"),
    )
    ligacao_projeto, projeto_criado = garantir_ligacao_projeto_por_furo(
        empregado=empregado,
        furo=ligacao_atualizada.furo,
        empresa=empresa,
        data_inicio=form.cleaned_data.get("data_inicio"),
    )
    return {
        "ok": True,
        "ligacao": ligacao_atualizada,
        "ligacao_projeto": ligacao_projeto,
        "projeto_criado": projeto_criado,
        "mensagem_sucesso": (
            "Ligação trabalhador/furo atualizada e projeto associado automaticamente."
            if projeto_criado
            else "Ligação trabalhador/furo atualizada com sucesso."
        ),
        "mensagem_erro": None,
    }


def processar_fluxo_form_empregado_furo(
    *,
    method,
    post_data,
    form_class,
    empresa,
    furo,
    instance=None,
    acao="create",
):
    form = preparar_form_empregado_furo(
        method=method,
        post_data=post_data,
        form_class=form_class,
        empresa=empresa,
        furo=furo,
        instance=instance,
    )

    if method != "POST":
        return {
            "form": form,
            "resultado": None,
        }

    if acao == "update":
        resultado = processar_submissao_form_empregado_furo_update(
            form=form,
            empresa=empresa,
            ligacao=instance,
        )
    else:
        resultado = processar_submissao_form_empregado_furo_create(
            form=form,
            empresa=empresa,
            furo=furo,
        )

    return {
        "form": form,
        "resultado": resultado,
    }
