from django.utils import timezone
from django.utils.translation import gettext as _

from projetos.models import (
    AssiduidadeRegisto,
    Empregados,
    MaquinaAvaria,
    NotificacaoGestao,
    PlaneamentoTurno,
)


def normalizar_filtros_notificacoes(query_params):
    return {
        "estado": (query_params.get("estado") or "").strip(),
        "prioridade": (query_params.get("prioridade") or "").strip(),
    }


def filtrar_notificacoes_gestao(*, empresa, filtros):
    queryset = NotificacaoGestao.objects.filter(empresa=empresa)
    if filtros.get("estado"):
        queryset = queryset.filter(estado=filtros["estado"])
    if filtros.get("prioridade"):
        queryset = queryset.filter(prioridade=filtros["prioridade"])
    return queryset


def calcular_sla_notificacao(notificacao, *, referencia=None, traduzir=False):
    referencia = referencia or timezone.now()
    labels = {
        "ok": _("OK") if traduzir else "OK",
        "atrasado": _("Atrasado") if traduzir else "Atrasado",
        "em_risco": _("Em risco") if traduzir else "Em risco",
    }

    if notificacao.prazo is None or notificacao.estado == "resolvida":
        return labels["ok"]
    if notificacao.prazo < referencia:
        return labels["atrasado"]
    if (notificacao.prazo - referencia).total_seconds() <= 24 * 3600:
        return labels["em_risco"]
    return labels["ok"]


def serializar_notificacao_gestao(notificacao, *, referencia=None, traduzir_sla=False):
    return {
        "id": notificacao.id,
        "titulo": notificacao.titulo,
        "prioridade": notificacao.get_prioridade_display(),
        "estado": notificacao.get_estado_display(),
        "responsavel": notificacao.responsavel.nome if notificacao.responsavel else "-",
        "prazo": notificacao.prazo.strftime("%d/%m/%Y %H:%M") if notificacao.prazo else "-",
        "sla": calcular_sla_notificacao(notificacao, referencia=referencia, traduzir=traduzir_sla),
    }


def construir_contexto_centro_notificacoes(*, empresa, filtros, limite=20, referencia=None):
    referencia = referencia or timezone.now()
    pendentes_empregado = Empregados.objects.filter(empresa=empresa, aprovado=False).count()
    assiduidade_pendente = AssiduidadeRegisto.objects.filter(empresa=empresa, estado="pendente").count()
    avarias_abertas = MaquinaAvaria.objects.filter(empresa=empresa).exclude(status="resolvida").count()
    planeamentos_pendentes = PlaneamentoTurno.objects.filter(empresa=empresa, estado="planeado").count()

    fila = []
    if pendentes_empregado:
        fila.append([_("Alta"), _("Empregados pendentes"), str(pendentes_empregado)])
    if avarias_abertas:
        fila.append([_("Alta"), _("Avarias em aberto"), str(avarias_abertas)])
    if assiduidade_pendente:
        fila.append([_("Média"), _("Assiduidade pendente"), str(assiduidade_pendente)])
    if planeamentos_pendentes:
        fila.append([_("Média"), _("Planeamentos por confirmar"), str(planeamentos_pendentes)])

    notificacoes = (
        filtrar_notificacoes_gestao(empresa=empresa, filtros=filtros)
        .select_related("responsavel")
        .order_by("estado", "prazo", "-criado_em")[:limite]
    )
    linhas_notificacoes = [
        serializar_notificacao_gestao(notificacao, referencia=referencia, traduzir_sla=True)
        for notificacao in notificacoes
    ]

    return {
        "kpis": [
            {"titulo": _("Pendências críticas"), "valor": str(pendentes_empregado + avarias_abertas)},
            {"titulo": _("Pendências médias"), "valor": str(assiduidade_pendente + planeamentos_pendentes)},
        ],
        "fila": fila,
        "notificacoes": linhas_notificacoes,
    }
