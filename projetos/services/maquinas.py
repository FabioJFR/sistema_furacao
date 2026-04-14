from django.core.exceptions import ValidationError
from django.db import transaction

from projetos.models import Maquina


ESTADOS_VALIDOS_MAQUINA = {
    "ativa",
    "avariada",
    "reparacao",
    "parada",
}


@transaction.atomic
def alterar_estado_maquina(maquina, novo_estado):
    if novo_estado not in ESTADOS_VALIDOS_MAQUINA:
        raise ValidationError({
            "estado": f"Estado inválido: {novo_estado}."
        })

    maquina.estado = novo_estado
    maquina.save(update_fields=["estado"])

    return maquina


def criar_maquina(form):
    maquina = form.save()
    return maquina


def atualizar_maquina(form):
    maquina = form.save()
    return maquina