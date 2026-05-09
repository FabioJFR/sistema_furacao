from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import EmailMessage
from django.urls import reverse
from django.utils import timezone


@dataclass
class EnvioRelatorioResultado:
    enviados: int
    destinos: list[str]


def construir_url_relatorio_com_filtros(*, filtros: dict) -> str:
    data_inicio = (filtros.get("data_inicio") or "").strip()
    data_fim = (filtros.get("data_fim") or "").strip()
    base_url = reverse("projetos:gestao_relatorios_executivos")
    if not data_inicio and not data_fim:
        return base_url
    params = {}
    if data_inicio:
        params["data_inicio"] = data_inicio
    if data_fim:
        params["data_fim"] = data_fim
    return f"{base_url}?{urlencode(params)}"


def normalizar_destinos(destinos_texto: str) -> list[str]:
    raw = (destinos_texto or "").strip()
    if not raw:
        return []
    for separador in [",", ";", "\n", "\r", "\t"]:
        raw = raw.replace(separador, " ")
    emails = [item.strip().lower() for item in raw.split(" ") if item.strip()]
    return list(dict.fromkeys(emails))


def resolver_destinos_relatorio(*, empresa, destinos_form: list[str] | None = None) -> list[str]:
    destinos = list(destinos_form or [])
    if destinos:
        return list(dict.fromkeys(destinos))
    fallback = [empresa.responsavel_email, empresa.email]
    return list(dict.fromkeys([e.strip() for e in fallback if e and e.strip()]))


def enviar_relatorio_executivo_email(
    *,
    empresa,
    filtros: dict,
    relatorio: dict,
    assunto: str,
    destinos: list[str],
    incluir_csv: bool,
    incluir_xlsx: bool,
    incluir_pdf: bool,
    csv_bytes: bytes,
    xlsx_bytes: bytes,
    pdf_bytes: bytes | None = None,
) -> EnvioRelatorioResultado:
    periodo_inicio = filtros.get("data_inicio") or "-"
    periodo_fim = filtros.get("data_fim") or "-"
    corpo = (
        "Segue em anexo o relatório executivo.\n\n"
        f"Empresa: {empresa.nome}\n"
        f"Período: {periodo_inicio} até {periodo_fim}\n"
        f"Projetos: {relatorio['kpis'][0]['valor']}\n"
        f"Furos: {relatorio['kpis'][1]['valor']}\n"
        f"Empregados: {relatorio['kpis'][2]['valor']}\n"
        f"Despesa no período: {relatorio['financeiro']['despesas_total']:.2f} €\n"
    )

    email = EmailMessage(
        subject=assunto,
        body=corpo,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=destinos,
    )
    if incluir_csv:
        email.attach("relatorio_executivo.csv", csv_bytes, "text/csv")
    if incluir_xlsx:
        email.attach(
            "relatorio_executivo.xlsx",
            xlsx_bytes,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    if incluir_pdf and pdf_bytes:
        email.attach("relatorio_executivo.pdf", pdf_bytes, "application/pdf")
    enviados = int(email.send(fail_silently=False) or 0)
    return EnvioRelatorioResultado(enviados=enviados, destinos=destinos)


def calcular_proximo_envio_agendado(*, agendamento, referencia=None):
    referencia = referencia or timezone.now()
    tz = timezone.get_current_timezone()
    local_ref = timezone.localtime(referencia, tz)

    base_data = local_ref.date()
    base_hora = agendamento.hora_execucao

    def aware_for_date(d):
        naive = datetime.combine(d, base_hora)
        return timezone.make_aware(naive, tz)

    if agendamento.frequencia == "diario":
        candidato = aware_for_date(base_data)
        if candidato <= local_ref:
            candidato = aware_for_date(base_data + timedelta(days=1))
        return candidato

    if agendamento.frequencia == "semanal":
        alvo = int(agendamento.dia_semana or 0)
        atual = base_data.weekday()
        delta = (alvo - atual) % 7
        candidato = aware_for_date(base_data + timedelta(days=delta))
        if candidato <= local_ref:
            candidato = aware_for_date((base_data + timedelta(days=delta + 7)))
        return candidato

    # mensal
    dia = int(agendamento.dia_mes or 1)
    ano = base_data.year
    mes = base_data.month

    def clamp_date(y, m, d):
        if m == 12:
            next_month = datetime(y + 1, 1, 1).date()
        else:
            next_month = datetime(y, m + 1, 1).date()
        ultimo_dia = (next_month - timedelta(days=1)).day
        return datetime(y, m, min(max(d, 1), min(28, ultimo_dia))).date()

    data_candidato = clamp_date(ano, mes, dia)
    candidato = aware_for_date(data_candidato)
    if candidato <= local_ref:
        if mes == 12:
            ano += 1
            mes = 1
        else:
            mes += 1
        data_candidato = clamp_date(ano, mes, dia)
        candidato = aware_for_date(data_candidato)
    return candidato
