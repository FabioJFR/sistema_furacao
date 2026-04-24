from projetos.models import EmpregadoFuro


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
