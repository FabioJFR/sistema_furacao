from datetime import date, datetime, time, timedelta
import csv
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
import zipfile
from collections import Counter
from xml.sax.saxutils import escape

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from projetos.models import Furo, RegistoDiarioFotoAmostra
from projetos.services.empregados import recalcular_resumo_empregado
from projetos.services.furos import recalcular_resumo_furo
from projetos.services.maquina_historico import registar_operacao_maquinas_por_registo



def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


RELATORIO_TURNO_CAMPOS_SIM_NAO = {
    "manobra",
    "reaming",
    "avaria",
    "relatorio_horas_paragem",
    "medicao_desvio",
    "cimentacao",
    "lavar_furo",
    "varas_presas",
    "entubamento",
}
RELATORIO_TURNO_OCORRENCIAS_LABELS = {
    "furacao": "Furação",
    "viagem": "Viagem",
    "preparar_material": "Preparar material",
    "palestra_seguranca": "Palestra segurança",
    "formacao": "Formação",
    "trabalho_ajudante": "Trabalho de ajudante",
    "manobra": "Manobra",
    "reaming": "Reaming",
    "avaria": "Avaria",
    "horas_paragem": "Horas paragem",
    "medicao_desvio": "Medição de desvio",
    "cimentacao": "Cimentação",
    "lavar_furo": "Lavar furo",
    "varas_presas": "Varas presas",
    "entubamento": "Entubamento",
    "bit_novo": "Bit novo",
    "outros": "Outros",
}

RELATORIO_TURNO_CAMPOS_MODELO = [
    "cliente", "sonda", "torre", "bomba_injecao", "bomba_captacao", "estaleiro",
    "numero_sondagem", "inclinacao", "diametro_furo", "numero_relatorio", "no_inicio",
    "no_final", "avanco_turno", "testemunho_recuperado", "percentagem_recuperacao", "furacoes",
    "operacoes_ocorrencias",
    "furacao_inicio", "furacao_fim", "furacao_avanco", "furacao_recuperacao",
    "furacao_rocha", "furacao_descricao", "manobra", "manobra_de", "manobra_ate",
    "reaming", "reaming_de", "reaming_ate", "avaria", "avaria_de", "avaria_ate",
    "relatorio_horas_paragem", "horas_paragem_de", "horas_paragem_ate", "medicao_desvio",
    "medicao_desvio_de", "medicao_desvio_ate", "cimentacao", "cimentacao_de",
    "cimentacao_ate", "lavar_furo", "lavar_furo_de", "lavar_furo_ate", "polimeros",
    "polimeros_de", "polimeros_ate", "varas_presas", "varas_presas_de", "varas_presas_ate",
    "outros", "outros_de", "outros_ate", "notas", "entubamento", "entubamento_de",
    "entubamento_ate", "equipa_turno", "especialista_1", "horas_especialista_1", "especialista_2",
    "horas_especialista_2", "especialista_3", "horas_especialista_3", "especialista_4",
    "horas_especialista_4", "servente_1", "horas_servente_1", "servente_2",
    "horas_servente_2", "servente_3", "horas_servente_3", "servente_4",
    "horas_servente_4", "bit_novo", "bit_novo_de", "bit_novo_ate", "turno",
]


def _resolver_registo_relatorio(relatorio):
    return getattr(relatorio, "registo", relatorio)


def _obter_furacoes_relatorio(relatorio):
    furacoes = getattr(relatorio, "furacoes", None) or []
    if furacoes:
        return furacoes

    valores_legado = [
        getattr(relatorio, "furacao_inicio", None),
        getattr(relatorio, "furacao_fim", None),
        getattr(relatorio, "furacao_avanco", None),
        getattr(relatorio, "furacao_recuperacao", None),
        getattr(relatorio, "furacao_rocha", ""),
        getattr(relatorio, "furacao_descricao", ""),
    ]
    if any(valor not in (None, "", []) for valor in valores_legado):
        return [
            {
                "inicio": getattr(relatorio, "furacao_inicio", None),
                "fim": getattr(relatorio, "furacao_fim", None),
                "avanco": getattr(relatorio, "furacao_avanco", None),
                "recuperacao": getattr(relatorio, "furacao_recuperacao", None),
                "rocha": getattr(relatorio, "furacao_rocha", ""),
                "descricao": getattr(relatorio, "furacao_descricao", ""),
            }
        ]
    return []


def _fmt_furacoes_relatorio(furacoes):
    linhas = []
    for index, item in enumerate(furacoes, start=1):
        if not isinstance(item, dict):
            continue
        partes = [f"{index}."]
        if item.get("inicio") not in (None, ""):
            partes.append(f"início {item['inicio']:.2f}" if isinstance(item["inicio"], (int, float)) else f"início {item['inicio']}")
        if item.get("fim") not in (None, ""):
            partes.append(f"fim {item['fim']:.2f}" if isinstance(item["fim"], (int, float)) else f"fim {item['fim']}")
        if item.get("avanco") not in (None, ""):
            partes.append(f"avanço {item['avanco']:.2f}" if isinstance(item["avanco"], (int, float)) else f"avanço {item['avanco']}")
        if item.get("recuperacao") not in (None, ""):
            partes.append(f"recuperação {item['recuperacao']:.2f}" if isinstance(item["recuperacao"], (int, float)) else f"recuperação {item['recuperacao']}")
        if item.get("rocha"):
            partes.append(f"rocha {item['rocha']}")
        if item.get("descricao"):
            partes.append(str(item["descricao"]))
        linhas.append(" | ".join(partes))
    return "\n".join(linhas) if linhas else "-"


def _obter_operacoes_ocorrencias_relatorio(relatorio):
    operacoes = getattr(relatorio, "operacoes_ocorrencias", None) or []
    if operacoes:
        return operacoes

    operacoes_legado = []
    for tipo, campo_flag, campo_de, campo_ate in (
        ("manobra", "manobra", "manobra_de", "manobra_ate"),
        ("reaming", "reaming", "reaming_de", "reaming_ate"),
        ("avaria", "avaria", "avaria_de", "avaria_ate"),
        ("horas_paragem", "relatorio_horas_paragem", "horas_paragem_de", "horas_paragem_ate"),
        ("medicao_desvio", "medicao_desvio", "medicao_desvio_de", "medicao_desvio_ate"),
        ("cimentacao", "cimentacao", "cimentacao_de", "cimentacao_ate"),
        ("lavar_furo", "lavar_furo", "lavar_furo_de", "lavar_furo_ate"),
        ("varas_presas", "varas_presas", "varas_presas_de", "varas_presas_ate"),
        ("entubamento", "entubamento", "entubamento_de", "entubamento_ate"),
        ("outros", "outros", "outros_de", "outros_ate"),
    ):
        valor_flag = getattr(relatorio, campo_flag, None)
        hora_de = getattr(relatorio, campo_de, None)
        hora_ate = getattr(relatorio, campo_ate, None)
        ativo = valor_flag == "sim" if campo_flag != "outros" else valor_flag not in (None, "")
        if not ativo and not hora_de and not hora_ate:
            continue
        operacoes_legado.append(
            {
                "tipo": tipo,
                "de": hora_de.strftime("%H:%M") if hora_de else "",
                "ate": hora_ate.strftime("%H:%M") if hora_ate else "",
            }
        )
    valor_bit_novo = getattr(relatorio, "bit_novo", None)
    hora_bit_novo_de = getattr(relatorio, "bit_novo_de", None)
    hora_bit_novo_ate = getattr(relatorio, "bit_novo_ate", None)
    bit_novo_ativo = valor_bit_novo not in (None, "", "nao")
    if bit_novo_ativo or hora_bit_novo_de or hora_bit_novo_ate:
        operacoes_legado.append(
            {
                "tipo": "bit_novo",
                "de": hora_bit_novo_de.strftime("%H:%M") if hora_bit_novo_de else "",
                "ate": hora_bit_novo_ate.strftime("%H:%M") if hora_bit_novo_ate else "",
            }
        )
    return operacoes_legado


def _fmt_operacoes_ocorrencias_relatorio(operacoes):
    linhas = []
    for index, item in enumerate(operacoes, start=1):
        if not isinstance(item, dict):
            continue
        tipo = RELATORIO_TURNO_OCORRENCIAS_LABELS.get(item.get("tipo"), item.get("tipo") or "-")
        hora_de = item.get("de") or "-"
        hora_ate = item.get("ate") or "-"
        linhas.append(f"{index}. {tipo} | de {hora_de} | até {hora_ate}")
    return "\n".join(linhas) if linhas else "-"


def _obter_equipa_turno_relatorio(relatorio):
    equipa = getattr(relatorio, "equipa_turno", None) or []
    if equipa:
        return equipa

    equipa_legado = []
    for prefixo, rotulo in (("especialista", "Especialista"), ("servente", "Servente")):
        for index in range(1, 5):
            nome = getattr(relatorio, f"{prefixo}_{index}", "") or ""
            horas = getattr(relatorio, f"horas_{prefixo}_{index}", None)
            if not nome and horas in (None, ""):
                continue
            equipa_legado.append(
                {
                    "funcao": rotulo,
                    "nome": str(nome).strip(),
                    "horas": float(horas) if horas not in (None, "") else None,
                }
            )
    return equipa_legado


def _fmt_equipa_turno_relatorio(equipa):
    linhas = []
    for index, item in enumerate(equipa, start=1):
        if not isinstance(item, dict):
            continue
        funcao = item.get("funcao") or "-"
        nome = item.get("nome") or "-"
        horas = item.get("horas")
        horas_fmt = f"{float(horas):.2f}" if horas not in (None, "") else "-"
        linhas.append(f"{index}. {funcao} | {nome} | {horas_fmt} h")
    return "\n".join(linhas) if linhas else "-"


def _calcular_totais_furacoes(furacoes):
    total_furadas = 0
    total_avanco = 0.0
    total_recuperacao = 0.0
    for item in furacoes:
        if not isinstance(item, dict):
            continue
        total_furadas += 1
        total_avanco += float(item.get("avanco") or 0)
        total_recuperacao += float(item.get("recuperacao") or 0)
    return {
        "total_furadas": total_furadas,
        "total_avanco": round(total_avanco, 2),
        "total_recuperacao": round(total_recuperacao, 2),
    }


RELATORIO_TURNO_SECOES_DETALHE = [
    {
        "titulo": "Informação",
        "campos": [
            ("cliente", "Cliente"),
            ("sonda", "Sonda"),
            ("torre", "Torre"),
            ("bomba_injecao", "Bomba injeção"),
            ("bomba_captacao", "Bomba captação"),
            ("estaleiro", "Estaleiro"),
            ("numero_sondagem", "Número sondagem"),
            ("inclinacao", "Inclinação"),
            ("diametro_furo", "Diâmetro do furo"),
            ("numero_relatorio", "Número relatório"),
            ("data", "Data"),
            ("turno", "Turno"),
            ("no_inicio", "No início"),
            ("no_final", "No final"),
            ("avanco_turno", "Avanço do turno"),
            ("testemunho_recuperado", "Testemunho recuperado"),
            ("percentagem_recuperacao", "Percentagem de recuperação"),
        ],
    },
    {
        "titulo": "Avanço e recuperação",
        "campos": [
            ("furacoes", "Furadas do turno"),
        ],
    },
    {
        "titulo": "Operações e ocorrências",
        "campos": [
            ("operacoes_ocorrencias", "Ocorrências do turno"),
            ("polimeros", "Polímeros"),
            ("bit_novo", "Bit novo"),
            ("notas", "Notas"),
        ],
    },
    {
        "titulo": "Equipa",
        "campos": [
            ("equipa_turno", "Equipa do turno"),
        ],
    },
]


def _fmt_valor_relatorio(valor):
    if valor in (None, ""):
        return "-"
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M")
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, time):
        return valor.strftime("%H:%M")
    if isinstance(valor, list):
        if valor and all(isinstance(item, dict) for item in valor):
            if valor and "funcao" in valor[0] and "nome" in valor[0]:
                return _fmt_equipa_turno_relatorio(valor)
            if valor and "tipo" in valor[0]:
                return _fmt_operacoes_ocorrencias_relatorio(valor)
            return _fmt_furacoes_relatorio(valor)
        itens = [str(item).strip() for item in valor if str(item).strip()]
        return "\n".join(itens) if itens else "-"
    return str(valor)


def _float_or_zero(valor):
    if valor in (None, ""):
        return 0.0
    try:
        return float(valor)
    except (TypeError, ValueError):
        return 0.0


def _duracao_intervalo_horas(inicio, fim):
    if not inicio or not fim:
        return 0.0
    inicio_dt = datetime.combine(date.today(), inicio)
    fim_dt = datetime.combine(date.today(), fim)
    if fim_dt < inicio_dt:
        fim_dt += timedelta(days=1)
    return round((fim_dt - inicio_dt).total_seconds() / 3600, 2)


def obter_relatorio_turno_contexto(relatorio):
    registo = _resolver_registo_relatorio(relatorio)
    cabecalho = {
        "cliente": relatorio.cliente or "-",
        "numero_relatorio": relatorio.numero_relatorio or "-",
        "data": _fmt_valor_relatorio(registo.data),
        "turno": relatorio.turno or (registo.planeamento_turno.get_turno_display() if registo.planeamento_turno_id else "-"),
        "empregado": registo.empregado.nome if registo.empregado_id else "-",
        "projeto": registo.projeto.nome if registo.projeto_id else "-",
        "furo": registo.furo.nome if registo.furo_id else "-",
        "planeamento": registo.planeamento_turno.nome_efetivo if registo.planeamento_turno_id else "-",
    }
    secoes = []
    for secao in RELATORIO_TURNO_SECOES_DETALHE:
        linhas = []
        for atributo, label in secao["campos"]:
            if atributo == "furacoes":
                furacoes = _obter_furacoes_relatorio(relatorio)
                totais_furacoes = _calcular_totais_furacoes(furacoes)
                linhas.append(
                    {
                        "label": label,
                        "valor": _fmt_valor_relatorio(furacoes),
                    }
                )
                linhas.append(
                    {
                        "label": "Total de furadas",
                        "valor": str(totais_furacoes["total_furadas"]),
                    }
                )
                linhas.append(
                    {
                        "label": "Avanço total das furadas",
                        "valor": _fmt_valor_relatorio(totais_furacoes["total_avanco"]),
                    }
                )
                linhas.append(
                    {
                        "label": "Recuperação total das furadas",
                        "valor": _fmt_valor_relatorio(totais_furacoes["total_recuperacao"]),
                    }
                )
                continue
            if atributo == "operacoes_ocorrencias":
                operacoes = _obter_operacoes_ocorrencias_relatorio(relatorio)
                linhas.append(
                    {
                        "label": label,
                        "valor": _fmt_valor_relatorio(operacoes),
                    }
                )
                continue
            if atributo == "polimeros":
                polimeros = getattr(relatorio, "polimeros", []) or []
                valor_polimeros = _fmt_valor_relatorio(polimeros)
                hora_de = getattr(relatorio, "polimeros_de", None)
                hora_ate = getattr(relatorio, "polimeros_ate", None)
                if hora_de or hora_ate:
                    horario = " - ".join(
                        parte for parte in [
                            _fmt_valor_relatorio(hora_de) if hora_de else "",
                            _fmt_valor_relatorio(hora_ate) if hora_ate else "",
                        ] if parte
                    )
                    if valor_polimeros == "-":
                        valor_polimeros = horario or "-"
                    elif horario:
                        valor_polimeros = f"{valor_polimeros}\nHorário: {horario}"
                linhas.append(
                    {
                        "label": label,
                        "valor": valor_polimeros,
                    }
                )
                continue
            if atributo == "equipa_turno":
                equipa = _obter_equipa_turno_relatorio(relatorio)
                linhas.append(
                    {
                        "label": label,
                        "valor": _fmt_valor_relatorio(equipa),
                    }
                )
                continue

            valor = getattr(relatorio, atributo)
            if atributo in RELATORIO_TURNO_CAMPOS_SIM_NAO and valor:
                valor = getattr(relatorio, f"get_{atributo}_display")()
            if atributo == "bit_novo" and valor == "nao":
                valor = ""
            if atributo in {"furacao_descricao", "notas"} and valor:
                valor = valor.strip()
            linhas.append(
                {
                    "label": label,
                    "valor": _fmt_valor_relatorio(valor),
                }
            )
        secoes.append({"titulo": secao["titulo"], "linhas": linhas})
    return {
        "cabecalho": cabecalho,
        "secoes": secoes,
    }


def exportar_relatorio_turno_pdf(relatorio):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise ValidationError(
            "Exportação PDF indisponível: instala `reportlab` no ambiente (`pip install reportlab==4.2.2`)."
        ) from exc

    contexto = obter_relatorio_turno_contexto(relatorio)
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=14 * mm,
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>Sistema Furação</b> | Relatório Técnico do Turno", styles["Title"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(f"<b>Cliente:</b> {escape(contexto['cabecalho']['cliente'])}", styles["Heading2"]))
    story.append(Paragraph(f"<b>Número relatório:</b> {escape(contexto['cabecalho']['numero_relatorio'])}", styles["Normal"]))
    story.append(Paragraph(f"<b>Data:</b> {escape(contexto['cabecalho']['data'])}", styles["Normal"]))
    story.append(Paragraph(f"<b>Turno:</b> {escape(contexto['cabecalho']['turno'])}", styles["Normal"]))
    story.append(Spacer(1, 4 * mm))

    resumo = Table(
        [
            ["Empregado", contexto["cabecalho"]["empregado"]],
            ["Projeto", contexto["cabecalho"]["projeto"]],
            ["Furo", contexto["cabecalho"]["furo"]],
            ["Planeamento", contexto["cabecalho"]["planeamento"]],
        ],
        colWidths=[40 * mm, 130 * mm],
        hAlign="LEFT",
    )
    resumo.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E5EEF8")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(resumo)
    story.append(Spacer(1, 6 * mm))

    for secao in contexto["secoes"]:
        story.append(Paragraph(f"<b>{escape(secao['titulo'])}</b>", styles["Heading3"]))
        linhas = [["Campo", "Valor"]]
        for linha in secao["linhas"]:
            linhas.append([linha["label"], (linha["valor"] or "-").replace("\n", "<br/>")])
        tabela = Table(linhas, colWidths=[55 * mm, 115 * mm], repeatRows=1, hAlign="LEFT")
        tabela.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(tabela)
        story.append(Spacer(1, 5 * mm))

    doc.build(story)
    return output.getvalue()


@transaction.atomic
def guardar_relatorio_turno_dedicado(*, relatorio_form, registo):
    if not relatorio_form.is_valid():
        return {"ok": False, "relatorio": None}

    relatorio = _guardar_relatorio_turno(relatorio_form=relatorio_form, registo=registo)
    return {
        "ok": True,
        "relatorio": relatorio,
        "apagado": relatorio is None,
    }


def exportar_relatorios_turno_zip(relatorios, *, nome_base="relatorios-tecnicos-turno"):
    relatorios = list(relatorios)
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        linhas_manifesto = [
            "Sistema Furação | Exportação consolidada de relatórios técnicos do turno",
            f"Gerado em: {timezone.localtime().strftime('%d/%m/%Y %H:%M')}",
            f"Total de relatórios: {len(relatorios)}",
            "",
        ]
        for index, relatorio in enumerate(relatorios, start=1):
            registo = _resolver_registo_relatorio(relatorio)
            nome_pdf = slugify(
                relatorio.numero_relatorio
                or f"{registo.empregado.nome}-{registo.data or index}"
            ) or f"relatorio-turno-{index}"
            pdf_bytes = exportar_relatorio_turno_pdf(relatorio)
            zip_file.writestr(f"{index:03d}-{nome_pdf}.pdf", pdf_bytes)
            linhas_manifesto.append(
                f"{index}. {relatorio.numero_relatorio or '-'} | "
                f"{_fmt_valor_relatorio(registo.data)} | "
                f"{relatorio.cliente or '-'} | "
                f"{registo.empregado.nome if registo.empregado_id else '-'} | "
                f"{registo.projeto.nome if registo.projeto_id else '-'} | "
                f"{registo.furo.nome if registo.furo_id else '-'}"
            )
        zip_file.writestr("manifesto.txt", "\n".join(linhas_manifesto))
    return zip_buffer.getvalue(), f"{slugify(nome_base) or 'relatorios-tecnicos-turno'}.zip"


def obter_dashboard_relatorios_turno(relatorios):
    relatorios = list(relatorios)
    projetos = Counter()
    turnos = Counter()
    maquinas = Counter()
    ocorrencias = Counter()
    projetos_metricas = {}
    turnos_metricas = {}
    maquinas_metricas = {}
    total_avanco = 0.0
    total_paragem = 0.0
    soma_recuperacao = 0.0
    total_com_recuperacao = 0
    total_com_ocorrencia = 0

    def _obter_bucket(mapa, chave):
        if chave not in mapa:
            mapa[chave] = {
                "nome": chave,
                "total": 0,
                "avanco": 0.0,
                "paragem": 0.0,
                "recuperacao_soma": 0.0,
                "recuperacao_qtd": 0,
            }
        return mapa[chave]

    for relatorio in relatorios:
        registo = _resolver_registo_relatorio(relatorio)
        projeto_nome = registo.projeto.nome if registo.projeto_id else "Sem projeto"
        turno_label = relatorio.turno or (registo.planeamento_turno.get_turno_display() if registo.planeamento_turno_id else "Sem turno")
        turnos[turno_label] += 1
        maquina_nome = (
            registo.planeamento_turno.maquina.nome
            if registo.planeamento_turno_id and registo.planeamento_turno.maquina_id
            else "Sem máquina"
        )
        projetos[projeto_nome] += 1
        maquinas[maquina_nome] += 1

        avanco = _float_or_zero(relatorio.avanco_turno)
        operacoes = _obter_operacoes_ocorrencias_relatorio(relatorio)
        paragem = round(
            sum(
                _duracao_intervalo_horas(
                    datetime.strptime(item.get("de"), "%H:%M").time() if item.get("de") else None,
                    datetime.strptime(item.get("ate"), "%H:%M").time() if item.get("ate") else None,
                )
                for item in operacoes
                if isinstance(item, dict) and item.get("tipo") == "horas_paragem"
            ),
            2,
        )
        if not paragem:
            paragem = _duracao_intervalo_horas(relatorio.horas_paragem_de, relatorio.horas_paragem_ate)
        if not paragem and relatorio.relatorio_horas_paragem not in {"sim", "nao", "", None}:
            paragem = _float_or_zero(relatorio.relatorio_horas_paragem)
        recuperacao = relatorio.percentagem_recuperacao

        total_avanco += avanco
        total_paragem += paragem

        for mapa, chave in (
            (projetos_metricas, projeto_nome),
            (turnos_metricas, turno_label),
            (maquinas_metricas, maquina_nome),
        ):
            bucket = _obter_bucket(mapa, chave)
            bucket["total"] += 1
            bucket["avanco"] += avanco
            bucket["paragem"] += paragem
            if recuperacao is not None:
                bucket["recuperacao_soma"] += _float_or_zero(recuperacao)
                bucket["recuperacao_qtd"] += 1

        if recuperacao is not None:
            soma_recuperacao += _float_or_zero(recuperacao)
            total_com_recuperacao += 1

        tipos_ocorrencia = [
            RELATORIO_TURNO_OCORRENCIAS_LABELS.get(item.get("tipo"), item.get("tipo") or "-")
            for item in operacoes
            if isinstance(item, dict) and item.get("tipo")
        ]
        if relatorio.polimeros:
            tipos_ocorrencia.append("Polímeros")
        if tipos_ocorrencia:
            total_com_ocorrencia += 1
            for tipo in tipos_ocorrencia:
                ocorrencias[tipo] += 1

    def _serializar(counter):
        return [{"nome": nome, "total": total} for nome, total in counter.most_common(8)]

    def _serializar_metricas(mapa):
        itens = []
        for bucket in mapa.values():
            itens.append(
                {
                    "nome": bucket["nome"],
                    "total": bucket["total"],
                    "avanco": round(bucket["avanco"], 2),
                    "paragem": round(bucket["paragem"], 2),
                    "recuperacao_media": round(
                        bucket["recuperacao_soma"] / bucket["recuperacao_qtd"], 2
                    ) if bucket["recuperacao_qtd"] else 0.0,
                }
            )
        itens.sort(key=lambda item: (-item["total"], item["nome"]))
        return itens[:8]

    return {
        "cards": {
            "total_relatorios": len(relatorios),
            "avanco_total": round(total_avanco, 2),
            "recuperacao_media": round(soma_recuperacao / total_com_recuperacao, 2) if total_com_recuperacao else 0.0,
            "horas_paragem_total": round(total_paragem, 2),
            "relatorios_com_ocorrencia": total_com_ocorrencia,
        },
        "por_projeto": _serializar(projetos),
        "por_turno": _serializar(turnos),
        "por_maquina": _serializar(maquinas),
        "metricas_projeto": _serializar_metricas(projetos_metricas),
        "metricas_turno": _serializar_metricas(turnos_metricas),
        "metricas_maquina": _serializar_metricas(maquinas_metricas),
        "ocorrencias_por_tipo": _serializar(ocorrencias),
    }


def exportar_relatorios_turno_csv_bytes(relatorios):
    relatorios = list(relatorios)
    import io
    string_io = io.StringIO()
    writer = csv.writer(string_io)
    writer.writerow(
        [
            "Data",
            "Numero relatorio",
            "Cliente",
            "Empregado",
            "Projeto",
            "Furo",
            "Planeamento",
            "Turno",
            "Sonda",
            "Torre",
            "No inicio",
            "No final",
            "Avanco turno",
            "Horas paragem",
            "Notas",
        ]
    )
    for relatorio in relatorios:
        registo = _resolver_registo_relatorio(relatorio)
        writer.writerow(
            [
                _fmt_valor_relatorio(registo.data),
                relatorio.numero_relatorio or "",
                relatorio.cliente or "",
                registo.empregado.nome if registo.empregado_id else "",
                registo.projeto.nome if registo.projeto_id else "",
                registo.furo.nome if registo.furo_id else "",
                registo.planeamento_turno.nome_efetivo if registo.planeamento_turno_id else "",
                relatorio.turno or "",
                relatorio.sonda or "",
                relatorio.torre or "",
                relatorio.no_inicio if relatorio.no_inicio is not None else "",
                relatorio.no_final if relatorio.no_final is not None else "",
                relatorio.avanco_turno if relatorio.avanco_turno is not None else "",
                _duracao_intervalo_horas(relatorio.horas_paragem_de, relatorio.horas_paragem_ate),
                relatorio.notas or "",
            ]
        )
    return string_io.getvalue().encode("utf-8-sig")


def exportar_relatorios_turno_xlsx_bytes(relatorios):
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise ValidationError(
            "Exportação XLSX indisponível: instala `openpyxl` no ambiente (`pip install openpyxl==3.1.5`)."
        ) from exc

    relatorios = list(relatorios)
    wb = Workbook()
    ws = wb.active
    ws.title = "RelatoriosTecnicos"
    ws.append(
        [
            "Data",
            "Numero relatorio",
            "Cliente",
            "Empregado",
            "Projeto",
            "Furo",
            "Planeamento",
            "Turno",
            "Sonda",
            "Torre",
            "No inicio",
            "No final",
            "Avanco turno",
            "Horas paragem",
            "Notas",
        ]
    )
    for relatorio in relatorios:
        registo = _resolver_registo_relatorio(relatorio)
        ws.append(
            [
                _fmt_valor_relatorio(registo.data),
                relatorio.numero_relatorio or "",
                relatorio.cliente or "",
                registo.empregado.nome if registo.empregado_id else "",
                registo.projeto.nome if registo.projeto_id else "",
                registo.furo.nome if registo.furo_id else "",
                registo.planeamento_turno.nome_efetivo if registo.planeamento_turno_id else "",
                relatorio.turno or "",
                relatorio.sonda or "",
                relatorio.torre or "",
                float(relatorio.no_inicio) if relatorio.no_inicio is not None else None,
                float(relatorio.no_final) if relatorio.no_final is not None else None,
                float(relatorio.avanco_turno) if relatorio.avanco_turno is not None else None,
                _duracao_intervalo_horas(relatorio.horas_paragem_de, relatorio.horas_paragem_ate) or None,
                relatorio.notas or "",
            ]
        )
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def exportar_relatorios_turno_pdf_consolidado(relatorios):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise ValidationError(
            "Exportação PDF indisponível: instala `reportlab` no ambiente (`pip install reportlab==4.2.2`)."
        ) from exc

    relatorios = list(relatorios)
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm, bottomMargin=14 * mm)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>Sistema Furação</b> | Relatórios Técnicos do Turno", styles["Title"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(f"<b>Total de relatórios:</b> {len(relatorios)}", styles["Normal"]))
    story.append(Paragraph(f"<b>Gerado em:</b> {timezone.localtime().strftime('%d/%m/%Y %H:%M')}", styles["Normal"]))
    story.append(Spacer(1, 6 * mm))

    resumo_dashboard = obter_dashboard_relatorios_turno(relatorios)
    for titulo, itens in [
        ("Por projeto", resumo_dashboard["por_projeto"]),
        ("Por turno", resumo_dashboard["por_turno"]),
        ("Por máquina", resumo_dashboard["por_maquina"]),
    ]:
        story.append(Paragraph(f"<b>{titulo}</b>", styles["Heading3"]))
        linhas = [["Nome", "Total"]]
        if itens:
            linhas.extend([[item["nome"], str(item["total"])] for item in itens])
        else:
            linhas.append(["Sem dados", "0"])
        tabela = Table(linhas, colWidths=[130 * mm, 40 * mm], hAlign="LEFT")
        tabela.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(tabela)
        story.append(Spacer(1, 4 * mm))

    for index, relatorio in enumerate(relatorios, start=1):
        contexto = obter_relatorio_turno_contexto(relatorio)
        story.append(PageBreak())
        story.append(Paragraph(f"<b>Relatório {index}</b> | {escape(contexto['cabecalho']['numero_relatorio'])}", styles["Heading2"]))
        story.append(Paragraph(f"<b>Cliente:</b> {escape(contexto['cabecalho']['cliente'])}", styles["Normal"]))
        story.append(Paragraph(f"<b>Data:</b> {escape(contexto['cabecalho']['data'])} | <b>Turno:</b> {escape(contexto['cabecalho']['turno'])}", styles["Normal"]))
        story.append(Spacer(1, 3 * mm))
        for secao in contexto["secoes"]:
            story.append(Paragraph(f"<b>{escape(secao['titulo'])}</b>", styles["Heading3"]))
            linhas = [["Campo", "Valor"]]
            for linha in secao["linhas"]:
                linhas.append([linha["label"], (linha["valor"] or "-").replace("\n", "<br/>")])
            tabela = Table(linhas, colWidths=[55 * mm, 115 * mm], repeatRows=1, hAlign="LEFT")
            tabela.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5EEF8")),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            story.append(tabela)
            story.append(Spacer(1, 4 * mm))

    doc.build(story)
    return output.getvalue()



def _obter_furo_para_registo(furo_id, empregado):
    queryset = Furo.objects.select_for_update()

    if empregado.empresa_id:
        queryset = queryset.filter(empresa_id=empregado.empresa_id)

    return queryset.get(pk=furo_id)



def _validar_registo_multiempresa(registo, empregado, furo=None):
    if empregado.empresa_id:
        if registo.empresa_id and registo.empresa_id != empregado.empresa_id:
            raise ValidationError("O registo não pertence à empresa do empregado.")

        if registo.projeto_id and registo.projeto and registo.projeto.empresa_id != empregado.empresa_id:
            raise ValidationError("O projeto do registo não pertence à empresa do empregado.")

        if furo and furo.empresa_id != empregado.empresa_id:
            raise ValidationError("O furo do registo não pertence à empresa do empregado.")

    if registo.projeto_id and furo and furo.projeto_id != registo.projeto_id:
        raise ValidationError("O furo selecionado não pertence ao projeto do registo.")



def _preencher_snapshot_furo_no_registo(registo, furo):
    profundidade_antes = furo.profundidade_atual or 0.0
    metros_novos = registo.metros_furados or 0.0
    profundidade_depois = profundidade_antes + metros_novos

    registo.profundidade_furo_antes = profundidade_antes
    registo.profundidade_furo_depois = profundidade_depois

    registo.profundidade_alvo_inicial_furo = furo.profundidade_alvo_inicial or 0.0
    registo.inclinacao_planeada_inicial_furo = furo.inclinacao_planeada_inicial
    registo.azimute_planeado_inicial_furo = furo.azimute_planeado_inicial

    registo.profundidade_alvo_atual_furo = furo.profundidade_alvo_atual or 0.0
    registo.inclinacao_planeada_atual_furo = furo.inclinacao_planeada_atual
    registo.azimute_planeado_atual_furo = furo.azimute_planeado_atual

    registo.inclinacao_real_atual_furo = furo.inclinacao_real_atual
    registo.azimute_real_atual_furo = furo.azimute_real_atual


def _guardar_relatorio_turno(*, relatorio_form, registo):
    if not _relatorio_form_tem_conteudo(relatorio_form):
        for campo in RELATORIO_TURNO_CAMPOS_MODELO:
            field = registo._meta.get_field(campo)
            if campo == "polimeros":
                setattr(registo, campo, [])
            elif campo in RELATORIO_TURNO_CAMPOS_SIM_NAO:
                setattr(registo, campo, "nao")
            elif getattr(field, "null", False):
                setattr(registo, campo, None)
            else:
                setattr(registo, campo, "")
        registo.save(update_fields=RELATORIO_TURNO_CAMPOS_MODELO)
        return None

    relatorio = relatorio_form.save(commit=False)

    def _decimal_2(valor):
        if valor in (None, ""):
            return None
        return Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    furacoes = getattr(relatorio, "furacoes", []) or []
    if furacoes:
        primeira = furacoes[0]
        ultima = furacoes[-1]
        relatorio.furacao_inicio = _decimal_2(primeira.get("inicio"))
        relatorio.furacao_fim = _decimal_2(ultima.get("fim"))
        relatorio.furacao_avanco = _decimal_2(
            sum(item.get("avanco") or 0 for item in furacoes if isinstance(item, dict)),
        )
        relatorio.furacao_recuperacao = _decimal_2(
            sum(item.get("recuperacao") or 0 for item in furacoes if isinstance(item, dict)),
        )
        rochas = [str(item.get("rocha")).strip() for item in furacoes if isinstance(item, dict) and str(item.get("rocha") or "").strip()]
        descricoes = [str(item.get("descricao")).strip() for item in furacoes if isinstance(item, dict) and str(item.get("descricao") or "").strip()]
        relatorio.furacao_rocha = rochas[0] if len(rochas) == 1 else (" / ".join(dict.fromkeys(rochas))[:200] if rochas else "")
        relatorio.furacao_descricao = " | ".join(descricoes)[:2000] if descricoes else ""
    else:
        relatorio.furacao_inicio = None
        relatorio.furacao_fim = None
        relatorio.furacao_avanco = None
        relatorio.furacao_recuperacao = None
        relatorio.furacao_rocha = ""
        relatorio.furacao_descricao = ""

    operacoes = getattr(relatorio, "operacoes_ocorrencias", []) or []
    for campo in (
        "manobra",
        "reaming",
        "avaria",
        "relatorio_horas_paragem",
        "medicao_desvio",
        "cimentacao",
        "lavar_furo",
        "varas_presas",
        "entubamento",
    ):
        setattr(relatorio, campo, "nao")
        setattr(relatorio, f"{campo}_de" if campo != "relatorio_horas_paragem" else "horas_paragem_de", None)
        setattr(relatorio, f"{campo}_ate" if campo != "relatorio_horas_paragem" else "horas_paragem_ate", None)
    relatorio.bit_novo_de = None
    relatorio.bit_novo_ate = None
    relatorio.outros = ""
    relatorio.outros_de = None
    relatorio.outros_ate = None

    def _parse_hora(valor):
        if not valor:
            return None
        return datetime.strptime(valor, "%H:%M").time()

    for item in operacoes:
        if not isinstance(item, dict):
            continue
        tipo = item.get("tipo")
        hora_de = _parse_hora(item.get("de"))
        hora_ate = _parse_hora(item.get("ate"))
        if tipo == "horas_paragem":
            relatorio.relatorio_horas_paragem = "sim"
            if relatorio.horas_paragem_de is None:
                relatorio.horas_paragem_de = hora_de
            if relatorio.horas_paragem_ate is None:
                relatorio.horas_paragem_ate = hora_ate
            continue
        if tipo == "outros":
            relatorio.outros = "Ocorrência registada"
            if relatorio.outros_de is None:
                relatorio.outros_de = hora_de
            if relatorio.outros_ate is None:
                relatorio.outros_ate = hora_ate
            continue
        if tipo == "bit_novo":
            if relatorio.bit_novo_de is None:
                relatorio.bit_novo_de = hora_de
            if relatorio.bit_novo_ate is None:
                relatorio.bit_novo_ate = hora_ate
            continue
        if tipo in RELATORIO_TURNO_CAMPOS_SIM_NAO:
            setattr(relatorio, tipo, "sim")
            if getattr(relatorio, f"{tipo}_de") is None:
                setattr(relatorio, f"{tipo}_de", hora_de)
            if getattr(relatorio, f"{tipo}_ate") is None:
                setattr(relatorio, f"{tipo}_ate", hora_ate)

    equipa = getattr(relatorio, "equipa_turno", []) or []
    for prefixo in ("especialista", "servente"):
        for index in range(1, 5):
            setattr(relatorio, f"{prefixo}_{index}", "")
            setattr(relatorio, f"horas_{prefixo}_{index}", None)

    especialistas = []
    serventes = []
    outros = []
    for item in equipa:
        if not isinstance(item, dict):
            continue
        funcao = str(item.get("funcao") or "").strip()
        funcao_lower = funcao.lower()
        if "servent" in funcao_lower:
            serventes.append(item)
        elif "especial" in funcao_lower:
            especialistas.append(item)
        else:
            outros.append(item)
    especialistas.extend(outros)

    for index, item in enumerate(especialistas[:4], start=1):
        setattr(relatorio, f"especialista_{index}", str(item.get("nome") or "").strip())
        setattr(relatorio, f"horas_especialista_{index}", item.get("horas"))
    for index, item in enumerate(serventes[:4], start=1):
        setattr(relatorio, f"servente_{index}", str(item.get("nome") or "").strip())
        setattr(relatorio, f"horas_servente_{index}", item.get("horas"))

    if not relatorio.cliente and registo.projeto_id:
        relatorio.cliente = registo.projeto.cliente
    if not relatorio.numero_sondagem and registo.furo_id:
        relatorio.numero_sondagem = registo.furo.nome
    if not relatorio.estaleiro and registo.furo_id:
        relatorio.estaleiro = registo.furo.local_sondagem
    if not relatorio.turno and registo.planeamento_turno_id:
        relatorio.turno = registo.planeamento_turno.get_turno_display()
    if not relatorio.relatorio_horas_paragem and registo.horas_paragem:
        relatorio.relatorio_horas_paragem = "sim"

    for campo in RELATORIO_TURNO_CAMPOS_MODELO:
        setattr(registo, campo, getattr(relatorio, campo))

    registo.empregado = registo.empregado or getattr(relatorio, "empregado", None) or registo.empregado
    registo.empresa = registo.empresa or getattr(relatorio, "empresa", None) or registo.empresa
    registo.save(update_fields=RELATORIO_TURNO_CAMPOS_MODELO + ["empregado", "empresa"])
    return registo


def _relatorio_form_tem_conteudo(relatorio_form):
    cleaned_data = getattr(relatorio_form, "cleaned_data", None) or {}
    for chave, valor in cleaned_data.items():
        if chave in {"registo", "empresa"}:
            continue
        if chave in RELATORIO_TURNO_CAMPOS_SIM_NAO and valor == "nao":
            continue
        if valor in (None, "", [], (), {}):
            continue
        if isinstance(valor, str) and not valor.strip():
            continue
        return True
    return False



def _preparar_registo_para_guardar(registo, empregado):
    registo.empregado = empregado
    registo.empresa = empregado.empresa

    if registo.planeamento_turno_id:
        planeamento = registo.planeamento_turno
        registo.projeto = planeamento.projeto
        if planeamento.furo_id:
            registo.furo = planeamento.furo
        if not registo.data:
            registo.data = planeamento.data_inicio
        if not registo.hora_inicio:
            registo.hora_inicio = planeamento.hora_inicio
        if not registo.hora_fim:
            registo.hora_fim = planeamento.hora_fim

    if not registo.furo_id:
        _validar_registo_multiempresa(registo, empregado)
        return None

    furo = _obter_furo_para_registo(registo.furo_id, empregado)
    if furo.estado == "concluido" and not registo.pk:
        raise ValidationError("Este furo está terminado e não aceita novos relatórios.")
    _validar_registo_multiempresa(registo, empregado, furo=furo)
    _preencher_snapshot_furo_no_registo(registo, furo)
    return furo



def _atualizar_resumo_furo_com_registo(furo, registo):
    profundidade_atual = registo.profundidade_furo_depois

    profundidade_maxima_atual = furo.profundidade_maxima_atingida or 0.0
    profundidade_maxima_atingida = profundidade_maxima_atual
    if profundidade_atual is not None and profundidade_maxima_atual < profundidade_atual:
        profundidade_maxima_atingida = profundidade_atual

    total_horas_atual = furo.total_horas or timedelta()
    horas_registo = registo.horas_trabalhadas_furo or timedelta()
    total_horas = total_horas_atual + horas_registo

    data_registo = registo.data or (registo.criado_em.date() if registo.criado_em else None)
    data_inicio_operacao = furo.data_inicio_operacao
    if data_registo:
        if not data_inicio_operacao or data_registo < data_inicio_operacao:
            data_inicio_operacao = data_registo

    # Esta atualização é meramente operacional e não deve falhar por validações
    # antigas de outros campos do furo que o registo não alterou.
    update_data = {
        "profundidade_maxima_atingida": profundidade_maxima_atingida,
        "total_horas": total_horas,
        "data_inicio_operacao": data_inicio_operacao,
    }
    if profundidade_atual is not None:
        update_data["profundidade_atual"] = profundidade_atual

    Furo.objects.filter(pk=furo.pk).update(**update_data)

    furo.profundidade_atual = update_data.get("profundidade_atual", furo.profundidade_atual)
    furo.profundidade_maxima_atingida = profundidade_maxima_atingida
    furo.total_horas = total_horas
    furo.data_inicio_operacao = data_inicio_operacao



def _recalcular_dependencias_registo(empregado, furo_antigo=None, furo_novo=None):
    recalcular_resumo_empregado(empregado)

    if furo_antigo:
        recalcular_resumo_furo(furo_antigo)

    if furo_novo and (not furo_antigo or furo_novo.pk != furo_antigo.pk):
        recalcular_resumo_furo(furo_novo)



@transaction.atomic
def criar_registo_diario(form, empregado):
    registo = form.save(commit=False)
    registo.empregado = empregado
    registo.empresa = empregado.empresa
    furo = _preparar_registo_para_guardar(registo, empregado)

    registo.save()

    if furo:
        _atualizar_resumo_furo_com_registo(furo, registo)
        registar_operacao_maquinas_por_registo(registo=registo, empregado=empregado)

    _recalcular_dependencias_registo(empregado, furo_novo=registo.furo)
    return registo



@transaction.atomic
def atualizar_registo_diario(registo, form):
    empregado = registo.empregado
    furo_antigo = registo.furo

    registo_atualizado = form.save(commit=False)
    registo_atualizado.pk = registo.pk
    furo_novo = _preparar_registo_para_guardar(registo_atualizado, empregado)

    registo_atualizado.save()

    _recalcular_dependencias_registo(
        empregado,
        furo_antigo=furo_antigo,
        furo_novo=registo_atualizado.furo,
    )

    return registo_atualizado


@transaction.atomic
def anexar_fotos_amostra(registo, empresa, fotos):
    empresa_id = _resolver_empresa_id(empresa)
    for foto in fotos:
        RegistoDiarioFotoAmostra.objects.create(
            registo=registo,
            empresa_id=empresa_id,
            imagem=foto,
        )


@transaction.atomic
def atualizar_registo_diario_empregado(registo, form):
    registo.editado_por_empregado = True
    registo.editado_em = timezone.now()
    return atualizar_registo_diario(registo, form)


def preparar_form_registo_empregado(*, form_class, relatorio_form_class, request, empregado, instance=None, initial=None):
    relatorio_instance = instance if instance is not None else None
    if request.method == "POST":
        form = form_class(
            request.POST,
            request.FILES,
            instance=instance,
            empregado=empregado,
        )
    else:
        form = form_class(
            instance=instance,
            empregado=empregado,
            initial=initial or {},
        )

    form.instance.empregado = empregado
    form.instance.empresa = empregado.empresa
    if request.method == "POST":
        relatorio_form = relatorio_form_class(
            request.POST,
            instance=relatorio_instance,
            registo=instance or form.instance,
            prefix="relatorio",
        )
    else:
        if initial and initial.get("data") and not form.instance.data:
            form.instance.data = initial.get("data")
        relatorio_form = relatorio_form_class(
            instance=relatorio_instance,
            registo=instance or form.instance,
            prefix="relatorio",
        )
    return form, relatorio_form


def processar_fluxo_form_registo_empregado(
    *,
    form_class,
    relatorio_form_class,
    request,
    empregado,
    registo=None,
    initial=None,
):
    form, relatorio_form = preparar_form_registo_empregado(
        form_class=form_class,
        relatorio_form_class=relatorio_form_class,
        request=request,
        empregado=empregado,
        instance=registo,
        initial=initial,
    )
    if request.method != "POST":
        return {
            "form": form,
            "relatorio_form": relatorio_form,
            "resultado": None,
        }

    resultado = processar_submissao_registo_empregado_form(
        form=form,
        relatorio_form=relatorio_form,
        empregado=empregado,
        fotos=request.FILES.getlist("fotos_amostra"),
        registo=registo,
    )
    return {
        "form": form,
        "relatorio_form": relatorio_form,
        "resultado": resultado,
    }


def processar_fluxo_form_registo_admin(
    *,
    form_class,
    relatorio_form_class,
    request,
    registo,
    empresa,
):
    relatorio_instance = registo
    if request.method == "POST":
        form = form_class(
            request.POST,
            request.FILES,
            instance=registo,
        )
        relatorio_form = relatorio_form_class(
            request.POST,
            instance=relatorio_instance,
            registo=registo,
            prefix="relatorio",
        )
        resultado = processar_submissao_registo_admin_form(
            form=form,
            relatorio_form=relatorio_form,
            registo=registo,
            empresa=empresa,
            fotos=request.FILES.getlist("fotos_amostra"),
        )
        return {
            "form": form,
            "relatorio_form": relatorio_form,
            "resultado": resultado,
        }

    form = form_class(instance=registo)
    relatorio_form = relatorio_form_class(instance=relatorio_instance, registo=registo, prefix="relatorio")
    return {
        "form": form,
        "relatorio_form": relatorio_form,
        "resultado": None,
    }


def processar_submissao_registo_empregado_create(*, form, relatorio_form, empregado, fotos):
    form_valido = form.is_valid()
    relatorio_valido = relatorio_form.is_valid()
    if not (form_valido and relatorio_valido):
        return {"ok": False, "registo": None}

    registo = criar_registo_diario(form=form, empregado=empregado)
    _guardar_relatorio_turno(relatorio_form=relatorio_form, registo=registo)
    anexar_fotos_amostra(
        registo=registo,
        empresa=empregado.empresa,
        fotos=fotos,
    )
    return {"ok": True, "registo": registo}


def processar_submissao_registo_empregado_update(*, form, relatorio_form, registo, empregado, fotos):
    form_valido = form.is_valid()
    relatorio_valido = relatorio_form.is_valid()
    if not (form_valido and relatorio_valido):
        return {"ok": False, "registo": None}

    registo = atualizar_registo_diario_empregado(registo, form)
    _guardar_relatorio_turno(relatorio_form=relatorio_form, registo=registo)
    anexar_fotos_amostra(
        registo=registo,
        empresa=empregado.empresa_id,
        fotos=fotos,
    )
    return {"ok": True, "registo": registo}


def processar_submissao_registo_admin_update(*, form, relatorio_form, registo, empresa, fotos):
    form_valido = form.is_valid()
    relatorio_valido = relatorio_form.is_valid()
    if not (form_valido and relatorio_valido):
        return {"ok": False, "registo": None}

    registo = atualizar_registo_diario(registo, form)
    _guardar_relatorio_turno(relatorio_form=relatorio_form, registo=registo)
    anexar_fotos_amostra(
        registo=registo,
        empresa=empresa,
        fotos=fotos,
    )
    return {"ok": True, "registo": registo}


def processar_submissao_registo_empregado_form(
    *,
    form,
    relatorio_form,
    empregado,
    fotos,
    registo=None,
):
    if registo is None:
        resultado = processar_submissao_registo_empregado_create(
            form=form,
            relatorio_form=relatorio_form,
            empregado=empregado,
            fotos=fotos,
        )
    else:
        resultado = processar_submissao_registo_empregado_update(
            form=form,
            relatorio_form=relatorio_form,
            registo=registo,
            empregado=empregado,
            fotos=fotos,
        )
    return {
        "ok": resultado["ok"],
        "registo": resultado.get("registo"),
        "erros_form": {
            "registo": form.errors,
            "relatorio": relatorio_form.errors,
        },
    }


def processar_submissao_registo_admin_form(*, form, relatorio_form, registo, empresa, fotos):
    resultado = processar_submissao_registo_admin_update(
        form=form,
        relatorio_form=relatorio_form,
        registo=registo,
        empresa=empresa,
        fotos=fotos,
    )
    return {
        "ok": resultado["ok"],
        "registo": resultado.get("registo"),
        "erros_form": {
            "registo": form.errors,
            "relatorio": relatorio_form.errors,
        },
    }
