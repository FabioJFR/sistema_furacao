from django.db.models import Q

from projetos.models import (
    Despesa,
    Empregados,
    EventoAnalytics,
    Furo,
    Maquina,
    Material,
    Medicao,
    Projeto,
    RegistoDiarioEmpregado,
)


def _empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


def obter_resultados_procurar_dashboard(empresa, termo):
    empresa_id = _empresa_id(empresa)
    resultados = {
        "projetos": Projeto.objects.none(),
        "furos": Furo.objects.none(),
        "empregados": Empregados.objects.none(),
        "maquinas": Maquina.objects.none(),
        "materiais": Material.objects.none(),
        "registos": RegistoDiarioEmpregado.objects.none(),
        "medicoes": Medicao.objects.none(),
        "despesas": Despesa.objects.none(),
        "eventos": EventoAnalytics.objects.none(),
    }
    totais = {chave: 0 for chave in resultados}

    if not termo:
        return resultados, totais

    filtros_projetos = (
        Q(nome__icontains=termo)
        | Q(cliente__icontains=termo)
        | Q(cidade__icontains=termo)
        | Q(pais__icontains=termo)
        | Q(notas__icontains=termo)
    )
    filtros_furos = (
        Q(nome__icontains=termo)
        | Q(localizacao__icontains=termo)
        | Q(local_sondagem__icontains=termo)
        | Q(detalhes__icontains=termo)
    )
    filtros_empregados = (
        Q(nome__icontains=termo)
        | Q(email__icontains=termo)
        | Q(telefone__icontains=termo)
        | Q(funcao__icontains=termo)
        | Q(morada__icontains=termo)
    )
    filtros_maquinas = (
        Q(nome__icontains=termo)
        | Q(tipo__icontains=termo)
        | Q(marca__icontains=termo)
        | Q(modelo__icontains=termo)
        | Q(numero_serie__icontains=termo)
        | Q(matricula__icontains=termo)
        | Q(localizacao_atual__icontains=termo)
    )
    filtros_materiais = (
        Q(nome__icontains=termo)
        | Q(tipo__icontains=termo)
        | Q(marca__icontains=termo)
        | Q(numero_serie__icontains=termo)
        | Q(fornecedor__icontains=termo)
        | Q(localizacao__icontains=termo)
        | Q(observacoes__icontains=termo)
    )
    filtros_registos = (
        Q(observacoes__icontains=termo)
        | Q(empregado__nome__icontains=termo)
        | Q(projeto__nome__icontains=termo)
        | Q(furo__nome__icontains=termo)
    )
    filtros_medicoes = (
        Q(nome_furo_snapshot__icontains=termo)
        | Q(tipo_rocha__icontains=termo)
        | Q(observacoes__icontains=termo)
        | Q(furo__nome__icontains=termo)
    )
    filtros_despesas = (
        Q(descricao__icontains=termo)
        | Q(tipo__icontains=termo)
        | Q(categoria__icontains=termo)
        | Q(observacoes__icontains=termo)
    )
    filtros_eventos = (
        Q(entidade_tipo__icontains=termo)
        | Q(entidade_label__icontains=termo)
        | Q(actor_username__icontains=termo)
    )

    resultados["projetos"] = (
        Projeto.objects.filter(empresa_id=empresa_id).filter(filtros_projetos).order_by("nome")[:12]
    )
    resultados["furos"] = (
        Furo.objects.filter(empresa_id=empresa_id)
        .select_related("projeto")
        .filter(filtros_furos)
        .order_by("nome")[:12]
    )
    resultados["empregados"] = (
        Empregados.objects.filter(empresa_id=empresa_id).filter(filtros_empregados).order_by("nome")[:12]
    )
    resultados["maquinas"] = (
        Maquina.objects.filter(empresa_id=empresa_id).filter(filtros_maquinas).order_by("nome")[:12]
    )
    resultados["materiais"] = (
        Material.objects.filter(empresa_id=empresa_id)
        .select_related("projeto", "furo")
        .filter(filtros_materiais)
        .order_by("nome")[:12]
    )
    resultados["registos"] = (
        RegistoDiarioEmpregado.objects.filter(empresa_id=empresa_id)
        .select_related("empregado", "projeto", "furo")
        .filter(filtros_registos)
        .order_by("-data", "-criado_em")[:12]
    )
    resultados["medicoes"] = (
        Medicao.objects.filter(empresa_id=empresa_id)
        .select_related("furo")
        .filter(filtros_medicoes)
        .order_by("-criado_em")[:12]
    )
    resultados["despesas"] = (
        Despesa.objects.filter(empresa_id=empresa_id)
        .select_related("projeto", "furo", "maquina")
        .filter(filtros_despesas)
        .order_by("-data", "-criado_em")[:12]
    )
    resultados["eventos"] = (
        EventoAnalytics.objects.filter(empresa_id=empresa_id)
        .select_related("projeto", "furo", "empregado", "material", "maquina")
        .filter(filtros_eventos)
        .order_by("-criado_em")[:20]
    )

    totais = {
        "projetos": Projeto.objects.filter(empresa_id=empresa_id).filter(filtros_projetos).count(),
        "furos": Furo.objects.filter(empresa_id=empresa_id).filter(filtros_furos).count(),
        "empregados": Empregados.objects.filter(empresa_id=empresa_id).filter(filtros_empregados).count(),
        "maquinas": Maquina.objects.filter(empresa_id=empresa_id).filter(filtros_maquinas).count(),
        "materiais": Material.objects.filter(empresa_id=empresa_id).filter(filtros_materiais).count(),
        "registos": RegistoDiarioEmpregado.objects.filter(empresa_id=empresa_id).filter(filtros_registos).count(),
        "medicoes": Medicao.objects.filter(empresa_id=empresa_id).filter(filtros_medicoes).count(),
        "despesas": Despesa.objects.filter(empresa_id=empresa_id).filter(filtros_despesas).count(),
        "eventos": EventoAnalytics.objects.filter(empresa_id=empresa_id).filter(filtros_eventos).count(),
    }
    return resultados, totais
