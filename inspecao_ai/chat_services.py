import ast
import math
import operator
import re
from pathlib import Path
from datetime import date, datetime, time
from decimal import Decimal

from django.db.models import Count, Sum

from projetos.models import Despesa, Empregados, EventoAnalytics, Furo, Maquina, Material, Medicao, Projeto, RegistoDiarioEmpregado


SAFE_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}

SAFE_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

SAFE_FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "pi": lambda: math.pi,
    "e": lambda: math.e,
}

KNOWLEDGE_BASE_ROOT = Path(__file__).resolve().parent.parent / "knowledge_base"


def gerar_resposta_chat(*, empresa, pergunta):
    texto = (pergunta or "").strip()
    if not texto:
        return "Escreve uma pergunta e eu respondo com base nos dados atuais da empresa.", {}

    resumo = construir_resumo_empresa(empresa)
    texto_lower = texto.lower()

    if _parece_calculo(texto_lower):
        resultado = _avaliar_expressao_segura(texto)
        if resultado is not None:
            return (
                f"Resultado: {resultado}\n\nPosso também ajudar a relacionar este cálculo com metros furados, custos, margens ou despesas da empresa.",
                {"tipo": "calculo"},
            )

    if any(palavra in texto_lower for palavra in ["funciona a plataforma", "como funciona", "o que podes fazer", "ajuda", "ajudar"]):
        return _resposta_capacidades(resumo), {"tipo": "ajuda"}

    if any(
        palavra in texto_lower
        for palavra in [
            "documento",
            "documentos",
            "pdf",
            "relatório",
            "relatorio",
            "base de conhecimento",
            "base documental",
            "componentes do drone",
            "drone proprio",
            "especificações do drone",
            "especificacoes do drone",
        ]
    ):
        return _resposta_base_conhecimento(texto_lower), {"tipo": "base_conhecimento"}

    if any(palavra in texto_lower for palavra in ["alerta", "alertas", "problema", "problemas", "risco", "riscos"]):
        return _resposta_alertas(resumo), {"tipo": "alertas", "resumo": resumo}

    if any(palavra in texto_lower for palavra in ["despesa", "despesas", "gasto", "gastos", "contabilidade", "financeiro", "custos"]):
        return _resposta_financeira(empresa=empresa, resumo=resumo, texto=texto_lower), {"tipo": "financeiro", "resumo": resumo}

    if any(palavra in texto_lower for palavra in ["furo", "furos", "metros", "perfuração", "perfuracao", "medição", "medições", "medicoes"]):
        return _resposta_furos(empresa=empresa, resumo=resumo, texto=texto), {"tipo": "furos", "resumo": resumo}

    if any(palavra in texto_lower for palavra in ["empregado", "empregados", "trabalhador", "trabalhadores", "equipa", "equipe"]):
        return _resposta_empregados(resumo), {"tipo": "empregados", "resumo": resumo}

    if any(palavra in texto_lower for palavra in ["máquina", "maquina", "máquinas", "maquinas", "equipamento", "equipamentos"]):
        return _resposta_maquinas(resumo), {"tipo": "maquinas", "resumo": resumo}

    if any(palavra in texto_lower for palavra in ["material", "materiais", "stock", "estoque", "levantamento", "devolução", "devolucao"]):
        return _resposta_materiais(resumo), {"tipo": "materiais", "resumo": resumo}

    if any(palavra in texto_lower for palavra in ["evento", "eventos", "alteração", "alteracoes", "alteração", "analytics"]):
        return _resposta_eventos(empresa), {"tipo": "eventos"}

    return _resposta_geral(resumo), {"tipo": "geral", "resumo": resumo}


def construir_resumo_empresa(empresa):
    projetos_qs = Projeto.objects.filter(empresa=empresa)
    furos_qs = Furo.objects.filter(empresa=empresa)
    empregados_qs = Empregados.objects.filter(empresa=empresa)
    maquinas_qs = Maquina.objects.filter(empresa=empresa)
    materiais_qs = Material.objects.filter(empresa=empresa)
    despesas_qs = Despesa.objects.filter(empresa=empresa)

    materiais_baixo_stock = list(
        materiais_qs.filter(quantidade__lte=0).values_list("nome", flat=True)[:5]
    ) + list(
        materiais_qs.extra(where=["quantidade <= stock_minimo"]).values_list("nome", flat=True)[:5]
    )
    materiais_baixo_stock = list(dict.fromkeys(materiais_baixo_stock))

    maquinas_alerta = list(
        maquinas_qs.exclude(estado="operacional").values("nome", "estado")[:8]
    )
    furos_ativos = furos_qs.filter(estado="ativo")
    furos_concluidos = furos_qs.filter(estado="concluido")

    total_despesas = despesas_qs.aggregate(total=Sum("valor")).get("total") or 0
    categorias = list(
        despesas_qs.values("categoria").annotate(total=Sum("valor")).order_by("-total")[:5]
    )
    eventos_recentes = list(
        EventoAnalytics.objects.filter(empresa=empresa)
        .values("entidade_tipo", "tipo_evento", "entidade_label", "criado_em")
        .order_by("-criado_em")[:5]
    )

    return {
        "total_projetos": projetos_qs.count(),
        "total_furos": furos_qs.count(),
        "furos_ativos": furos_ativos.count(),
        "furos_concluidos": furos_concluidos.count(),
        "total_metros_furados": round(sum(furos_qs.values_list("metros_furados", flat=True)), 2),
        "total_medicoes": Medicao.objects.filter(empresa=empresa).count(),
        "total_registos": RegistoDiarioEmpregado.objects.filter(empresa=empresa).count(),
        "total_empregados": empregados_qs.count(),
        "empregados_pendentes": empregados_qs.filter(aprovado=False).count(),
        "total_maquinas": maquinas_qs.count(),
        "total_materiais": materiais_qs.count(),
        "materiais_baixo_stock": materiais_baixo_stock,
        "maquinas_alerta": maquinas_alerta,
        "total_despesas": float(total_despesas),
        "despesas_top_categorias": categorias,
        "eventos_recentes": eventos_recentes,
        "furos_ativos_lista": list(
            furos_ativos.values("nome", "projeto__nome", "profundidade_atual", "profundidade_alvo_atual")[:8]
        ),
        "furos_concluidos_lista": list(
            furos_concluidos.values("nome", "projeto__nome", "profundidade_maxima_atingida")[:8]
        ),
        "maquinas_estados": list(
            maquinas_qs.values("estado").annotate(total=Count("id")).order_by("estado")
        ),
    }


def normalizar_json_chat(valor):
    if valor is None or isinstance(valor, (str, int, float, bool)):
        return valor
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (datetime, date, time)):
        return valor.isoformat()
    if isinstance(valor, dict):
        return {str(chave): normalizar_json_chat(item) for chave, item in valor.items()}
    if isinstance(valor, (list, tuple, set)):
        return [normalizar_json_chat(item) for item in valor]
    return str(valor)


def _listar_documentos_base_conhecimento():
    if not KNOWLEDGE_BASE_ROOT.exists():
        return []
    documentos = []
    for path in sorted(KNOWLEDGE_BASE_ROOT.rglob("*")):
        if not path.is_file():
            continue
        documentos.append(
            {
                "nome": path.name,
                "relativo": str(path.relative_to(KNOWLEDGE_BASE_ROOT)),
                "extensao": path.suffix.lower(),
                "path": path,
            }
        )
    return documentos


def _ler_documento_texto(relativo):
    path = KNOWLEDGE_BASE_ROOT / relativo
    if not path.exists() or not path.is_file():
        return ""
    if path.suffix.lower() not in {".md", ".txt", ".json"}:
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _resposta_base_conhecimento(texto):
    documentos = _listar_documentos_base_conhecimento()
    if not documentos:
        return "Ainda não existe base de conhecimento disponível para consulta."

    linhas = [
        "Tenho acesso à base documental do projeto.",
        "Documentos disponíveis:",
    ]
    for doc in documentos[:12]:
        linhas.append(f"- {doc['relativo']}")

    if any(palavra in texto for palavra in ["drone", "componentes", "especificações", "especificacoes"]):
        conteudo = _ler_documento_texto("drone/drone_proprio_componentes.md")
        if conteudo:
            resumo = []
            for raw_line in conteudo.splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                resumo.append(line)
                if len(resumo) >= 10:
                    break
            if resumo:
                linhas.extend(
                    [
                        "",
                        "Resumo rápido do documento de drone próprio:",
                        *[f"- {item}" for item in resumo],
                    ]
                )

    linhas.extend(
        [
            "",
            "Podes pedir, por exemplo:",
            "- 'resume o documento do drone próprio'",
            "- 'que sensores deve ter o drone?'",
            "- 'que documentos existem na base de conhecimento?'",
        ]
    )
    return "\n".join(linhas)


def _resposta_capacidades(resumo):
    return (
        "Posso ajudar em quatro frentes principais:\n"
        f"1. Operação: ler projetos, furos, medições, registos e eventos da empresa. Hoje tens {resumo['furos_ativos']} furos ativos e {resumo['furos_concluidos']} concluídos.\n"
        f"2. Recursos: consultar empregados, máquinas, materiais e alertas. Tens {resumo['total_empregados']} empregados e {resumo['total_maquinas']} máquinas registadas.\n"
        "3. Financeiro: resumir despesas, custos e margens com base no que está na base de dados.\n"
        "4. Cálculo: resolver expressões matemáticas e apoiar contas técnicas.\n\n"
        "Exemplos:\n"
        "- 'quais são os alertas atuais?'\n"
        "- 'quanto já gastámos em despesas?'\n"
        "- 'que furos estão em curso?'\n"
        "- 'calcula (125.4 * 3.8) / 12'"
    )


def _resposta_alertas(resumo):
    partes = []
    if resumo["materiais_baixo_stock"]:
        partes.append("Materiais com stock baixo ou esgotado: " + ", ".join(resumo["materiais_baixo_stock"][:8]) + ".")
    if resumo["maquinas_alerta"]:
        partes.append(
            "Máquinas em alerta: "
            + ", ".join(f"{item['nome']} ({item['estado']})" for item in resumo["maquinas_alerta"][:8])
            + "."
        )
    if resumo["empregados_pendentes"]:
        partes.append(f"Empregados pendentes de aprovação: {resumo['empregados_pendentes']}.")
    if not partes:
        partes.append("Não encontrei alertas relevantes neste momento para stock, máquinas ou aprovação de empregados.")
    return "\n".join(partes)


def _resposta_financeira(*, empresa, resumo, texto):
    resposta = [f"Despesa total registada: {resumo['total_despesas']:.2f} €."]
    if resumo["despesas_top_categorias"]:
        resposta.append(
            "Categorias com maior peso: "
            + ", ".join(
                f"{item['categoria']}: {float(item['total'] or 0):.2f} €" for item in resumo["despesas_top_categorias"]
            )
            + "."
        )

    nome_furo = _detetar_nome_entidade(texto, Furo.objects.filter(empresa=empresa).values_list("nome", flat=True))
    if nome_furo:
        furo = Furo.objects.filter(empresa=empresa, nome__iexact=nome_furo).first()
        if furo:
            total_furo = float(Despesa.objects.filter(empresa=empresa, furo=furo).aggregate(total=Sum("valor")).get("total") or 0)
            resposta.append(f"No furo {furo.nome}, a despesa direta registada é {total_furo:.2f} €.")

    return "\n".join(resposta)


def _resposta_furos(*, empresa, resumo, texto):
    resposta = [
        f"Furos ativos: {resumo['furos_ativos']}.",
        f"Furos concluídos: {resumo['furos_concluidos']}.",
        f"Metros furados acumulados: {resumo['total_metros_furados']:.2f} m.",
        f"Medições registadas: {resumo['total_medicoes']}.",
    ]
    nome_furo = _detetar_nome_entidade(texto.lower(), [nome.lower() for nome in Furo.objects.filter(empresa=empresa).values_list("nome", flat=True)])
    if nome_furo:
        furo = Furo.objects.filter(empresa=empresa, nome__iexact=nome_furo).first()
        if furo:
            resposta.append(
                f"Detalhe de {furo.nome}: profundidade atual {furo.profundidade_atual:.2f} m, alvo atual {furo.profundidade_alvo_atual:.2f} m, estado {furo.get_estado_display()}."
            )
    elif resumo["furos_ativos_lista"]:
        resposta.append(
            "Furos em curso: "
            + ", ".join(
                f"{item['nome']} ({item['profundidade_atual']:.1f}/{item['profundidade_alvo_atual']:.1f} m)"
                for item in resumo["furos_ativos_lista"][:5]
            )
            + "."
        )
    return "\n".join(resposta)


def _resposta_empregados(resumo):
    return (
        f"Total de empregados: {resumo['total_empregados']}.\n"
        f"Pendentes de aprovação: {resumo['empregados_pendentes']}.\n"
        f"Registos diários guardados: {resumo['total_registos']}."
    )


def _resposta_maquinas(resumo):
    linhas = [f"Total de máquinas: {resumo['total_maquinas']}."]
    if resumo["maquinas_estados"]:
        linhas.append(
            "Estados atuais: "
            + ", ".join(f"{item['estado']}: {item['total']}" for item in resumo["maquinas_estados"])
            + "."
        )
    if resumo["maquinas_alerta"]:
        linhas.append(
            "Máquinas não operacionais: "
            + ", ".join(f"{item['nome']} ({item['estado']})" for item in resumo["maquinas_alerta"][:8])
            + "."
        )
    return "\n".join(linhas)


def _resposta_materiais(resumo):
    linhas = [f"Total de materiais registados: {resumo['total_materiais']}."]
    if resumo["materiais_baixo_stock"]:
        linhas.append("Itens em alerta de stock: " + ", ".join(resumo["materiais_baixo_stock"][:8]) + ".")
    else:
        linhas.append("Não encontrei materiais em stock baixo neste momento.")
    return "\n".join(linhas)


def _resposta_eventos(empresa):
    eventos = EventoAnalytics.objects.filter(empresa=empresa).order_by("-criado_em")[:8]
    if not eventos:
        return "Ainda não existem eventos analytics registados para esta empresa."
    return "Eventos recentes:\n" + "\n".join(
        f"- {evento.entidade_tipo} {evento.get_tipo_evento_display().lower()} · {evento.entidade_label or evento.entidade_id}"
        for evento in eventos
    )


def _resposta_geral(resumo):
    return (
        f"Resumo rápido da empresa: {resumo['total_projetos']} projetos, {resumo['total_furos']} furos, "
        f"{resumo['total_empregados']} empregados, {resumo['total_maquinas']} máquinas, {resumo['total_materiais']} materiais e "
        f"{resumo['total_despesas']:.2f} € em despesas registadas.\n\n"
        "Posso aprofundar um tema específico se perguntares por furos, despesas, alertas, materiais, máquinas, empregados ou eventos."
    )


def _parece_calculo(texto):
    return texto.startswith("calcula") or bool(re.fullmatch(r"[\d\s\.\,\+\-\*\/\(\)\%\^a-zA-Z_]+", texto))


def _avaliar_expressao_segura(texto):
    expr = texto.lower().replace("calcula", "").strip().replace("^", "**").replace(",", ".")
    if not expr:
        return None
    try:
        node = ast.parse(expr, mode="eval")
        valor = _eval_node(node.body)
        if isinstance(valor, float):
            return round(valor, 6)
        return valor
    except Exception:
        return None


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in SAFE_BIN_OPS:
        return SAFE_BIN_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in SAFE_UNARY_OPS:
        return SAFE_UNARY_OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in SAFE_FUNCTIONS:
        func = SAFE_FUNCTIONS[node.func.id]
        args = [_eval_node(arg) for arg in node.args]
        return func(*args)
    if isinstance(node, ast.Name) and node.id in {"pi", "e"}:
        return SAFE_FUNCTIONS[node.id]()
    raise ValueError("Expressão não suportada")


def _detetar_nome_entidade(texto, nomes):
    texto_norm = texto.lower()
    for nome in nomes:
        if nome.lower() in texto_norm:
            return nome
    return None
