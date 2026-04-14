from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from projetos.models import Material

from django.core.exceptions import ValidationError

from projetos.models import LevantamentoMaterial, DevolucaoMaterial
from projetos.services.empregados import recalcular_resumo_empregado


def registrar_entrada_material(material, quantidade):
    if quantidade is None or int(quantidade) <= 0:
        raise ValidationError("A quantidade de entrada deve ser maior que zero.")

    material.quantidade = (material.quantidade or 0) + int(quantidade)
    material.save(update_fields=["quantidade"])
    return material


def registrar_saida_material(material, quantidade):
    if quantidade is None or int(quantidade) <= 0:
        raise ValidationError("A quantidade de saída deve ser maior que zero.")

    quantidade = int(quantidade)
    atual = material.quantidade or 0

    if quantidade > atual:
        raise ValidationError(f"Stock insuficiente. Disponível: {atual}.")

    material.quantidade = atual - quantidade
    material.save(update_fields=["quantidade"])
    return material


def criar_levantamento_material(form, empregado):
    levantamento = form.save(commit=False)
    levantamento.empregado = empregado
    levantamento.save()

    registrar_saida_material(levantamento.material, levantamento.quantidade)
    recalcular_resumo_empregado(empregado)

    return levantamento


def criar_devolucao_material(form, empregado):
    devolucao = form.save(commit=False)
    devolucao.empregado = empregado
    devolucao.save()

    registrar_entrada_material(devolucao.material, devolucao.quantidade)
    recalcular_resumo_empregado(empregado)

    return devolucao


def verificar_stock_critico(material):
    return material.quantidade <= material.stock_minimo


@transaction.atomic
def registrar_entrada_material(material, quantidade):
    if quantidade is None or quantidade <= 0:
        raise ValidationError({"quantidade": "A quantidade de entrada deve ser maior que zero."})

    material.quantidade = (material.quantidade or 0) + quantidade
    material.save(update_fields=["quantidade"])

    return material


@transaction.atomic
def registrar_saida_material(material, quantidade):
    if quantidade is None or quantidade <= 0:
        raise ValidationError({"quantidade": "A quantidade de saída deve ser maior que zero."})

    quantidade_atual = material.quantidade or 0

    if quantidade > quantidade_atual:
        raise ValidationError({
            "quantidade": f"Stock insuficiente. Disponível: {quantidade_atual}."
        })

    material.quantidade = quantidade_atual - quantidade
    material.save(update_fields=["quantidade"])

    return material


def obter_materiais_stock_critico():
    return Material.objects.filter(
        ativo=True,
        quantidade__lte=F("stock_minimo")
    ).order_by("quantidade")