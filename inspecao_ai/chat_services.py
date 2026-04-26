import ast
import math
import operator
import re
from pathlib import Path
from datetime import date, datetime, time
from decimal import Decimal

from inspecao_ai.selectors.chat import (
    contar_medicoes_empresa,
    contar_registos_empresa,
    listar_candidatos_furos_relacionados,
    listar_despesas_top_categorias,
    listar_eventos_empresa,
    listar_eventos_recentes_values,
    listar_furos_memoria_empresa,
    listar_maquinas_alerta,
    listar_maquinas_estados,
    listar_materiais_baixo_stock,
    listar_nomes_furos_empresa,
    obter_despesas_empresa_qs,
    obter_empregados_empresa_qs,
    obter_furo_empresa_por_nome,
    obter_furos_empresa_qs,
    obter_maquinas_empresa_qs,
    obter_materiais_empresa_qs,
    obter_projetos_empresa_qs,
    obter_total_despesas_empresa,
    obter_total_despesas_furo,
)


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
FURO_MEMORY_RADIUS_KM = 0.35
EXTENSOES_TEXTO_DIRETO = {
    ".md",
    ".txt",
    ".json",
    ".csv",
    ".log",
    ".ini",
    ".cfg",
    ".yaml",
    ".yml",
    ".xml",
    ".html",
    ".htm",
}

PROMPT_APROFUNDAR_TEMA = "Quero aprofundar um tema."


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
                {"tipo": "calculo", "sugestoes": _sugestoes_por_tipo("calculo")},
            )

    if any(palavra in texto_lower for palavra in ["funciona a plataforma", "como funciona", "o que podes fazer", "ajuda", "ajudar"]):
        return _resposta_capacidades(resumo), {
            "tipo": "ajuda",
            "sugestoes": _sugestoes_por_tipo("ajuda"),
        }

    if any(
        palavra in texto_lower
        for palavra in [
            "aprofundar um tema",
            "aprofundar tema",
            "explorar temas",
            "menu de temas",
            "temas disponíveis",
            "temas disponiveis",
            "mostrar temas",
        ]
    ):
        return _resposta_menu_temas(), {
            "tipo": "menu_temas",
            "sugestoes": _sugestoes_menu_temas(),
        }

    if any(
        palavra in texto_lower
        for palavra in [
            "já houve um furo",
            "ja houve um furo",
            "nesta zona",
            "nessa zona",
            "neste local",
            "nesse local",
            "perto daqui",
            "perto desta zona",
            "histórico da zona",
            "historico da zona",
            "zona do furo",
        ]
    ):
        return _resposta_memoria_zona(empresa=empresa, texto=texto), {
            "tipo": "memoria_zona",
            "resumo": resumo,
            "sugestoes": _sugestoes_por_tipo("memoria_zona"),
        }

    if any(palavra in texto_lower for palavra in ["furos ativos", "ativos dos furos"]):
        return _resposta_furos_ativos(resumo), {
            "tipo": "furos_ativos",
            "resumo": resumo,
            "sugestoes": _sugestoes_por_tipo("furos_ativos"),
        }

    if any(palavra in texto_lower for palavra in ["furos concluídos", "furos concluidos", "concluídos dos furos", "concluidos dos furos"]):
        return _resposta_furos_concluidos(resumo), {
            "tipo": "furos_concluidos",
            "resumo": resumo,
            "sugestoes": _sugestoes_por_tipo("furos_concluidos"),
        }

    if any(palavra in texto_lower for palavra in ["resumo de medições", "resumo de medicoes", "medições dos furos", "medicoes dos furos"]):
        return _resposta_furos_medicoes(resumo), {
            "tipo": "furos_medicoes",
            "resumo": resumo,
            "sugestoes": _sugestoes_por_tipo("furos_medicoes"),
        }

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
            "plataforma",
            "features",
            "permissoes",
            "permissões",
            "go live",
            "online",
            "deploy",
        ]
    ):
        return _resposta_base_conhecimento(texto_lower), {
            "tipo": "base_conhecimento",
            "sugestoes": _sugestoes_por_tipo("base_conhecimento"),
        }

    if any(palavra in texto_lower for palavra in ["estados das máquinas", "estados das maquinas", "estado das máquinas", "estado das maquinas"]):
        return _resposta_maquinas_estados(resumo), {
            "tipo": "maquinas_estados",
            "resumo": resumo,
            "sugestoes": _sugestoes_por_tipo("maquinas_estados"),
        }

    if any(palavra in texto_lower for palavra in ["máquinas em alerta", "maquinas em alerta", "máquinas não operacionais", "maquinas nao operacionais"]):
        return _resposta_maquinas_alerta(resumo), {
            "tipo": "maquinas_alerta",
            "resumo": resumo,
            "sugestoes": _sugestoes_por_tipo("maquinas_alerta"),
        }

    if any(palavra in texto_lower for palavra in ["alerta", "alertas", "problema", "problemas", "risco", "riscos"]):
        return _resposta_alertas(resumo), {
            "tipo": "alertas",
            "resumo": resumo,
            "sugestoes": _sugestoes_por_tipo("alertas"),
        }

    if any(palavra in texto_lower for palavra in ["materiais com stock baixo", "stock baixo de materiais", "stock crítico", "stock critico"]):
        return _resposta_materiais_stock_baixo(resumo), {
            "tipo": "materiais_stock",
            "resumo": resumo,
            "sugestoes": _sugestoes_por_tipo("materiais_stock"),
        }

    if any(palavra in texto_lower for palavra in ["resumo de levantamentos", "levantamentos de materiais"]):
        return _resposta_materiais_levantamentos(resumo), {
            "tipo": "materiais_levantamentos",
            "resumo": resumo,
            "sugestoes": _sugestoes_por_tipo("materiais_levantamentos"),
        }

    if any(palavra in texto_lower for palavra in ["resumo de devoluções", "resumo de devolucoes", "devoluções de materiais", "devolucoes de materiais"]):
        return _resposta_materiais_devolucoes(resumo), {
            "tipo": "materiais_devolucoes",
            "resumo": resumo,
            "sugestoes": _sugestoes_por_tipo("materiais_devolucoes"),
        }

    if any(palavra in texto_lower for palavra in ["categorias de despesa", "top categorias de despesa"]):
        return _resposta_financeira_categorias(resumo), {
            "tipo": "financeiro_categorias",
            "resumo": resumo,
            "sugestoes": _sugestoes_por_tipo("financeiro_categorias"),
        }

    if any(palavra in texto_lower for palavra in ["despesa por furo", "despesas por furo"]):
        return _resposta_financeira_furo(resumo), {
            "tipo": "financeiro_furo",
            "resumo": resumo,
            "sugestoes": _sugestoes_por_tipo("financeiro_furo"),
        }

    if any(palavra in texto_lower for palavra in ["despesa", "despesas", "gasto", "gastos", "contabilidade", "financeiro", "custos"]):
        return _resposta_financeira(empresa=empresa, resumo=resumo, texto=texto_lower), {
            "tipo": "financeiro",
            "resumo": resumo,
            "sugestoes": _sugestoes_por_tipo("financeiro"),
        }

    if any(palavra in texto_lower for palavra in ["furo", "furos", "metros", "perfuração", "perfuracao", "medição", "medições", "medicoes"]):
        return _resposta_furos(empresa=empresa, resumo=resumo, texto=texto), {
            "tipo": "furos",
            "resumo": resumo,
            "sugestoes": _sugestoes_por_tipo("furos"),
        }

    if any(palavra in texto_lower for palavra in ["resumo de empregados", "total de empregados"]):
        return _resposta_empregados_total(resumo), {
            "tipo": "empregados_total",
            "resumo": resumo,
            "sugestoes": _sugestoes_por_tipo("empregados_total"),
        }

    if any(palavra in texto_lower for palavra in ["empregados pendentes", "pendentes de empregados", "pendentes"]):
        return _resposta_empregados_pendentes(resumo), {
            "tipo": "empregados_pendentes",
            "resumo": resumo,
            "sugestoes": _sugestoes_por_tipo("empregados_pendentes"),
        }

    if any(palavra in texto_lower for palavra in ["registos de empregados", "registos diários de empregados", "registos diarios de empregados"]):
        return _resposta_empregados_registos(resumo), {
            "tipo": "empregados_registos",
            "resumo": resumo,
            "sugestoes": _sugestoes_por_tipo("empregados_registos"),
        }

    if any(palavra in texto_lower for palavra in ["empregado", "empregados", "trabalhador", "trabalhadores", "equipa", "equipe"]):
        return _resposta_empregados(resumo), {
            "tipo": "empregados",
            "resumo": resumo,
            "sugestoes": _sugestoes_por_tipo("empregados"),
        }

    if any(palavra in texto_lower for palavra in ["máquina", "maquina", "máquinas", "maquinas", "equipamento", "equipamentos"]):
        return _resposta_maquinas(resumo), {
            "tipo": "maquinas",
            "resumo": resumo,
            "sugestoes": _sugestoes_por_tipo("maquinas"),
        }

    if any(palavra in texto_lower for palavra in ["material", "materiais", "stock", "estoque", "levantamento", "devolução", "devolucao"]):
        return _resposta_materiais(resumo), {
            "tipo": "materiais",
            "resumo": resumo,
            "sugestoes": _sugestoes_por_tipo("materiais"),
        }

    if any(palavra in texto_lower for palavra in ["evento", "eventos", "alteração", "alteracoes", "alteração", "analytics"]):
        return _resposta_eventos(empresa), {
            "tipo": "eventos",
            "sugestoes": _sugestoes_por_tipo("eventos"),
        }

    return _resposta_geral(resumo), {
        "tipo": "geral",
        "resumo": resumo,
        "sugestoes": _sugestoes_por_tipo("geral"),
    }


def construir_resumo_empresa(empresa):
    projetos_qs = obter_projetos_empresa_qs(empresa)
    furos_qs = obter_furos_empresa_qs(empresa)
    empregados_qs = obter_empregados_empresa_qs(empresa)
    maquinas_qs = obter_maquinas_empresa_qs(empresa)
    materiais_qs = obter_materiais_empresa_qs(empresa)
    despesas_qs = obter_despesas_empresa_qs(empresa)

    materiais_baixo_stock = listar_materiais_baixo_stock(materiais_qs, limit=5)
    maquinas_alerta = listar_maquinas_alerta(maquinas_qs, limit=8)
    furos_ativos = furos_qs.filter(estado="ativo")
    furos_concluidos = furos_qs.filter(estado="concluido")

    total_despesas = obter_total_despesas_empresa(despesas_qs)
    categorias = listar_despesas_top_categorias(despesas_qs, limit=5)
    eventos_recentes = listar_eventos_recentes_values(empresa, limit=5)

    return {
        "total_projetos": projetos_qs.count(),
        "total_furos": furos_qs.count(),
        "furos_ativos": furos_ativos.count(),
        "furos_concluidos": furos_concluidos.count(),
        "total_metros_furados": round(sum(furos_qs.values_list("metros_furados", flat=True)), 2),
        "total_medicoes": contar_medicoes_empresa(empresa),
        "total_registos": contar_registos_empresa(empresa),
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
        "maquinas_estados": listar_maquinas_estados(maquinas_qs),
        "memoria_furos": _construir_memoria_furos_empresa(empresa, limite=12),
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
    if path.suffix.lower() not in EXTENSOES_TEXTO_DIRETO:
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _ler_conteudo_consultavel_documento(relativo):
    path = KNOWLEDGE_BASE_ROOT / relativo
    if not path.exists() or not path.is_file():
        return ""

    extensao = path.suffix.lower()
    if extensao in EXTENSOES_TEXTO_DIRETO:
        return path.read_text(encoding="utf-8", errors="ignore")

    sidecar_txt = path.with_suffix(".txt")
    if sidecar_txt.exists() and sidecar_txt.is_file():
        return sidecar_txt.read_text(encoding="utf-8", errors="ignore")

    return ""


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

    docs_pdf = [doc for doc in documentos if doc["extensao"] == ".pdf"]
    docs_biblioteca = [doc for doc in documentos if doc["relativo"].startswith("pdf/")]
    if docs_pdf:
        linhas.extend(
            [
                "",
                "PDFs encontrados na base documental:",
                *[f"- {doc['relativo']}" for doc in docs_pdf[:12]],
            ]
        )
    if docs_biblioteca:
        linhas.extend(
            [
                "",
                "Outros documentos encontrados na biblioteca documental:",
                *[
                    f"- {doc['relativo']}"
                    for doc in docs_biblioteca[:12]
                    if doc["extensao"] != ".pdf"
                ],
            ]
        )

    if any(palavra in texto for palavra in ["drone", "componentes", "especificações", "especificacoes"]):
        conteudo = _ler_conteudo_consultavel_documento("drone/drone_proprio_componentes.md")
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

    if any(
        palavra in texto
        for palavra in [
            "plataforma",
            "features",
            "permissoes",
            "permissões",
            "go live",
            "online",
            "deploy",
        ]
    ):
        conteudo_plataforma = _ler_conteudo_consultavel_documento("plataforma/plataforma_base_funcional.md")
        conteudo_go_live = _ler_conteudo_consultavel_documento("plataforma/plataforma_go_live_checklist.md")
        if conteudo_plataforma:
            resumo_plataforma = []
            for raw_line in conteudo_plataforma.splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                resumo_plataforma.append(line)
                if len(resumo_plataforma) >= 10:
                    break
            if resumo_plataforma:
                linhas.extend(
                    [
                        "",
                        "Resumo rápido da base funcional da plataforma:",
                        *[f"- {item}" for item in resumo_plataforma],
                    ]
                )
        if conteudo_go_live:
            resumo_go_live = []
            for raw_line in conteudo_go_live.splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                resumo_go_live.append(line)
                if len(resumo_go_live) >= 8:
                    break
            if resumo_go_live:
                linhas.extend(
                    [
                        "",
                        "Checklist base para colocar a plataforma online:",
                        *[f"- {item}" for item in resumo_go_live],
                    ]
                )

    if any(palavra in texto for palavra in ["pdf", "ficheiro", "arquivo", "documento"]):
        linhas.extend(
            [
                "",
                "Como a AI consulta documentos nesta base:",
                "- formatos textuais como `.md`, `.txt`, `.json`, `.csv`, `.log`, `.yaml`, `.yml`, `.xml`, `.html`, `.ini` e `.cfg` podem ser lidos diretamente",
                "- PDFs e outros formatos não textuais podem ser usados com um `.txt` auxiliar com o mesmo nome",
                "- exemplo: `manual_operacao.pdf` + `manual_operacao.txt`",
                "- para leitura profunda de formatos não textuais, este é o fluxo recomendado neste ambiente",
            ]
        )

    linhas.extend(
        [
            "",
            "Podes pedir, por exemplo:",
            "- 'resume o documento do drone próprio'",
            "- 'resume a base funcional da plataforma'",
            "- 'o que falta para colocar a plataforma online?'",
            "- 'que PDFs existem na base de conhecimento?'",
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
        "4. Cálculo: resolver expressões matemáticas e apoiar contas técnicas.\n"
        "5. Memória operacional: lembrar furos anteriores da mesma zona e resumir o que aconteceu nesses trabalhos.\n\n"
        "Exemplos:\n"
        "- 'quais são os alertas atuais?'\n"
        "- 'quanto já gastámos em despesas?'\n"
        "- 'que furos estão em curso?'\n"
        "- 'já houve um furo nesta zona?'\n"
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

    nome_furo = _detetar_nome_entidade(texto, listar_nomes_furos_empresa(empresa))
    if nome_furo:
        furo = obter_furo_empresa_por_nome(empresa, nome_furo)
        if furo:
            total_furo = obter_total_despesas_furo(furo)
            resposta.append(f"No furo {furo.nome}, a despesa direta registada é {total_furo:.2f} €.")

    return "\n".join(resposta)


def _resposta_financeira_categorias(resumo):
    if not resumo["despesas_top_categorias"]:
        return "Ainda não existem categorias de despesa suficientes para resumir."
    return "Top categorias de despesa:\n" + "\n".join(
        f"- {item['categoria']}: {float(item['total'] or 0):.2f} €" for item in resumo["despesas_top_categorias"]
    )


def _resposta_financeira_furo(resumo):
    if not resumo["furos_ativos_lista"]:
        return "Não encontrei furos ativos para cruzar com despesa por furo."
    linhas = [
        "Para despesa por furo com valor exato, indica o nome do furo (ex.: 'despesa por furo Furo-12').",
        "Furos ativos disponíveis para consulta rápida:",
    ]
    linhas.extend(f"- {item['nome']} · {item['projeto__nome']}" for item in resumo["furos_ativos_lista"][:8])
    return "\n".join(linhas)


def _resposta_furos(*, empresa, resumo, texto):
    resposta = [
        f"Furos ativos: {resumo['furos_ativos']}.",
        f"Furos concluídos: {resumo['furos_concluidos']}.",
        f"Metros furados acumulados: {resumo['total_metros_furados']:.2f} m.",
        f"Medições registadas: {resumo['total_medicoes']}.",
    ]
    nomes_furos = listar_nomes_furos_empresa(empresa)
    nome_furo = _detetar_nome_entidade(texto.lower(), [nome.lower() for nome in nomes_furos])
    if nome_furo:
        furo = obter_furo_empresa_por_nome(empresa, nome_furo)
        if furo:
            resposta.append(
                f"Detalhe de {furo.nome}: profundidade atual {furo.profundidade_atual:.2f} m, alvo atual {furo.profundidade_alvo_atual:.2f} m, estado {furo.get_estado_display()}."
            )
            memoria = _resumir_memoria_furo(furo)
            if memoria:
                resposta.append("")
                resposta.append("Memória operacional deste furo:")
                resposta.extend(f"- {linha}" for linha in memoria)
            proximos = _obter_furos_relacionados(empresa, furo)
            if proximos:
                resposta.append("")
                resposta.append("Furos relacionados na mesma zona:")
                resposta.extend(f"- {linha}" for linha in proximos[:5])
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


def _resposta_furos_ativos(resumo):
    linhas = [f"Furos ativos no momento: {resumo['furos_ativos']}."]
    if resumo["furos_ativos_lista"]:
        linhas.append("Lista rápida dos furos em curso:")
        linhas.extend(
            f"- {item['nome']} · {item['projeto__nome']} · {float(item['profundidade_atual'] or 0):.1f}/{float(item['profundidade_alvo_atual'] or 0):.1f} m"
            for item in resumo["furos_ativos_lista"][:8]
        )
    else:
        linhas.append("Não encontrei furos ativos listados neste momento.")
    return "\n".join(linhas)


def _resposta_furos_concluidos(resumo):
    linhas = [f"Furos concluídos: {resumo['furos_concluidos']}."]
    if resumo["furos_concluidos_lista"]:
        linhas.append("Últimos furos concluídos registados:")
        linhas.extend(
            f"- {item['nome']} · {item['projeto__nome']} · profundidade máxima {float(item['profundidade_maxima_atingida'] or 0):.1f} m"
            for item in resumo["furos_concluidos_lista"][:8]
        )
    else:
        linhas.append("Ainda não encontrei furos concluídos para listar.")
    return "\n".join(linhas)


def _resposta_furos_medicoes(resumo):
    return (
        f"Resumo de medições dos furos:\n"
        f"- Total de medições: {resumo['total_medicoes']}\n"
        f"- Total de registos diários: {resumo['total_registos']}\n"
        f"- Metros furados acumulados: {resumo['total_metros_furados']:.2f} m"
    )


def _resposta_empregados(resumo):
    return (
        f"Total de empregados: {resumo['total_empregados']}.\n"
        f"Pendentes de aprovação: {resumo['empregados_pendentes']}.\n"
        f"Registos diários guardados: {resumo['total_registos']}."
    )


def _resposta_empregados_total(resumo):
    return f"Total de empregados registados: {resumo['total_empregados']}."


def _resposta_empregados_pendentes(resumo):
    return f"Empregados pendentes de aprovação: {resumo['empregados_pendentes']}."


def _resposta_empregados_registos(resumo):
    return (
        "Resumo de atividade dos empregados:\n"
        f"- Registos diários guardados: {resumo['total_registos']}\n"
        f"- Empregados registados: {resumo['total_empregados']}"
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


def _resposta_maquinas_estados(resumo):
    linhas = ["Estados atuais das máquinas:"]
    if resumo["maquinas_estados"]:
        linhas.extend(f"- {item['estado']}: {item['total']}" for item in resumo["maquinas_estados"])
    else:
        linhas.append("- Sem estados registados.")
    return "\n".join(linhas)


def _resposta_maquinas_alerta(resumo):
    if not resumo["maquinas_alerta"]:
        return "Neste momento não encontrei máquinas em alerta."
    return "Máquinas em alerta:\n" + "\n".join(
        f"- {item['nome']} ({item['estado']})" for item in resumo["maquinas_alerta"][:10]
    )


def _resposta_materiais(resumo):
    linhas = [f"Total de materiais registados: {resumo['total_materiais']}."]
    if resumo["materiais_baixo_stock"]:
        linhas.append("Itens em alerta de stock: " + ", ".join(resumo["materiais_baixo_stock"][:8]) + ".")
    else:
        linhas.append("Não encontrei materiais em stock baixo neste momento.")
    return "\n".join(linhas)


def _resposta_materiais_stock_baixo(resumo):
    if resumo["materiais_baixo_stock"]:
        return "Materiais com stock baixo ou esgotado:\n" + "\n".join(
            f"- {item}" for item in resumo["materiais_baixo_stock"][:12]
        )
    return "Não encontrei materiais com stock baixo neste momento."


def _resposta_materiais_levantamentos(resumo):
    return (
        "Posso analisar levantamentos por período/projeto/furo.\n"
        "Para detalhar, clica em Furos ou indica um furo/projeto específico para cruzar com materiais."
    )


def _resposta_materiais_devolucoes(resumo):
    return (
        "Posso analisar devoluções por período/projeto/furo.\n"
        "Para detalhar, clica em Furos ou indica um furo/projeto específico para cruzar com materiais."
    )


def _resposta_eventos(empresa):
    eventos = listar_eventos_empresa(empresa, limit=8)
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
        "Posso aprofundar um tema específico. Clica em “Aprofundar um tema” para abrir opções com links clicáveis."
    )


def _resposta_menu_temas():
    return (
        "Escolhe um tema para aprofundar. Depois posso continuar com novas opções e respostas relacionadas."
    )


def _sugestao(label, prompt):
    return {"label": label, "prompt": prompt}


def _sugestoes_menu_temas():
    return [
        _sugestao("Furos", "Quero aprofundar furos."),
        _sugestao("Despesas", "Quero aprofundar despesas."),
        _sugestao("Alertas", "Quero aprofundar alertas."),
        _sugestao("Materiais", "Quero aprofundar materiais."),
        _sugestao("Máquinas", "Quero aprofundar máquinas."),
        _sugestao("Empregados", "Quero aprofundar empregados."),
        _sugestao("Eventos", "Quero aprofundar eventos."),
        _sugestao("Histórico por zona", "Quero histórico de furos por zona."),
    ]


def _sugestoes_por_tipo(tipo):
    if tipo in {"geral", "ajuda"}:
        return [_sugestao("Aprofundar um tema", PROMPT_APROFUNDAR_TEMA)]

    if tipo == "menu_temas":
        return _sugestoes_menu_temas()

    if tipo == "furos":
        return [
            _sugestao("Furos ativos", "Mostra os furos ativos."),
            _sugestao("Furos concluídos", "Mostra os furos concluídos."),
            _sugestao("Resumo de medições", "Quero resumo de medições dos furos."),
            _sugestao("Histórico por zona", "Quero histórico de furos por zona."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "furos_ativos":
        return [
            _sugestao("Furos concluídos", "Mostra os furos concluídos."),
            _sugestao("Resumo de medições", "Quero resumo de medições dos furos."),
            _sugestao("Histórico por zona", "Quero histórico de furos por zona."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "furos_concluidos":
        return [
            _sugestao("Furos ativos", "Mostra os furos ativos."),
            _sugestao("Resumo de medições", "Quero resumo de medições dos furos."),
            _sugestao("Histórico por zona", "Quero histórico de furos por zona."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "furos_medicoes":
        return [
            _sugestao("Furos ativos", "Mostra os furos ativos."),
            _sugestao("Furos concluídos", "Mostra os furos concluídos."),
            _sugestao("Histórico por zona", "Quero histórico de furos por zona."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "financeiro":
        return [
            _sugestao("Top categorias", "Mostra as categorias de despesa com maior peso."),
            _sugestao("Despesa por furo", "Quero despesa por furo."),
            _sugestao("Alertas", "Quero os alertas atuais."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "financeiro_categorias":
        return [
            _sugestao("Despesa por furo", "Quero despesa por furo."),
            _sugestao("Alertas", "Quero os alertas atuais."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "financeiro_furo":
        return [
            _sugestao("Top categorias", "Mostra as categorias de despesa com maior peso."),
            _sugestao("Alertas", "Quero os alertas atuais."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "alertas":
        return [
            _sugestao("Stock baixo", "Mostra materiais com stock baixo."),
            _sugestao("Máquinas em alerta", "Mostra máquinas em alerta."),
            _sugestao("Empregados pendentes", "Mostra empregados pendentes."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "materiais":
        return [
            _sugestao("Stock baixo", "Mostra materiais com stock baixo."),
            _sugestao("Levantamentos", "Quero resumo de levantamentos de materiais."),
            _sugestao("Devoluções", "Quero resumo de devoluções de materiais."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "materiais_stock":
        return [
            _sugestao("Levantamentos", "Quero resumo de levantamentos de materiais."),
            _sugestao("Devoluções", "Quero resumo de devoluções de materiais."),
            _sugestao("Alertas", "Quero os alertas atuais."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "materiais_levantamentos":
        return [
            _sugestao("Stock baixo", "Mostra materiais com stock baixo."),
            _sugestao("Devoluções", "Quero resumo de devoluções de materiais."),
            _sugestao("Furos", "Quero aprofundar furos."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "materiais_devolucoes":
        return [
            _sugestao("Stock baixo", "Mostra materiais com stock baixo."),
            _sugestao("Levantamentos", "Quero resumo de levantamentos de materiais."),
            _sugestao("Furos", "Quero aprofundar furos."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "maquinas":
        return [
            _sugestao("Estados das máquinas", "Mostra os estados das máquinas."),
            _sugestao("Máquinas não operacionais", "Mostra máquinas não operacionais."),
            _sugestao("Alertas", "Quero os alertas atuais."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "maquinas_estados":
        return [
            _sugestao("Máquinas em alerta", "Mostra máquinas em alerta."),
            _sugestao("Alertas", "Quero os alertas atuais."),
            _sugestao("Empregados", "Quero aprofundar empregados."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "maquinas_alerta":
        return [
            _sugestao("Estados das máquinas", "Mostra os estados das máquinas."),
            _sugestao("Alertas", "Quero os alertas atuais."),
            _sugestao("Furos", "Quero aprofundar furos."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "empregados":
        return [
            _sugestao("Total de empregados", "Mostra resumo de empregados."),
            _sugestao("Pendentes", "Mostra empregados pendentes."),
            _sugestao("Registos diários", "Mostra resumo de registos diários."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "empregados_total":
        return [
            _sugestao("Pendentes", "Mostra empregados pendentes."),
            _sugestao("Registos de empregados", "Mostra registos diários de empregados."),
            _sugestao("Furos", "Quero aprofundar furos."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "empregados_pendentes":
        return [
            _sugestao("Total de empregados", "Mostra resumo de empregados."),
            _sugestao("Registos de empregados", "Mostra registos diários de empregados."),
            _sugestao("Alertas", "Quero os alertas atuais."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "empregados_registos":
        return [
            _sugestao("Total de empregados", "Mostra resumo de empregados."),
            _sugestao("Pendentes", "Mostra empregados pendentes."),
            _sugestao("Furos", "Quero aprofundar furos."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "eventos":
        return [
            _sugestao("Eventos recentes", "Mostra eventos recentes."),
            _sugestao("Furos", "Quero aprofundar furos."),
            _sugestao("Alertas", "Quero os alertas atuais."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "memoria_zona":
        return [
            _sugestao("Cruzar zona", "Há memória operacional nesta zona?"),
            _sugestao("Furo próximo", "Já houve um furo perto desta zona?"),
            _sugestao("Furos", "Quero aprofundar furos."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "base_conhecimento":
        return [
            _sugestao("Documentos", "Que documentos existem na base de conhecimento?"),
            _sugestao("Resumo plataforma", "Resume a base funcional da plataforma."),
            _sugestao("Go live", "O que falta para colocar a plataforma online?"),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    if tipo == "calculo":
        return [
            _sugestao("Relacionar com custos", "Relaciona este cálculo com despesas."),
            _sugestao("Relacionar com furos", "Relaciona este cálculo com metros furados."),
            _sugestao("Outro tema", PROMPT_APROFUNDAR_TEMA),
        ]

    return [_sugestao("Aprofundar um tema", PROMPT_APROFUNDAR_TEMA)]


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


def _distancia_km(lat1, lon1, lat2, lon2):
    if None in {lat1, lon1, lat2, lon2}:
        return None
    raio = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * raio * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _resumir_memoria_furo(furo):
    memoria = []
    total_medicoes = furo.medicoes.count()
    total_registos = furo.registos_furo.count()
    total_despesas = obter_total_despesas_furo(furo)

    memoria.append(
        f"Estado final conhecido: {furo.get_estado_display()} · profundidade máxima atingida {float(furo.profundidade_maxima_atingida or 0):.2f} m."
    )
    if total_medicoes:
        ultima_medicao = furo.medicoes.order_by("-profundidade_medida", "-criado_em").first()
        profundidade_ultima = float(ultima_medicao.profundidade_medida or 0)
        memoria.append(f"Foram registadas {total_medicoes} medições. A medição mais profunda ficou em {profundidade_ultima:.2f} m.")
    if total_registos:
        metros_registados = round(sum(furo.registos_furo.values_list("metros_furados", flat=True)), 2)
        memoria.append(f"Foram guardados {total_registos} registos diários com {metros_registados:.2f} m registados.")
    if total_despesas:
        memoria.append(f"Despesa direta registada neste furo: {total_despesas:.2f} €.")
    if furo.localizacao or furo.local_sondagem:
        memoria.append(f"Referência de localização: {furo.localizacao or furo.local_sondagem}.")
    return memoria


def _obter_furos_relacionados(empresa, furo_base, limite=5):
    relacionados = []
    candidatos = listar_candidatos_furos_relacionados(empresa, furo_base)
    referencia_local = (furo_base.localizacao or furo_base.local_sondagem or "").strip().lower()

    for candidato in candidatos:
        distancia = _distancia_km(furo_base.latitude, furo_base.longitude, candidato.latitude, candidato.longitude)
        if distancia is not None and distancia <= FURO_MEMORY_RADIUS_KM:
            relacionados.append(
                (distancia, f"{candidato.nome} · {candidato.projeto.nome} · {distancia:.3f} km · {candidato.get_estado_display()}")
            )
            continue

        candidato_local = (candidato.localizacao or candidato.local_sondagem or "").strip().lower()
        if referencia_local and candidato_local and referencia_local == candidato_local:
            relacionados.append(
                (0.0, f"{candidato.nome} · {candidato.projeto.nome} · mesma localização textual · {candidato.get_estado_display()}")
            )

    relacionados.sort(key=lambda item: item[0])
    return [linha for _, linha in relacionados[:limite]]


def _construir_memoria_furos_empresa(empresa, limite=12):
    memoria = []
    furos = listar_furos_memoria_empresa(empresa, limite=limite)
    for furo in furos:
        memoria.append(
            {
                "nome": furo.nome,
                "projeto": furo.projeto.nome if furo.projeto_id else "",
                "estado": furo.get_estado_display(),
                "latitude": furo.latitude,
                "longitude": furo.longitude,
                "localizacao": furo.localizacao or furo.local_sondagem,
                "profundidade_maxima_atingida": float(furo.profundidade_maxima_atingida or 0),
                "metros_furados": float(furo.metros_furados or 0),
            }
        )
    return memoria


def _resposta_memoria_zona(*, empresa, texto):
    nomes_furos = listar_nomes_furos_empresa(empresa)
    nome_furo = _detetar_nome_entidade(texto.lower(), [nome.lower() for nome in nomes_furos])
    if nome_furo:
        furo = obter_furo_empresa_por_nome(empresa, nome_furo, include_projeto=True)
        if furo:
            relacionados = _obter_furos_relacionados(empresa, furo, limite=8)
            if relacionados:
                linhas = [
                    f"Já existe memória operacional para a zona do furo {furo.nome}.",
                    "Furos relacionados encontrados:",
                    *[f"- {item}" for item in relacionados],
                    "",
                    "Resumo do furo de referência:",
                    *[f"- {item}" for item in _resumir_memoria_furo(furo)],
                ]
                return "\n".join(linhas)
            return "\n".join(
                [
                    f"Encontrei o furo {furo.nome}, mas não encontrei outros furos próximos com memória comparável nesta zona.",
                    *[f"- {item}" for item in _resumir_memoria_furo(furo)],
                ]
            )

    memoria = _construir_memoria_furos_empresa(empresa, limite=8)
    if not memoria:
        return "Ainda não existem furos suficientes registados para construir memória operacional por zona."

    linhas = [
        "A AI já consegue consultar a memória operacional dos furos da empresa.",
        "Neste momento tenho estes furos disponíveis como base de memória:",
    ]
    for item in memoria:
        referencia = item["localizacao"] or "sem localização textual"
        linhas.append(
            f"- {item['nome']} · {item['projeto']} · {item['estado']} · {item['profundidade_maxima_atingida']:.2f} m · {referencia}"
        )
    linhas.extend(
        [
            "",
            "Para eu cruzar melhor a zona, podes perguntar por exemplo:",
            "- 'já houve um furo perto do furo Furo-12?'",
            "- 'o que aconteceu na zona deste furo?'",
            "- 'há memória operacional nesta localização?'",
        ]
    )
    return "\n".join(linhas)


def construir_memoria_operacional_furo(furo):
    if not furo:
        return {"furo_referencia": None, "relacionados": []}

    relacionados = _obter_furos_relacionados(furo.empresa, furo, limite=6)
    return {
        "furo_referencia": {
            "id": str(furo.pk),
            "nome": furo.nome,
            "projeto": furo.projeto.nome if furo.projeto_id else "",
            "estado": furo.get_estado_display(),
            "resumo": _resumir_memoria_furo(furo),
        },
        "relacionados": relacionados,
    }
