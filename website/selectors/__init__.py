import re

from plataforma.models import Plano


def listar_planos_ativos():
    return Plano.objects.filter(ativo=True).order_by("preco_mensal")


def obter_plano_ativo_por_id(plano_id):
    return Plano.objects.filter(pk=plano_id, ativo=True).first()


def construir_planos_contexto(planos_qs):
    return {
        str(plano.pk): {
            "nome": plano.nome,
            "tipo": plano.tipo,
            "periodos": plano.periodos_cobranca_disponiveis_normalizados,
            "preco_mensal": str(plano.preco_mensal or 0),
            "preco_anual": str(plano.preco_anual or 0),
        }
        for plano in planos_qs
    }


def _normalizar_texto_descricao(descricao):
    texto = (descricao or "").strip()
    if not texto:
        return ""
    texto = re.sub(r"\s+", " ", texto)
    texto = texto.replace("•", " · ")
    return texto.strip()


def _partes_descricao_plano(descricao):
    texto = _normalizar_texto_descricao(descricao)
    if not texto:
        return "", []

    # Pontos comuns usados nos textos atuais dos planos.
    texto = texto.replace("Inclui:", "||Inclui:")
    texto = texto.replace("Objetivo:", "||Objetivo:")
    texto = texto.replace("objetivo:", "||Objetivo:")
    texto = texto.replace("Começar grátis", "||Começar grátis")
    texto = texto.replace("Comecar gratis", "||Começar grátis")
    texto = texto.replace("👉", "||")
    texto = texto.replace(" - ", " || ")

    partes = [p.strip(" .") for p in texto.split("||") if p.strip(" .")]
    if not partes:
        return texto, []

    resumo = partes[0]
    pontos = partes[1:]

    # fallback: se ainda vier tudo muito corrido, divide por frases.
    if not pontos and len(resumo) > 180:
        frases = [f.strip(" .") for f in re.split(r"\.\s+", resumo) if f.strip(" .")]
        if len(frases) > 1:
            resumo = frases[0]
            pontos = frases[1:]

    return resumo, pontos


def construir_planos_para_cards(planos_qs):
    planos = []
    for plano in planos_qs:
        resumo, pontos = _partes_descricao_plano(getattr(plano, "descricao", ""))
        planos.append(
            {
                "obj": plano,
                "resumo": resumo,
                "pontos": pontos,
            }
        )
    return planos
