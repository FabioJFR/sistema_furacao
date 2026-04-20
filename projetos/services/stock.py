from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from projetos.models import Material
from projetos.services.empregados import recalcular_resumo_empregado


# TODO futuro:
# - adicionar histórico de movimentos de stock com auditoria completa
# - centralizar validações multiempresa num helper/base service reutilizável
# - usar select_for_update se houver concorrência elevada no stock



def _resolver_empresa_id(empresa):
    return getattr(empresa, "pk", empresa)



def _normalizar_quantidade(quantidade, campo="quantidade"):
    if quantidade is None:
        raise ValidationError({campo: "A quantidade deve ser maior que zero."})

    try:
        quantidade = int(quantidade)
    except (TypeError, ValueError):
        raise ValidationError({campo: "A quantidade deve ser um número inteiro válido."})

    if quantidade <= 0:
        raise ValidationError({campo: "A quantidade deve ser maior que zero."})

    return quantidade



def validar_material_empresa(material, empresa=None):
    if not material:
        raise ValidationError("Material inválido.")

    if empresa is not None and material.empresa_id != _resolver_empresa_id(empresa):
        raise ValidationError("O material não pertence à empresa atual.")



def validar_contexto_movimento_material(movimento, empregado):
    if not empregado or not empregado.empresa_id:
        raise ValidationError("O empregado tem de estar associado a uma empresa.")

    empresa_id = empregado.empresa_id

    if movimento.material and movimento.material.empresa_id != empresa_id:
        raise ValidationError({
            "material": "O material selecionado não pertence à empresa do empregado."
        })

    if movimento.projeto and movimento.projeto.empresa_id != empresa_id:
        raise ValidationError({
            "projeto": "O projeto selecionado não pertence à empresa do empregado."
        })

    if movimento.furo and movimento.furo.empresa_id != empresa_id:
        raise ValidationError({
            "furo": "O furo selecionado não pertence à empresa do empregado."
        })

    if movimento.furo and movimento.projeto and movimento.furo.projeto_id != movimento.projeto_id:
        raise ValidationError({
            "furo": "O furo selecionado não pertence ao projeto escolhido."
        })



def _atualizar_quantidade_material(material, diferenca):
    quantidade_atual = material.quantidade or 0
    nova_quantidade = quantidade_atual + diferenca

    if nova_quantidade < 0:
        raise ValidationError({
            "quantidade": f"Stock insuficiente. Disponível: {quantidade_atual}."
        })

    material.quantidade = nova_quantidade
    material.save(update_fields=["quantidade"])
    return material



@transaction.atomic
def registrar_entrada_material(material, quantidade, empresa=None):
    validar_material_empresa(material, empresa=empresa)
    quantidade = _normalizar_quantidade(quantidade)

    return _atualizar_quantidade_material(material, quantidade)



@transaction.atomic
def registrar_saida_material(material, quantidade, empresa=None):
    validar_material_empresa(material, empresa=empresa)
    quantidade = _normalizar_quantidade(quantidade)

    return _atualizar_quantidade_material(material, -quantidade)



@transaction.atomic
def criar_levantamento_material(form, empregado):
    levantamento = form.save(commit=False)
    levantamento.empregado = empregado
    levantamento.empresa = empregado.empresa

    validar_contexto_movimento_material(levantamento, empregado)
    registrar_saida_material(
        levantamento.material,
        levantamento.quantidade,
        empresa=empregado.empresa,
    )

    levantamento.save()
    recalcular_resumo_empregado(empregado)

    return levantamento



@transaction.atomic
def criar_devolucao_material(form, empregado):
    devolucao = form.save(commit=False)
    devolucao.empregado = empregado
    devolucao.empresa = empregado.empresa

    validar_contexto_movimento_material(devolucao, empregado)
    registrar_entrada_material(
        devolucao.material,
        devolucao.quantidade,
        empresa=empregado.empresa,
    )

    devolucao.save()
    recalcular_resumo_empregado(empregado)

    return devolucao



def verificar_stock_critico(material):
    return (material.quantidade or 0) <= (material.stock_minimo or 0)



def obter_materiais_stock_critico(empresa=None):
    queryset = Material.objects.filter(
        ativo=True,
        quantidade__lte=F("stock_minimo"),
    ).order_by("quantidade")

    if empresa is not None:
        queryset = queryset.filter(empresa_id=_resolver_empresa_id(empresa))

    return queryset