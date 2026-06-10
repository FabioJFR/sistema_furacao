from pathlib import Path


KNOWLEDGE_BASE_ROOT = Path(__file__).resolve().parent.parent / "knowledge_base"
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


def resposta_base_conhecimento(texto):
    documentos = listar_documentos_base_conhecimento()
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
        conteudo = ler_conteudo_consultavel_documento("drone/drone_proprio_componentes.md")
        if conteudo:
            resumo = _primeiras_linhas_uteis(conteudo, limite=10)
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
        conteudo_plataforma = ler_conteudo_consultavel_documento("plataforma/plataforma_base_funcional.md")
        conteudo_go_live = ler_conteudo_consultavel_documento("plataforma/plataforma_go_live_checklist.md")
        if conteudo_plataforma:
            resumo_plataforma = _primeiras_linhas_uteis(conteudo_plataforma, limite=10)
            if resumo_plataforma:
                linhas.extend(
                    [
                        "",
                        "Resumo rápido da base funcional da plataforma:",
                        *[f"- {item}" for item in resumo_plataforma],
                    ]
                )
        if conteudo_go_live:
            resumo_go_live = _primeiras_linhas_uteis(conteudo_go_live, limite=8)
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


def listar_documentos_base_conhecimento():
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


def ler_documento_texto(relativo):
    path = KNOWLEDGE_BASE_ROOT / relativo
    if not path.exists() or not path.is_file():
        return ""
    if path.suffix.lower() not in EXTENSOES_TEXTO_DIRETO:
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def ler_conteudo_consultavel_documento(relativo):
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


def _primeiras_linhas_uteis(conteudo, *, limite):
    resumo = []
    for raw_line in conteudo.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        resumo.append(line)
        if len(resumo) >= limite:
            break
    return resumo
