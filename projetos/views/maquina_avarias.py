import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render

from core.permissions import admin_required
from projetos.decorators import empregado_required
from projetos.forms.maquina_avaria import (
    MaquinaAvariaAdminUpdateForm,
    MaquinaAvariaEmpregadoForm,
    MaquinaAvariaEmpregadoUpdateForm,
)
from projetos.selectors.maquina_avarias import (
    listar_avarias_empresa,
    listar_avarias_responsavel,
    listar_furos_empresa,
    listar_maquinas_empresa,
    obter_avaria_empresa,
    obter_avaria_responsavel,
)
from projetos.services.acesso_contexto import obter_empresa_admin_contexto, obter_empregado_autenticado_contexto
from projetos.services.maquina_avarias import atualizar_avaria, criar_avaria_por_admin, criar_avaria_por_empregado

logger = logging.getLogger("core")


def _obter_empresa_admin_maquina_avarias(request):
    empresa, resposta_erro = obter_empresa_admin_contexto(
        request=request,
        mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
        mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa.",
        redirect_sem_permissao="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:dashboard",
    )
    return empresa, resposta_erro


def _obter_empregado_autenticado_maquina_avarias(request):
    empregado, _fallback, resposta_erro = obter_empregado_autenticado_contexto(
        request=request,
        mensagem_sem_empregado="A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        mensagem_sem_empresa="A tua conta não está associada a uma empresa. Contacta o administrador.",
        redirect_sem_empregado="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:redirect_after_login",
        vincular_por_email=True,
    )
    return empregado, resposta_erro


def _render_form_avaria(request, form, titulo, cancel_url):
    return render(
        request,
        "projetos/maquina_avaria_form_empregado.html",
        {"form": form, "titulo": titulo, "cancel_url": cancel_url},
    )


def _processar_create_avaria(
    *,
    request,
    form,
    on_success,
    sucesso_msg,
    erro_msg,
):
    if not form.is_valid():
        messages.error(request, erro_msg)
        return None

    maquina = form.cleaned_data["maquina"]
    furo = form.cleaned_data.get("furo")
    descricao = form.cleaned_data.get("descricao")
    on_success(maquina=maquina, furo=furo, descricao=descricao)
    messages.success(request, sucesso_msg)
    return maquina


@login_required
@empregado_required
def avaria_maquina_create_empregado(request):
    empregado, resposta_erro = _obter_empregado_autenticado_maquina_avarias(request)
    if resposta_erro:
        return resposta_erro

    if request.method == "POST":
        form = MaquinaAvariaEmpregadoForm(request.POST, empresa_id=empregado.empresa_id)
        maquina = _processar_create_avaria(
            request=request,
            form=form,
            on_success=lambda **kwargs: criar_avaria_por_empregado(empregado=empregado, **kwargs),
            sucesso_msg="Avaria registada com sucesso. A empresa foi notificada no painel de avarias.",
            erro_msg="Não foi possível registar a avaria. Verifica os dados.",
        )
        if maquina:
            return redirect("projetos:area_empregado")
    else:
        form = MaquinaAvariaEmpregadoForm(empresa_id=empregado.empresa_id)

    return _render_form_avaria(
        request,
        form,
        "Registar avaria de máquina",
        "projetos:area_empregado",
    )


@login_required
@admin_required
def avaria_maquina_create_admin(request):
    empresa, resposta_erro = _obter_empresa_admin_maquina_avarias(request)
    if resposta_erro:
        return resposta_erro

    initial = {}
    maquina_id = request.GET.get("maquina")
    furo_id = request.GET.get("furo")

    if maquina_id:
        maquina = listar_maquinas_empresa(empresa.id).filter(pk=maquina_id).first()
        if not maquina:
            raise Http404("Máquina não encontrada para esta empresa.")
        initial["maquina"] = maquina

    if furo_id:
        furo = listar_furos_empresa(empresa.id).filter(pk=furo_id).first()
        if not furo:
            raise Http404("Furo não encontrado para esta empresa.")
        initial["furo"] = furo

    if request.method == "POST":
        form = MaquinaAvariaEmpregadoForm(request.POST, empresa_id=empresa.id)
        maquina = _processar_create_avaria(
            request=request,
            form=form,
            on_success=lambda **kwargs: criar_avaria_por_admin(empresa=empresa, **kwargs),
            sucesso_msg="Avaria registada com sucesso.",
            erro_msg="Não foi possível registar a avaria. Verifica os dados.",
        )
        if maquina:
            return redirect("projetos:maquina_detail", maquina_id=maquina.id)
    else:
        form = MaquinaAvariaEmpregadoForm(empresa_id=empresa.id, initial=initial)

    return _render_form_avaria(
        request,
        form,
        "Registar avaria de máquina",
        "projetos:maquina_list",
    )


@login_required
@admin_required
def avaria_maquina_list_admin(request):
    empresa, resposta_erro = _obter_empresa_admin_maquina_avarias(request)
    if resposta_erro:
        return resposta_erro

    avarias = listar_avarias_empresa(empresa.id)
    return render(
        request,
        "projetos/maquina_avaria_list_admin.html",
        {"avarias": avarias},
    )


@login_required
@admin_required
def avaria_maquina_update_admin(request, pk):
    empresa, resposta_erro = _obter_empresa_admin_maquina_avarias(request)
    if resposta_erro:
        return resposta_erro

    avaria = obter_avaria_empresa(pk, empresa.id)

    if request.method == "POST":
        form = MaquinaAvariaAdminUpdateForm(request.POST, instance=avaria, empresa_id=empresa.id)
        if form.is_valid():
            atualizar_avaria(
                avaria=avaria,
                status=form.cleaned_data["status"],
                solucao=form.cleaned_data.get("solucao", ""),
                responsavel_empregado=form.cleaned_data.get("responsavel_empregado"),
                ator_nome=request.user.get_username() or "Administrador",
            )
            messages.success(request, "Avaria atualizada com sucesso.")
            return redirect("projetos:avaria_maquina_list_admin")
        messages.error(request, "Não foi possível atualizar a avaria.")
    else:
        form = MaquinaAvariaAdminUpdateForm(instance=avaria, empresa_id=empresa.id)

    return render(
        request,
        "projetos/maquina_avaria_update_admin.html",
        {"form": form, "avaria": avaria},
    )


@login_required
@empregado_required
def avaria_maquina_minhas_empregado(request):
    empregado, resposta_erro = _obter_empregado_autenticado_maquina_avarias(request)
    if resposta_erro:
        return resposta_erro

    avarias = listar_avarias_responsavel(empregado.id, empregado.empresa_id)
    return render(
        request,
        "projetos/maquina_avaria_minhas_empregado.html",
        {"avarias": avarias},
    )


@login_required
@empregado_required
def avaria_maquina_update_empregado(request, pk):
    empregado, resposta_erro = _obter_empregado_autenticado_maquina_avarias(request)
    if resposta_erro:
        return resposta_erro

    avaria = obter_avaria_responsavel(pk, empregado.id, empregado.empresa_id)
    if request.method == "POST":
        form = MaquinaAvariaEmpregadoUpdateForm(request.POST, instance=avaria)
        if form.is_valid():
            atualizar_avaria(
                avaria=avaria,
                status=form.cleaned_data["status"],
                solucao=form.cleaned_data.get("solucao", ""),
                responsavel_empregado=avaria.responsavel_empregado,
                ator_nome=empregado.nome or request.user.get_username(),
            )
            messages.success(request, "Estado da avaria atualizado com sucesso.")
            return redirect("projetos:avaria_maquina_minhas_empregado")
        messages.error(request, "Não foi possível atualizar a avaria.")
    else:
        form = MaquinaAvariaEmpregadoUpdateForm(instance=avaria)

    return render(
        request,
        "projetos/maquina_avaria_update_empregado.html",
        {"form": form, "avaria": avaria},
    )
