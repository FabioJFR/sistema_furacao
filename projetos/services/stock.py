from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404

from projetos.models import Material
from projetos.selectors.material import obter_material_por_id_empresa
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


def aplicar_erros_validacao_no_form(form, erro):
    if hasattr(erro, "message_dict"):
        for campo, erros in erro.message_dict.items():
            destino = campo if campo in form.fields else None
            for mensagem in erros:
                form.add_error(destino, mensagem)
        return

    if hasattr(erro, "messages"):
        for mensagem in erro.messages:
            form.add_error(None, mensagem)
        return

    form.add_error(None, str(erro))



def validar_material_empresa(material, empresa=None):
    if not material:
        raise ValidationError("Material inválido.")

    if empresa is not None and material.empresa_id != _resolver_empresa_id(empresa):
        raise ValidationError("O material não pertence à empresa atual.")


def _preparar_material_para_guardar(material, empresa=None):
    if empresa is not None:
        material.empresa_id = _resolver_empresa_id(empresa)
    validar_material_empresa(material, empresa=empresa)
    return material



def _atualizar_estado_material(material):
    quantidade = material.quantidade or 0
    stock_minimo = getattr(material, "stock_minimo", None)

    if quantidade <= 0:
        material.quantidade = 0
        if hasattr(material, "estado"):
            material.estado = "sem_stock"
        return

    if stock_minimo is not None and quantidade <= stock_minimo:
        if hasattr(material, "estado"):
            material.estado = "sem_stock"
        return

    if hasattr(material, "estado"):
        material.estado = "em_estoque"


def _obter_material_para_movimento(material, empresa=None):
    material_obj = material
    if not isinstance(material_obj, Material):
        material_obj = get_object_or_404(Material, pk=material_obj)

    validar_material_empresa(material_obj, empresa=empresa)

    return Material.objects.select_for_update().get(pk=material_obj.pk)


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
    _atualizar_estado_material(material)

    campos_update = ["quantidade"]
    if hasattr(material, "estado"):
        campos_update.append("estado")

    material.save(update_fields=campos_update)
    return material



@transaction.atomic
def registrar_entrada_material(material, quantidade, empresa=None):
    material = _obter_material_para_movimento(material, empresa=empresa)
    quantidade = _normalizar_quantidade(quantidade)

    return _atualizar_quantidade_material(material, quantidade)



@transaction.atomic
def registrar_saida_material(material, quantidade, empresa=None):
    material = _obter_material_para_movimento(material, empresa=empresa)
    quantidade = _normalizar_quantidade(quantidade)

    return _atualizar_quantidade_material(material, -quantidade)


def processar_entrada_material_form(*, form, material, empresa=None):
    if not form.is_valid():
        return None, "form_invalido"
    try:
        material_atualizado = registrar_entrada_material(
            material=material,
            quantidade=form.cleaned_data["quantidade"],
            empresa=empresa,
        )
        return material_atualizado, None
    except ValidationError as erro:
        aplicar_erros_validacao_no_form(form, erro)
        return None, "validacao"


def processar_saida_material_form(*, form, material, empresa=None):
    if not form.is_valid():
        return None, "form_invalido"
    try:
        material_atualizado = registrar_saida_material(
            material=material,
            quantidade=form.cleaned_data["quantidade"],
            empresa=empresa,
        )
        return material_atualizado, None
    except ValidationError as erro:
        aplicar_erros_validacao_no_form(form, erro)
        return None, "validacao"


def processar_submissao_entrada_saida_form(*, form, material, empresa, tipo):
    if tipo == "entrada":
        material_atualizado, erro = processar_entrada_material_form(
            form=form,
            material=material,
            empresa=empresa,
        )
    elif tipo == "saida":
        material_atualizado, erro = processar_saida_material_form(
            form=form,
            material=material,
            empresa=empresa,
        )
    else:
        raise ValidationError("Tipo inválido para movimento de stock.")

    return {
        "ok": erro is None,
        "material": material_atualizado,
        "erro": erro,
        "erros_form": form.errors,
    }


def processar_fluxo_entrada_saida_material_admin(*, method, post_data, form_class, material, empresa, tipo):
    if method == "POST":
        form = form_class(post_data)
        resultado = processar_submissao_entrada_saida_form(
            form=form,
            material=material,
            empresa=empresa,
            tipo=tipo,
        )
        return {
            "form": form,
            "resultado": resultado,
        }

    return {
        "form": form_class(),
        "resultado": None,
    }


def _preparar_movimento_contexto(movimento):
    if movimento.furo and not movimento.projeto:
        movimento.projeto = movimento.furo.projeto

    if not movimento.projeto and movimento.material and movimento.material.projeto_id:
        movimento.projeto = movimento.material.projeto

    return movimento



@transaction.atomic
def criar_levantamento_material(form, empregado):
    levantamento = form.save(commit=False)
    levantamento.empregado = empregado
    levantamento.empresa = empregado.empresa
    levantamento.quantidade = _normalizar_quantidade(
        levantamento.quantidade,
        campo="quantidade",
    )

    levantamento.material = _obter_material_para_movimento(
        levantamento.material,
        empresa=empregado.empresa,
    )
    _preparar_movimento_contexto(levantamento)

    validar_contexto_movimento_material(levantamento, empregado)
    _atualizar_quantidade_material(
        levantamento.material,
        -levantamento.quantidade,
    )

    levantamento.save()
    recalcular_resumo_empregado(empregado)

    return levantamento


def processar_levantamento_material_form(*, form, empregado):
    if not form.is_valid():
        return None, "form_invalido"
    try:
        levantamento = criar_levantamento_material(form=form, empregado=empregado)
        return levantamento, None
    except ValidationError as erro:
        aplicar_erros_validacao_no_form(form, erro)
        return None, "validacao"



@transaction.atomic
def criar_devolucao_material(form, empregado):
    devolucao = form.save(commit=False)
    devolucao.empregado = empregado
    devolucao.empresa = empregado.empresa
    devolucao.quantidade = _normalizar_quantidade(
        devolucao.quantidade,
        campo="quantidade",
    )

    devolucao.material = _obter_material_para_movimento(
        devolucao.material,
        empresa=empregado.empresa,
    )
    _preparar_movimento_contexto(devolucao)

    validar_contexto_movimento_material(devolucao, empregado)
    _atualizar_quantidade_material(
        devolucao.material,
        devolucao.quantidade,
    )

    devolucao.save()
    recalcular_resumo_empregado(empregado)

    return devolucao


def processar_devolucao_material_form(*, form, empregado):
    if not form.is_valid():
        return None, "form_invalido"
    try:
        devolucao = criar_devolucao_material(form=form, empregado=empregado)
        return devolucao, None
    except ValidationError as erro:
        aplicar_erros_validacao_no_form(form, erro)
        return None, "validacao"



def processar_submissao_material_admin_form(*, form, empresa, acao):
    if not form.is_valid():
        return {
            "ok": False,
            "material": None,
            "erro": "form_invalido",
            "erros_form": form.errors,
        }

    try:
        if acao == "create":
            material = criar_material_admin(form=form, empresa=empresa)
        elif acao == "update":
            material = atualizar_material_admin(form=form, empresa=empresa)
        else:
            raise ValidationError("Ação inválida para submissão de material.")
        return {
            "ok": True,
            "material": material,
            "erro": None,
            "erros_form": None,
        }
    except ValidationError as erro:
        aplicar_erros_validacao_no_form(form, erro)
        return {
            "ok": False,
            "material": None,
            "erro": "validacao",
            "erros_form": form.errors,
        }


def processar_fluxo_material_admin_form(*, method, post_data, form_class, empresa, acao, instance=None):
    if method == "POST":
        form = form_class(post_data, instance=instance, empresa=empresa)
        resultado = processar_submissao_material_admin_form(
            form=form,
            empresa=empresa,
            acao=acao,
        )
        return {
            "form": form,
            "resultado": resultado,
        }

    form = form_class(instance=instance, empresa=empresa)
    return {
        "form": form,
        "resultado": None,
    }


def construir_initial_movimento_material(*, empregado, material_id):
    initial = {}
    if not material_id:
        return initial

    initial["material"] = material_id
    material_selecionado = obter_material_por_id_empresa(material_id, empregado.empresa)
    if material_selecionado is not None and getattr(material_selecionado, "projeto_id", None):
        initial["projeto"] = material_selecionado.projeto_id
    return initial


def preparar_form_movimento_material(*, form, empregado):
    form.instance.empregado = empregado
    form.instance.empresa = empregado.empresa
    return form


def processar_fluxo_movimento_material_form(
    *,
    method,
    post_data,
    material_id,
    empregado,
    form_class,
    processar_fn,
):
    if method == "POST":
        form = preparar_form_movimento_material(
            form=form_class(post_data, empregado=empregado),
            empregado=empregado,
        )
        resultado = processar_submissao_movimento_material_form(
            form=form,
            empregado=empregado,
            processar_fn=processar_fn,
        )
        return {
            "form": form,
            "resultado": resultado,
        }

    initial = construir_initial_movimento_material(
        empregado=empregado,
        material_id=material_id,
    )
    form = preparar_form_movimento_material(
        form=form_class(empregado=empregado, initial=initial),
        empregado=empregado,
    )
    return {
        "form": form,
        "resultado": None,
    }


def processar_submissao_movimento_material_form(*, form, empregado, processar_fn):
    movimento, erro = processar_fn(form=form, empregado=empregado)
    return {
        "ok": erro is None,
        "movimento": movimento,
        "erro": erro,
        "erros_form": form.errors,
    }


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


@transaction.atomic
def criar_material_admin(*, form, empresa):
    material = form.save(commit=False)
    material = _preparar_material_para_guardar(material, empresa=empresa)
    material.save()
    form.save_m2m()
    return material


@transaction.atomic
def atualizar_material_admin(*, form, empresa):
    material = form.save(commit=False)
    material = _preparar_material_para_guardar(material, empresa=empresa)
    material.save()
    form.save_m2m()
    return material


@transaction.atomic
def apagar_material_admin(*, material, empresa=None):
    validar_material_empresa(material, empresa=empresa)
    material_id = material.id
    material.delete()
    return material_id
