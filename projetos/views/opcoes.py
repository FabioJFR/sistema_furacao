import csv
import io
import json
import textwrap
import zipfile
from xml.sax.saxutils import escape as xml_escape
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.utils import translation
from django.utils.text import slugify

from core.permissions import admin_required

from projetos.forms import EmpresaFinanceiraForm, PreferenciasForm
from projetos.models import (
    Despesa,
    Empregados,
    EventoAnalytics,
    Furo,
    Maquina,
    Material,
    Medicao,
    PreferenciasUser,
    Projeto,
    RegistoDiarioEmpregado,
)

from .projetos import _obter_empresa_admin_projetos


def _empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


def _parse_data(valor):
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        return None


def _obter_filtros_exportacao(request, empresa):
    projeto_id = (request.GET.get("projeto") or "").strip()
    furo_id = (request.GET.get("furo") or "").strip()
    tipo_registo = (request.GET.get("tipo_registo") or "").strip()
    categoria_despesa = (request.GET.get("categoria_despesa") or "").strip()
    data_inicio = _parse_data(request.GET.get("data_inicio"))
    data_fim = _parse_data(request.GET.get("data_fim"))
    projeto = None
    furo = None
    if projeto_id:
        projeto = Projeto.objects.filter(empresa=empresa, pk=projeto_id).first()
    if furo_id:
        furo_queryset = Furo.objects.filter(empresa=empresa, pk=furo_id)
        if projeto:
            furo_queryset = furo_queryset.filter(projeto=projeto)
        furo = furo_queryset.first()
    return {
        "projeto": projeto,
        "furo": furo,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "tipo_registo": tipo_registo,
        "categoria_despesa": categoria_despesa,
        "tipo_registo_label": dict(
            [("", "Todos os registos"), ("sem_paragem", "Sem paragem"), ("cliente", "Paragem do cliente"), ("empresa", "Paragem da empresa")]
        ).get(tipo_registo, tipo_registo),
        "categoria_despesa_label": dict(Despesa.CATEGORIA_CHOICES).get(categoria_despesa, categoria_despesa),
    }


def _filtrar_periodo_queryset(queryset, campo, filtros):
    if filtros.get("data_inicio"):
        queryset = queryset.filter(**{f"{campo}__gte": filtros["data_inicio"]})
    if filtros.get("data_fim"):
        queryset = queryset.filter(**{f"{campo}__lte": filtros["data_fim"]})
    return queryset


def _qs_projetos(empresa, filtros):
    queryset = Projeto.objects.filter(empresa=empresa)
    projeto = filtros.get("projeto")
    if projeto:
        queryset = queryset.filter(pk=projeto.pk)
    return _filtrar_periodo_queryset(queryset, "data_inicio_proj", filtros)


def _qs_furos(empresa, filtros):
    queryset = Furo.objects.filter(empresa=empresa)
    projeto = filtros.get("projeto")
    if projeto:
        queryset = queryset.filter(projeto=projeto)
    furo = filtros.get("furo")
    if furo:
        queryset = queryset.filter(pk=furo.pk)
    return _filtrar_periodo_queryset(queryset, "data__date", filtros)


def _qs_maquinas(empresa, filtros):
    queryset = Maquina.objects.filter(empresa=empresa)
    projeto = filtros.get("projeto")
    if projeto:
        queryset = queryset.filter(Q(projeto_atual=projeto) | Q(projetos=projeto)).distinct()
    furo = filtros.get("furo")
    if furo:
        queryset = queryset.filter(furos=furo).distinct()
    return _filtrar_periodo_queryset(queryset, "data_registo", filtros)


def _qs_materiais(empresa, filtros):
    queryset = Material.objects.filter(empresa=empresa)
    projeto = filtros.get("projeto")
    if projeto:
        queryset = queryset.filter(Q(projeto=projeto) | Q(furo__projeto=projeto)).distinct()
    furo = filtros.get("furo")
    if furo:
        queryset = queryset.filter(furo=furo)
    return _filtrar_periodo_queryset(queryset, "data_compra", filtros)


def _qs_empregados(empresa, filtros):
    queryset = Empregados.objects.filter(empresa=empresa)
    projeto = filtros.get("projeto")
    if projeto:
        queryset = queryset.filter(ligacoes_projetos__projeto=projeto).distinct()
    furo = filtros.get("furo")
    if furo:
        queryset = queryset.filter(Q(furos=furo) | Q(ligacoes_furos__furo=furo)).distinct()
    return _filtrar_periodo_queryset(queryset, "data_admissao", filtros)


def _qs_registos(empresa, filtros):
    queryset = RegistoDiarioEmpregado.objects.filter(empresa=empresa)
    projeto = filtros.get("projeto")
    if projeto:
        queryset = queryset.filter(projeto=projeto)
    furo = filtros.get("furo")
    if furo:
        queryset = queryset.filter(furo=furo)
    tipo_registo = filtros.get("tipo_registo")
    if tipo_registo == "sem_paragem":
        queryset = queryset.filter(tipo_paragem="")
    elif tipo_registo:
        queryset = queryset.filter(tipo_paragem=tipo_registo)
    return _filtrar_periodo_queryset(queryset, "data", filtros)


def _qs_medicoes(empresa, filtros):
    queryset = Medicao.objects.filter(empresa=empresa)
    projeto = filtros.get("projeto")
    if projeto:
        queryset = queryset.filter(furo__projeto=projeto)
    furo = filtros.get("furo")
    if furo:
        queryset = queryset.filter(furo=furo)
    return _filtrar_periodo_queryset(queryset, "criado_em__date", filtros)


def _qs_despesas(empresa, filtros):
    queryset = Despesa.objects.filter(empresa=empresa)
    projeto = filtros.get("projeto")
    if projeto:
        queryset = queryset.filter(Q(projeto=projeto) | Q(furo__projeto=projeto) | Q(maquina__projetos=projeto)).distinct()
    furo = filtros.get("furo")
    if furo:
        queryset = queryset.filter(Q(furo=furo) | Q(projeto=furo.projeto) | Q(maquina__furos=furo)).distinct()
    categoria_despesa = filtros.get("categoria_despesa")
    if categoria_despesa:
        queryset = queryset.filter(categoria=categoria_despesa)
    return _filtrar_periodo_queryset(queryset, "data", filtros)


def _qs_eventos(empresa, filtros):
    queryset = EventoAnalytics.objects.filter(empresa=empresa)
    projeto = filtros.get("projeto")
    if projeto:
        queryset = queryset.filter(Q(projeto=projeto) | Q(furo__projeto=projeto)).distinct()
    furo = filtros.get("furo")
    if furo:
        queryset = queryset.filter(furo=furo)
    return _filtrar_periodo_queryset(queryset, "criado_em__date", filtros)


def _coerce_export_value(value):
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, timedelta):
        return round(value.total_seconds(), 2)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if hasattr(value, "name"):
        return getattr(value, "name", "") or ""
    if isinstance(value, dict):
        return {str(chave): _coerce_export_value(item) for chave, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_coerce_export_value(item) for item in value]
    return str(value)


def _normalizar_linhas_exportacao(linhas):
    return [{chave: _coerce_export_value(valor) for chave, valor in linha.items()} for linha in linhas]


def _escapar_pdf_texto(texto):
    return (
        str(texto)
        .replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def _gerar_pdf_simples(titulo, subtitulo, linhas):
    linhas_paginas = []
    pagina_atual = [titulo, subtitulo, ""]
    linhas_usadas = len(pagina_atual)
    max_linhas_por_pagina = 46

    for linha in linhas:
        partes = textwrap.wrap(str(linha), width=92, break_long_words=False, break_on_hyphens=False) or [""]
        for parte in partes:
            if linhas_usadas >= max_linhas_por_pagina:
                linhas_paginas.append(pagina_atual)
                pagina_atual = []
                linhas_usadas = 0
            pagina_atual.append(parte)
            linhas_usadas += 1

    if pagina_atual:
        linhas_paginas.append(pagina_atual)

    objetos = []

    def adicionar_objeto(conteudo):
        objetos.append(conteudo)
        return len(objetos)

    fonte_id = adicionar_objeto("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    conteudos_ids = []

    for pagina in linhas_paginas:
        comandos = ["BT", "/F1 10 Tf", "40 800 Td", "13 TL"]
        for indice, linha in enumerate(pagina):
            linha_escapada = _escapar_pdf_texto(linha)
            if indice == 0:
                comandos.append(f"({linha_escapada}) Tj")
            else:
                comandos.append(f"T* ({linha_escapada}) Tj")
        comandos.append("ET")
        stream = "\n".join(comandos)
        tamanho = len(stream.encode("latin-1", errors="replace"))
        conteudos_ids.append(
            adicionar_objeto(f"<< /Length {tamanho} >>\nstream\n{stream}\nendstream")
        )

    paginas_id = len(objetos) + len(conteudos_ids) + 1
    pagina_ids = []
    for conteudo_id in conteudos_ids:
        pagina_ids.append(
            adicionar_objeto(
                f"<< /Type /Page /Parent {paginas_id} 0 R /MediaBox [0 0 595 842] "
                f"/Resources << /Font << /F1 {fonte_id} 0 R >> >> /Contents {conteudo_id} 0 R >>"
            )
        )

    filhos = " ".join(f"{pagina_id} 0 R" for pagina_id in pagina_ids)
    adicionar_objeto(f"<< /Type /Pages /Count {len(pagina_ids)} /Kids [{filhos}] >>")
    catalogo_id = adicionar_objeto(f"<< /Type /Catalog /Pages {paginas_id} 0 R >>")

    partes = [b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
    offsets = [0]
    for indice, objeto in enumerate(objetos, start=1):
        offsets.append(sum(len(parte) for parte in partes))
        partes.append(f"{indice} 0 obj\n{objeto}\nendobj\n".encode("latin-1", errors="replace"))

    xref_inicio = sum(len(parte) for parte in partes)
    partes.append(f"xref\n0 {len(objetos) + 1}\n".encode("latin-1"))
    partes.append(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        partes.append(f"{offset:010d} 00000 n \n".encode("latin-1"))
    partes.append(
        (
            f"trailer\n<< /Size {len(objetos) + 1} /Root {catalogo_id} 0 R >>\n"
            f"startxref\n{xref_inicio}\n%%EOF"
        ).encode("latin-1")
    )
    return b"".join(partes)


def _linhas_resumo_geral(empresa, filtros):
    financeiro = empresa.recalcular_indicadores_financeiros(guardar=False)
    return [
        {
            "empresa_id": empresa.pk,
            "empresa": empresa.nome,
            "filtro_projeto": filtros["projeto"].nome if filtros.get("projeto") else "",
            "filtro_data_inicio": filtros.get("data_inicio"),
            "filtro_data_fim": filtros.get("data_fim"),
            "total_projetos": _qs_projetos(empresa, filtros).count(),
            "total_furos": _qs_furos(empresa, filtros).count(),
            "total_empregados": _qs_empregados(empresa, filtros).count(),
            "total_maquinas": _qs_maquinas(empresa, filtros).count(),
            "total_materiais": _qs_materiais(empresa, filtros).count(),
            "total_registos": _qs_registos(empresa, filtros).count(),
            "total_medicoes": _qs_medicoes(empresa, filtros).count(),
            "total_despesas": _qs_despesas(empresa, filtros).count(),
            "total_eventos": _qs_eventos(empresa, filtros).count(),
            "custo_por_metro_cliente": financeiro.get("custo_por_metro_cliente", 0.0),
            "custo_por_metro_empresa": financeiro.get("custo_por_metro_empresa", 0.0),
            "valor_total_cobrado_cliente": financeiro.get("valor_total_cobrado_cliente", 0.0),
            "valor_total_gasto_furo": financeiro.get("valor_total_gasto_furo", 0.0),
            "valor_total_gasto_materias": financeiro.get("valor_total_gasto_materias", 0.0),
            "valor_total_gasto_maquinas": financeiro.get("valor_total_gasto_maquinas", 0.0),
            "valor_total_ganho_furo": financeiro.get("valor_total_ganho_furo", 0.0),
            "outros_valores_gastos_associados": financeiro.get("outros_valores_gastos_associados", 0.0),
        }
    ]


def _linhas_projetos(empresa, filtros):
    return [
        {
            "id": projeto.pk,
            "nome": projeto.nome,
            "cliente": projeto.cliente,
            "status": projeto.status,
            "cidade": projeto.cidade,
            "pais": projeto.pais,
            "data_inicio": projeto.data_inicio_proj,
            "data_fim": projeto.data_fim_proj,
            "total_furos": projeto.furos.count(),
            "total_maquinas": projeto.maquinas.count(),
            "notas": projeto.notas,
            "criado_em": projeto.criado_em,
            "atualizado_em": projeto.atualizado_em,
        }
        for projeto in _qs_projetos(empresa, filtros).order_by("nome")
    ]


def _linhas_furos(empresa, filtros):
    return [
        {
            "id": furo.pk,
            "projeto": furo.projeto.nome if furo.projeto_id else "",
            "nome": furo.nome,
            "tipo": furo.tipo,
            "estado": furo.estado,
            "localizacao": furo.localizacao or furo.local_sondagem,
            "profundidade_inicial": furo.profundidade_inicial,
            "profundidade_alvo_atual": furo.profundidade_alvo_atual,
            "profundidade_atual": furo.profundidade_atual,
            "profundidade_maxima_atingida": furo.profundidade_maxima_atingida,
            "metros_furados": furo.metros_furados,
            "inclinacao_planeada_atual": furo.inclinacao_planeada_atual,
            "azimute_planeado_atual": furo.azimute_planeado_atual,
            "inclinacao_real_atual": furo.inclinacao_real_atual,
            "azimute_real_atual": furo.azimute_real_atual,
            "sistema_coordenadas": furo.sistema_coordenadas,
            "origem_este": furo.origem_este,
            "origem_norte": furo.origem_norte,
            "origem_tvd": furo.origem_tvd,
            "data_criacao": furo.data,
        }
        for furo in _qs_furos(empresa, filtros).select_related("projeto").order_by("nome")
    ]


def _linhas_maquinas(empresa, filtros):
    return [
        {
            "id": maquina.pk,
            "nome": maquina.nome,
            "tipo": maquina.tipo,
            "estado": maquina.estado,
            "marca": maquina.marca,
            "modelo": maquina.modelo,
            "numero_serie": maquina.numero_serie,
            "matricula": maquina.matricula,
            "projeto_atual": maquina.projeto_atual.nome if maquina.projeto_atual_id else "",
            "km": maquina.km,
            "horimetro": maquina.horimetro,
            "valor": maquina.valor,
            "localizacao_atual": maquina.localizacao_atual,
            "ativo": maquina.ativo,
            "data_compra": maquina.data_compra,
            "data_revisao": maquina.data_revisao,
        }
        for maquina in _qs_maquinas(empresa, filtros).select_related("projeto_atual").order_by("nome")
    ]


def _linhas_materiais(empresa, filtros):
    return [
        {
            "id": material.pk,
            "nome": material.nome,
            "tipo": material.tipo,
            "estado": material.estado,
            "quantidade": material.quantidade,
            "unidade": material.unidade,
            "stock_minimo": material.stock_minimo,
            "diametro": material.diametro,
            "valor_unitario": material.valor,
            "fornecedor": material.fornecedor,
            "projeto": material.projeto.nome if material.projeto_id else "",
            "furo": material.furo.nome if material.furo_id else "",
            "localizacao": material.localizacao,
            "numero_serie": material.numero_serie,
            "observacoes": material.observacoes,
        }
        for material in _qs_materiais(empresa, filtros).select_related("projeto", "furo").order_by("nome")
    ]


def _linhas_empregados(empresa, filtros):
    return [
        {
            "id": empregado.pk,
            "nome": empregado.nome,
            "funcao": empregado.get_funcao_display() if empregado.funcao else "",
            "email": empregado.email,
            "telefone": empregado.telefone,
            "data_admissao": empregado.data_admissao,
            "aprovado": empregado.aprovado,
            "salario": empregado.salario,
            "horas_diarias": empregado.horas_diarias,
            "horas_mensais": empregado.horas_mensais,
            "total_metros_furados": empregado.total_metros_furados,
            "total_furos_trabalhados": empregado.total_furos_trabalhados,
            "media_metros_por_hora": empregado.media_metros_por_hora,
            "media_metros_por_dia": empregado.media_metros_por_dia,
        }
        for empregado in _qs_empregados(empresa, filtros).order_by("nome")
    ]


def _linhas_registos(empresa, filtros):
    return [
        {
            "id": registo.pk,
            "data": registo.data,
            "empregado": registo.empregado.nome if registo.empregado_id else "",
            "projeto": registo.projeto.nome if registo.projeto_id else "",
            "furo": registo.furo.nome if registo.furo_id else "",
            "metros_furados": registo.metros_furados,
            "horas_trabalhadas": registo.horas_trabalhadas,
            "horas_paragem": registo.horas_paragem,
            "tipo_paragem": registo.get_tipo_paragem_display() if registo.tipo_paragem else "",
            "profundidade_antes": registo.profundidade_furo_antes,
            "profundidade_depois": registo.profundidade_furo_depois,
            "observacoes": registo.observacoes,
            "relatorio_foto": registo.relatorio_foto,
            "criado_em": registo.criado_em,
        }
        for registo in _qs_registos(empresa, filtros)
        .select_related("empregado", "projeto", "furo")
        .order_by("-data", "-criado_em")
    ]


def _linhas_medicoes(empresa, filtros):
    return [
        {
            "id": medicao.pk,
            "furo": medicao.furo.nome if medicao.furo_id else medicao.nome_furo_snapshot,
            "profundidade_medida": medicao.profundidade_medida,
            "inclinacao_real_medida": medicao.inclinacao_real_medida,
            "azimute_real_medido": medicao.azimute_real_medido,
            "inclinacao_planeada_atual_furo": medicao.inclinacao_planeada_atual_furo,
            "azimute_planeado_atual_furo": medicao.azimute_planeado_atual_furo,
            "tipo_rocha": medicao.tipo_rocha,
            "dureza": medicao.dureza,
            "magnetismo": medicao.magnetismo,
            "observacoes": medicao.observacoes,
            "criado_em": medicao.criado_em,
        }
        for medicao in _qs_medicoes(empresa, filtros).select_related("furo").order_by("-criado_em")
    ]


def _linhas_despesas(empresa, filtros):
    return [
        {
            "id": despesa.pk,
            "data": despesa.data,
            "categoria": despesa.get_categoria_display() if despesa.categoria else "",
            "tipo": despesa.get_tipo_display() if despesa.tipo else despesa.tipo,
            "descricao": despesa.descricao,
            "valor": despesa.valor,
            "projeto": despesa.projeto.nome if despesa.projeto_id else "",
            "furo": despesa.furo.nome if despesa.furo_id else "",
            "maquina": despesa.maquina.nome if despesa.maquina_id else "",
            "observacoes": despesa.observacoes,
            "comprovativo": despesa.comprovativo,
            "criado_em": despesa.criado_em,
        }
        for despesa in _qs_despesas(empresa, filtros)
        .select_related("projeto", "furo", "maquina")
        .order_by("-data", "-criado_em")
    ]


def _linhas_eventos(empresa, filtros):
    return [
        {
            "id": evento.pk,
            "criado_em": evento.criado_em,
            "tipo_evento": evento.get_tipo_evento_display(),
            "entidade_tipo": evento.entidade_tipo,
            "entidade_id": evento.entidade_id,
            "entidade_label": evento.entidade_label,
            "ator": evento.actor_username,
            "ator_tipo": evento.actor_tipo,
            "projeto": evento.projeto.nome if evento.projeto_id else "",
            "furo": evento.furo.nome if evento.furo_id else "",
            "empregado": evento.empregado.nome if evento.empregado_id else "",
            "material": evento.material.nome if evento.material_id else "",
            "maquina": evento.maquina.nome if evento.maquina_id else "",
            "metricas": json.dumps(_coerce_export_value(evento.metricas), ensure_ascii=False),
        }
        for evento in _qs_eventos(empresa, filtros)
        .select_related("projeto", "furo", "empregado", "material", "maquina")
        .order_by("-criado_em")
    ]


EXPORT_DATASETS = {
    "resumo_geral": {
        "titulo": "Resumo Geral",
        "descricao": "Indicadores agregados da empresa, operação e finanças.",
        "icone": "🧭",
        "count": lambda empresa, filtros: 1,
        "builder": _linhas_resumo_geral,
    },
    "projetos": {
        "titulo": "Projetos",
        "descricao": "Projetos da empresa com cliente, estado, datas e contexto operacional.",
        "icone": "📁",
        "count": lambda empresa, filtros: _qs_projetos(empresa, filtros).count(),
        "builder": _linhas_projetos,
    },
    "furos": {
        "titulo": "Furos",
        "descricao": "Dados técnicos, profundidades, orientação e progresso de cada furo.",
        "icone": "🕳",
        "count": lambda empresa, filtros: _qs_furos(empresa, filtros).count(),
        "builder": _linhas_furos,
    },
    "maquinas": {
        "titulo": "Máquinas",
        "descricao": "Frota, estado operacional, localização e indicadores de utilização.",
        "icone": "⚙️",
        "count": lambda empresa, filtros: _qs_maquinas(empresa, filtros).count(),
        "builder": _linhas_maquinas,
    },
    "materiais": {
        "titulo": "Materiais",
        "descricao": "Stocks, valores, fornecedores e contexto de projeto/furo.",
        "icone": "📦",
        "count": lambda empresa, filtros: _qs_materiais(empresa, filtros).count(),
        "builder": _linhas_materiais,
    },
    "empregados": {
        "titulo": "Empregados",
        "descricao": "Equipa, funções, aprovação e métricas principais de produção.",
        "icone": "👷",
        "count": lambda empresa, filtros: _qs_empregados(empresa, filtros).count(),
        "builder": _linhas_empregados,
    },
    "registos": {
        "titulo": "Registos",
        "descricao": "Produção diária, tempos, observações e evolução dos furos.",
        "icone": "📋",
        "count": lambda empresa, filtros: _qs_registos(empresa, filtros).count(),
        "builder": _linhas_registos,
    },
    "medicoes": {
        "titulo": "Medições",
        "descricao": "Medições técnicas, desvios, rocha e dados usados no 3D.",
        "icone": "📏",
        "count": lambda empresa, filtros: _qs_medicoes(empresa, filtros).count(),
        "builder": _linhas_medicoes,
    },
    "despesas": {
        "titulo": "Despesas",
        "descricao": "Custos por projeto, furo, máquina e despesas gerais da empresa.",
        "icone": "💸",
        "count": lambda empresa, filtros: _qs_despesas(empresa, filtros).count(),
        "builder": _linhas_despesas,
    },
    "eventos": {
        "titulo": "Eventos",
        "descricao": "Histórico de alterações e interações para analytics e auditoria.",
        "icone": "🧾",
        "count": lambda empresa, filtros: _qs_eventos(empresa, filtros).count(),
        "builder": _linhas_eventos,
    },
}


def _obter_dataset_exportacao(dataset):
    try:
        return EXPORT_DATASETS[dataset]
    except KeyError as exc:
        raise Http404("Dataset de exportação inválido.") from exc


def _sufixo_nome_filtros(filtros):
    partes = []
    if filtros.get("projeto"):
        partes.append(f"projeto-{slugify(filtros['projeto'].nome)}")
    if filtros.get("furo"):
        partes.append(f"furo-{slugify(filtros['furo'].nome)}")
    if filtros.get("data_inicio"):
        partes.append(f"de-{filtros['data_inicio'].strftime('%Y%m%d')}")
    if filtros.get("data_fim"):
        partes.append(f"ate-{filtros['data_fim'].strftime('%Y%m%d')}")
    if filtros.get("tipo_registo"):
        partes.append(f"registo-{slugify(filtros['tipo_registo'])}")
    if filtros.get("categoria_despesa"):
        partes.append(f"despesa-{slugify(filtros['categoria_despesa'])}")
    return "-".join(parte for parte in partes if parte)


def _renderizar_csv_exportacao(linhas):
    output = io.StringIO()
    colunas = []
    for linha in linhas:
        for chave in linha.keys():
            if chave not in colunas:
                colunas.append(chave)

    writer = csv.DictWriter(output, fieldnames=colunas)
    writer.writeheader()
    for linha in linhas:
        writer.writerow({chave: linha.get(chave, "") for chave in colunas})
    return output.getvalue()


def _coluna_excel(indice):
    resultado = ""
    while indice > 0:
        indice, resto = divmod(indice - 1, 26)
        resultado = chr(65 + resto) + resultado
    return resultado


def _worksheet_xml(nome_folha, linhas):
    colunas = []
    for linha in linhas:
        for chave in linha.keys():
            if chave not in colunas:
                colunas.append(chave)

    dados = [colunas]
    for linha in linhas:
        dados.append([linha.get(coluna, "") for coluna in colunas])

    xml_linhas = []
    for row_idx, linha in enumerate(dados, start=1):
        cells = []
        for col_idx, value in enumerate(linha, start=1):
            ref = f"{_coluna_excel(col_idx)}{row_idx}"
            if isinstance(value, bool):
                cell_xml = f'<c r="{ref}" t="b"><v>{1 if value else 0}</v></c>'
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                cell_xml = f'<c r="{ref}"><v>{value}</v></c>'
            else:
                texto = xml_escape(str(value))
                cell_xml = f'<c r="{ref}" t="inlineStr"><is><t>{texto}</t></is></c>'
            cells.append(cell_xml)
        xml_linhas.append(f'<row r="{row_idx}">{"".join(cells)}</row>')

    dimensao_fim = f"{_coluna_excel(max(len(colunas), 1))}{max(len(dados), 1)}"
    sheet_name_safe = xml_escape(nome_folha)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheetPr><tabColor rgb="1F4ED8"/></sheetPr>'
        f'<dimension ref="A1:{dimensao_fim}"/>'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        '<cols><col min="1" max="50" width="20" customWidth="1"/></cols>'
        f'<sheetData>{"".join(xml_linhas)}</sheetData>'
        f'<headerFooter><oddHeader>&amp;C&amp;"Calibri,Bold"&amp;14 {sheet_name_safe}</oddHeader></headerFooter>'
        '</worksheet>'
    )


def _renderizar_xlsx_exportacao(dataset_info, linhas):
    sheet_name = (dataset_info["titulo"] or "Dados")[:31]
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<fileVersion appName="xl"/>'
        '<workbookPr/>'
        '<bookViews><workbookView xWindow="0" yWindow="0" windowWidth="24000" windowHeight="12000"/></bookViews>'
        f'<sheets><sheet name="{xml_escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets>'
        '</workbook>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
        '</Relationships>'
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
        'Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
        'Target="docProps/app.xml"/>'
        '</Relationships>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        '</Types>'
    )
    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        '</styleSheet>'
    )
    criado = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    core_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<dc:creator>Sistema Furacao</dc:creator>'
        f'<dc:title>{xml_escape(dataset_info["titulo"])}</dc:title>'
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{criado}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{criado}</dcterms:modified>'
        '</cp:coreProperties>'
    )
    app_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        '<Application>Sistema Furacao</Application>'
        '</Properties>'
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("[Content_Types].xml", content_types)
        zip_file.writestr("_rels/.rels", root_rels)
        zip_file.writestr("docProps/core.xml", core_xml)
        zip_file.writestr("docProps/app.xml", app_xml)
        zip_file.writestr("xl/workbook.xml", workbook_xml)
        zip_file.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zip_file.writestr("xl/styles.xml", styles_xml)
        zip_file.writestr("xl/worksheets/sheet1.xml", _worksheet_xml(sheet_name, linhas))
    return buffer.getvalue()


def _renderizar_json_exportacao(dataset, empresa, linhas):
    payload = {
        "dataset": dataset,
        "empresa": {
            "id": str(empresa.pk),
            "nome": empresa.nome,
        },
        "gerado_em": datetime.now().isoformat(),
        "total_registos": len(linhas),
        "rows": linhas,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _renderizar_pdf_exportacao(dataset_info, empresa, linhas):
    titulo = f"{dataset_info['icone']} {dataset_info['titulo']} - {empresa.nome}"
    subtitulo = f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} · Total de registos: {len(linhas)}"
    linhas_pdf = []
    for indice, linha in enumerate(linhas, start=1):
        linhas_pdf.append(f"{indice}.")
        for chave, valor in linha.items():
            linhas_pdf.append(f"{chave}: {valor}")
        linhas_pdf.append("")
    return _gerar_pdf_simples(titulo, subtitulo, linhas_pdf or ["Sem registos para exportação."])


@login_required
@admin_required
def definicoes_admin(request):
    empresa, resposta_erro = _obter_empresa_admin_projetos(request)
    if resposta_erro:
        return resposta_erro

    preferencias, _ = PreferenciasUser.objects.get_or_create(user=request.user)
    preferencias.empresa = empresa
    preferencias.save(update_fields=["empresa"])

    if request.method == "POST":
        form = PreferenciasForm(instance=preferencias, user=request.user, prefix="prefs")
        financeiro_form = EmpresaFinanceiraForm(instance=empresa, prefix="financeiro")

        if "guardar_preferencias" in request.POST:
            form = PreferenciasForm(request.POST, instance=preferencias, user=request.user, prefix="prefs")
            if form.is_valid():
                preferencias = form.save(commit=False)
                preferencias.user = request.user
                preferencias.empresa = empresa
                preferencias.save()

                if preferencias.idioma:
                    translation.activate(preferencias.idioma)
                    request.session["django_language"] = preferencias.idioma

                messages.success(request, "Preferências guardadas com sucesso.")
                return redirect("projetos:definicoes_admin")

            messages.error(request, "Erro ao guardar preferências.")

        if "guardar_financeiro" in request.POST:
            financeiro_form = EmpresaFinanceiraForm(request.POST, instance=empresa, prefix="financeiro")
            if financeiro_form.is_valid():
                empresa = financeiro_form.save()
                empresa.recalcular_indicadores_financeiros()
                messages.success(request, "Definições financeiras guardadas com sucesso.")
                return redirect("projetos:definicoes_admin")

            messages.error(request, "Erro ao guardar definições financeiras.")
    else:
        form = PreferenciasForm(instance=preferencias, user=request.user, prefix="prefs")
        financeiro_form = EmpresaFinanceiraForm(instance=empresa, prefix="financeiro")

    financeiro_preview = empresa.recalcular_indicadores_financeiros(guardar=False)

    return render(
        request,
        "projetos/definicoes_admin.html",
        {
            "form": form,
            "financeiro_form": financeiro_form,
            "titulo": "Definições da Empresa",
            "empresa": empresa,
            "financeiro_preview": financeiro_preview,
        },
    )


@login_required
@admin_required
def procurar_dashboard(request):
    empresa, resposta_erro = _obter_empresa_admin_projetos(request)
    if resposta_erro:
        return resposta_erro

    termo = request.GET.get("q", "").strip()
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

    if termo:
        resultados["projetos"] = (
            Projeto.objects.filter(empresa_id=empresa_id)
            .filter(
                Q(nome__icontains=termo)
                | Q(cliente__icontains=termo)
                | Q(cidade__icontains=termo)
                | Q(pais__icontains=termo)
                | Q(notas__icontains=termo)
            )
            .order_by("nome")[:12]
        )
        resultados["furos"] = (
            Furo.objects.filter(empresa_id=empresa_id)
            .select_related("projeto")
            .filter(
                Q(nome__icontains=termo)
                | Q(localizacao__icontains=termo)
                | Q(local_sondagem__icontains=termo)
                | Q(detalhes__icontains=termo)
            )
            .order_by("nome")[:12]
        )
        resultados["empregados"] = (
            Empregados.objects.filter(empresa_id=empresa_id)
            .filter(
                Q(nome__icontains=termo)
                | Q(email__icontains=termo)
                | Q(telefone__icontains=termo)
                | Q(funcao__icontains=termo)
                | Q(morada__icontains=termo)
            )
            .order_by("nome")[:12]
        )
        resultados["maquinas"] = (
            Maquina.objects.filter(empresa_id=empresa_id)
            .filter(
                Q(nome__icontains=termo)
                | Q(tipo__icontains=termo)
                | Q(marca__icontains=termo)
                | Q(modelo__icontains=termo)
                | Q(numero_serie__icontains=termo)
                | Q(matricula__icontains=termo)
                | Q(localizacao_atual__icontains=termo)
            )
            .order_by("nome")[:12]
        )
        resultados["materiais"] = (
            Material.objects.filter(empresa_id=empresa_id)
            .select_related("projeto", "furo")
            .filter(
                Q(nome__icontains=termo)
                | Q(tipo__icontains=termo)
                | Q(marca__icontains=termo)
                | Q(numero_serie__icontains=termo)
                | Q(fornecedor__icontains=termo)
                | Q(localizacao__icontains=termo)
                | Q(observacoes__icontains=termo)
            )
            .order_by("nome")[:12]
        )
        resultados["registos"] = (
            RegistoDiarioEmpregado.objects.filter(empresa_id=empresa_id)
            .select_related("empregado", "projeto", "furo")
            .filter(
                Q(observacoes__icontains=termo)
                | Q(empregado__nome__icontains=termo)
                | Q(projeto__nome__icontains=termo)
                | Q(furo__nome__icontains=termo)
            )
            .order_by("-data", "-criado_em")[:12]
        )
        resultados["medicoes"] = (
            Medicao.objects.filter(empresa_id=empresa_id)
            .select_related("furo")
            .filter(
                Q(nome_furo_snapshot__icontains=termo)
                | Q(tipo_rocha__icontains=termo)
                | Q(observacoes__icontains=termo)
                | Q(furo__nome__icontains=termo)
            )
            .order_by("-criado_em")[:12]
        )
        resultados["despesas"] = (
            Despesa.objects.filter(empresa_id=empresa_id)
            .select_related("projeto", "furo", "maquina")
            .filter(
                Q(descricao__icontains=termo)
                | Q(tipo__icontains=termo)
                | Q(categoria__icontains=termo)
                | Q(observacoes__icontains=termo)
            )
            .order_by("-data", "-criado_em")[:12]
        )
        resultados["eventos"] = (
            EventoAnalytics.objects.filter(empresa_id=empresa_id)
            .select_related("projeto", "furo", "empregado", "material", "maquina")
            .filter(
                Q(entidade_tipo__icontains=termo)
                | Q(entidade_label__icontains=termo)
                | Q(actor_username__icontains=termo)
            )
            .order_by("-criado_em")[:20]
        )

        totais = {
            "projetos": Projeto.objects.filter(empresa_id=empresa_id).filter(
                Q(nome__icontains=termo)
                | Q(cliente__icontains=termo)
                | Q(cidade__icontains=termo)
                | Q(pais__icontains=termo)
                | Q(notas__icontains=termo)
            ).count(),
            "furos": Furo.objects.filter(empresa_id=empresa_id).filter(
                Q(nome__icontains=termo)
                | Q(localizacao__icontains=termo)
                | Q(local_sondagem__icontains=termo)
                | Q(detalhes__icontains=termo)
            ).count(),
            "empregados": Empregados.objects.filter(empresa_id=empresa_id).filter(
                Q(nome__icontains=termo)
                | Q(email__icontains=termo)
                | Q(telefone__icontains=termo)
                | Q(funcao__icontains=termo)
                | Q(morada__icontains=termo)
            ).count(),
            "maquinas": Maquina.objects.filter(empresa_id=empresa_id).filter(
                Q(nome__icontains=termo)
                | Q(tipo__icontains=termo)
                | Q(marca__icontains=termo)
                | Q(modelo__icontains=termo)
                | Q(numero_serie__icontains=termo)
                | Q(matricula__icontains=termo)
                | Q(localizacao_atual__icontains=termo)
            ).count(),
            "materiais": Material.objects.filter(empresa_id=empresa_id).filter(
                Q(nome__icontains=termo)
                | Q(tipo__icontains=termo)
                | Q(marca__icontains=termo)
                | Q(numero_serie__icontains=termo)
                | Q(fornecedor__icontains=termo)
                | Q(localizacao__icontains=termo)
                | Q(observacoes__icontains=termo)
            ).count(),
            "registos": RegistoDiarioEmpregado.objects.filter(empresa_id=empresa_id).filter(
                Q(observacoes__icontains=termo)
                | Q(empregado__nome__icontains=termo)
                | Q(projeto__nome__icontains=termo)
                | Q(furo__nome__icontains=termo)
            ).count(),
            "medicoes": Medicao.objects.filter(empresa_id=empresa_id).filter(
                Q(nome_furo_snapshot__icontains=termo)
                | Q(tipo_rocha__icontains=termo)
                | Q(observacoes__icontains=termo)
                | Q(furo__nome__icontains=termo)
            ).count(),
            "despesas": Despesa.objects.filter(empresa_id=empresa_id).filter(
                Q(descricao__icontains=termo)
                | Q(tipo__icontains=termo)
                | Q(categoria__icontains=termo)
                | Q(observacoes__icontains=termo)
            ).count(),
            "eventos": EventoAnalytics.objects.filter(empresa_id=empresa_id).filter(
                Q(entidade_tipo__icontains=termo)
                | Q(entidade_label__icontains=termo)
                | Q(actor_username__icontains=termo)
            ).count(),
        }

    return render(
        request,
        "projetos/procurar_dashboard.html",
        {
            "empresa": empresa,
            "termo": termo,
            "resultados": resultados,
            "totais": totais,
        },
    )


@login_required
@admin_required
def relatorios_exportacao(request):
    empresa, resposta_erro = _obter_empresa_admin_projetos(request)
    if resposta_erro:
        return resposta_erro

    filtros = _obter_filtros_exportacao(request, empresa)
    datasets = []
    for chave, info in EXPORT_DATASETS.items():
        datasets.append(
            {
                "key": chave,
                "titulo": info["titulo"],
                "descricao": info["descricao"],
                "icone": info["icone"],
                "total": info["count"](empresa, filtros),
            }
        )

    return render(
        request,
        "projetos/relatorios_exportacao.html",
        {
            "empresa": empresa,
            "datasets": datasets,
            "projetos_filtro": Projeto.objects.filter(empresa=empresa).order_by("nome"),
            "furos_filtro": _qs_furos(empresa, {"projeto": filtros.get("projeto"), "furo": None, "data_inicio": None, "data_fim": None, "tipo_registo": "", "categoria_despesa": ""}).order_by("nome"),
            "tipos_registo": [
                ("", "Todos os registos"),
                ("sem_paragem", "Sem paragem"),
                ("cliente", "Paragem do cliente"),
                ("empresa", "Paragem da empresa"),
            ],
            "categorias_despesa": [("", "Todas as categorias"), *Despesa.CATEGORIA_CHOICES],
            "filtros": filtros,
        },
    )


@login_required
@admin_required
def relatorios_download(request, dataset, formato):
    empresa, resposta_erro = _obter_empresa_admin_projetos(request)
    if resposta_erro:
        return resposta_erro

    filtros = _obter_filtros_exportacao(request, empresa)
    dataset_info = _obter_dataset_exportacao(dataset)
    linhas = _normalizar_linhas_exportacao(dataset_info["builder"](empresa, filtros))
    empresa_slug = slugify(empresa.nome) or "empresa"
    dataset_slug = slugify(dataset_info["titulo"]) or dataset
    filtro_slug = _sufixo_nome_filtros(filtros)
    nome_base = f"{empresa_slug}-{dataset_slug}"
    if filtro_slug:
        nome_base = f"{nome_base}-{filtro_slug}"

    if formato == "csv":
        conteudo = _renderizar_csv_exportacao(linhas)
        response = HttpResponse(conteudo, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{nome_base}.csv"'
        return response

    if formato == "json":
        conteudo = _renderizar_json_exportacao(dataset, empresa, linhas)
        response = HttpResponse(conteudo, content_type="application/json; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{nome_base}.json"'
        return response

    if formato == "pdf":
        conteudo = _renderizar_pdf_exportacao(dataset_info, empresa, linhas)
        response = HttpResponse(conteudo, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{nome_base}.pdf"'
        return response

    if formato == "xlsx":
        conteudo = _renderizar_xlsx_exportacao(dataset_info, linhas)
        response = HttpResponse(
            conteudo,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{nome_base}.xlsx"'
        return response

    raise Http404("Formato de exportação inválido.")


@login_required
@admin_required
def relatorios_download_tudo(request, formato):
    empresa, resposta_erro = _obter_empresa_admin_projetos(request)
    if resposta_erro:
        return resposta_erro

    if formato not in {"csv", "json", "pdf", "xlsx"}:
        raise Http404("Formato de exportação inválido.")

    filtros = _obter_filtros_exportacao(request, empresa)
    empresa_slug = slugify(empresa.nome) or "empresa"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    filtro_slug = _sufixo_nome_filtros(filtros)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for dataset_key, dataset_info in EXPORT_DATASETS.items():
            linhas = _normalizar_linhas_exportacao(dataset_info["builder"](empresa, filtros))
            dataset_slug = slugify(dataset_info["titulo"]) or dataset_key
            nome_arquivo = f"{empresa_slug}-{dataset_slug}"
            if filtro_slug:
                nome_arquivo = f"{nome_arquivo}-{filtro_slug}"
            nome_arquivo = f"{nome_arquivo}.{formato}"

            if formato == "csv":
                conteudo = _renderizar_csv_exportacao(linhas).encode("utf-8")
            elif formato == "json":
                conteudo = _renderizar_json_exportacao(dataset_key, empresa, linhas).encode("utf-8")
            elif formato == "pdf":
                conteudo = _renderizar_pdf_exportacao(dataset_info, empresa, linhas)
            else:
                conteudo = _renderizar_xlsx_exportacao(dataset_info, linhas)

            zip_file.writestr(nome_arquivo, conteudo)

    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
    nome_zip = f"{empresa_slug}-relatorios"
    if filtro_slug:
        nome_zip = f"{nome_zip}-{filtro_slug}"
    nome_zip = f"{nome_zip}-{formato}-{timestamp}.zip"
    response["Content-Disposition"] = f'attachment; filename="{nome_zip}"'
    return response
