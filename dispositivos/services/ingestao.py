from decimal import Decimal

from django.db import transaction
from django.db.models import Max
from dispositivos.drivers.magcruiser.parser import parse_magcruiser_payload
from dispositivos.models import LeituraBrutaDispositivo, SurveyShot
from projetos.models import Medicao


def _normalizar_valor_para_json(valor):
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, dict):
        return {chave: _normalizar_valor_para_json(item) for chave, item in valor.items()}
    if isinstance(valor, list):
        return [_normalizar_valor_para_json(item) for item in valor]
    return valor


@transaction.atomic
def guardar_leitura_e_shot(sessao, furo, payload_texto: str, dados: dict):
    leitura = LeituraBrutaDispositivo.objects.create(
        sessao=sessao,
        payload_texto=payload_texto,
        payload_json=_normalizar_valor_para_json(dados),
    )

    shot = SurveyShot.objects.create(
        sessao=sessao,
        furo=furo,
        empresa=furo.empresa,
        profundidade=dados["profundidade"],
        inclinacao=dados["inclinacao"],
        azimute=dados["azimute"],
        magnetismo=dados.get("magnetismo"),
        origem="magcruiser",
    )

    medicao = Medicao.objects.create(
        furo=furo,
        empresa=furo.empresa,
        profundidade_medida=dados["profundidade"],
        inclinacao_real_medida=dados["inclinacao"],
        azimute_real_medido=dados["azimute"],
        magnetismo=dados.get("magnetismo"),
    )

    return leitura, shot, medicao


@transaction.atomic
def guardar_leitura_dispositivo(*, sessao, raw_payload: str, furo=None):
    sessao = (
        sessao.__class__.objects.select_for_update()
        .select_related("empresa")
        .get(pk=sessao.pk)
    )

    dados = parse_magcruiser_payload(raw_payload)
    furo_destino = furo or sessao.furo
    if not furo_destino:
        raise ValueError("A sessão não tem furo associado e não foi indicado furo de destino.")
    if furo_destino.empresa_id != sessao.empresa_id:
        raise ValueError("O furo de destino deve pertencer à mesma empresa da sessão.")

    ultima_seq = (
        LeituraBrutaDispositivo.objects.filter(sessao=sessao)
        .aggregate(max_seq=Max("sequencia"))
        .get("max_seq") or 0
    ) + 1

    leitura = LeituraBrutaDispositivo.objects.create(
        sessao=sessao,
        empresa=sessao.empresa,
        sequencia=ultima_seq,
        payload_texto=raw_payload,
        payload_json=_normalizar_valor_para_json(dados),
    )

    shot = SurveyShot.objects.create(
        sessao=sessao,
        empresa=sessao.empresa,
        furo=furo_destino,
        profundidade=dados["profundidade"],
        inclinacao=dados["inclinacao"],
        azimute=dados["azimute"],
        magnetismo=dados.get("magnetismo"),
        temperatura=dados.get("temperatura"),
        origem="magcruiser",
    )

    medicao = Medicao.objects.create(
        empresa=sessao.empresa,
        furo=furo_destino,
        profundidade_medida=dados["profundidade"],
        inclinacao_real_medida=dados["inclinacao"],
        azimute_real_medido=dados["azimute"],
        magnetismo=dados.get("magnetismo"),
    )

    return {
        "leitura": leitura,
        "shot": shot,
        "medicao": medicao,
        "dados": dados,
    }
