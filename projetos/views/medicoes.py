import logging
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ..decorators import admin_required
from ..forms.medicao import MedicaoForm
from ..models.empregado import Empregados
from ..models.furo import Furo
from plataforma.models import PerfilPlataforma
from projetos.selectors.medicoes import (
    obter_lista_medicoes,
    obter_medicao,
)
from projetos.services.medicoes import (
    atualizar_medicao,
    criar_medicao,
)

logger = logging.getLogger("core")


ADMIN_TIPOS_ACESSO_EMPRESA = ["empresa_admin", "empresa_gestor"]


# ---------------- HELPERS ----------------
def _obter_contexto_admin_medicoes(request):
    logger.debug(
        "A resolver contexto administrativo em medicoes.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    admin_empregado = Empregados.objects.filter(user=request.user).select_related("empresa").first()
    if admin_empregado:
        logger.info(
            "Contexto administrativo resolvido via Empregados em medicoes.py. user_id=%s, empresa_id=%s",
            request.user.id,
            admin_empregado.empresa_id,
        )
        return admin_empregado

    perfil = PerfilPlataforma.objects.filter(
        user=request.user,
        ativo=True,
        tipo_acesso__in=ADMIN_TIPOS_ACESSO_EMPRESA,
    ).select_related("empresa").first()
    if perfil:
        logger.info(
            "Contexto administrativo resolvido via PerfilPlataforma em medicoes.py. user_id=%s, empresa_id=%s, tipo_acesso=%s",
            request.user.id,
            perfil.empresa_id,
            perfil.tipo_acesso,
        )
        return perfil

    logger.warning(
        "Falha ao resolver contexto administrativo em medicoes.py. user_id=%s",
        request.user.id,
    )
    return None



def _obter_empresa_admin_medicoes(request):
    contexto_admin = _obter_contexto_admin_medicoes(request)
    if not contexto_admin:
        messages.error(request, "Não tens permissão para aceder a esta área.")
        return None, redirect("projetos:dashboard_projetos:redirect_after_login")

    empresa = getattr(contexto_admin, "empresa", None)
    empresa_id = getattr(contexto_admin, "empresa_id", None)

    if not empresa_id or not empresa:
        logger.warning(
            "Contexto administrativo sem empresa em medicoes.py. user_id=%s",
            request.user.id,
        )
        messages.error(request, "O utilizador administrador não está associado a uma empresa.")
        return None, redirect("projetos:dashboard_projetos:dashboard")

    return empresa, None


# Multiempresa: o administrador só pode listar e gerir medições da sua própria empresa.
@login_required
@admin_required
def medicao_list(request):
    logger.info(
        "Entrada na view medicao_list. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empresa, resposta_erro = _obter_empresa_admin_medicoes(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view medicao_list. user_id=%s", request.user.id)
        return resposta_erro

    medicoes = obter_lista_medicoes(empresa=empresa)

    logger.info(
        "View medicao_list carregada com sucesso. user_id=%s, empresa_id=%s, total_medicoes=%s",
        request.user.id,
        empresa.id,
        medicoes.count() if hasattr(medicoes, "count") else "n/a",
    )
    return render(
        request,
        "projetos/medicao_list.html",
        {"medicoes": medicoes},
    )


@login_required
@admin_required
def medicao_create(request, furo_id):
    logger.info(
        "Entrada na view medicao_create. user_id=%s, username='%s', furo_id=%s, method=%s",
        request.user.id,
        request.user.username,
        furo_id,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_medicoes(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view medicao_create. user_id=%s", request.user.id)
        return resposta_erro

    furo = get_object_or_404(Furo, pk=furo_id, empresa=empresa)

    if request.method == "POST":
        form = MedicaoForm(
            request.POST,
            request.FILES,
            furo=furo,
            empresa=empresa,
        )
        if form.is_valid():
            try:
                criar_medicao(form, furo=furo, empresa=empresa)
                logger.info(
                    "Medição criada com sucesso. user_id=%s, empresa_id=%s, furo_id=%s",
                    request.user.id,
                    empresa.id,
                    furo.pk,
                )
                messages.success(request, "Medição criada com sucesso.")
                return redirect("projetos:furos:detail", pk=furo.pk)

            except ValidationError as e:
                form.add_error(None, e)
                logger.warning(
                    "Erro de validação ao criar medição. user_id=%s, furo_id=%s, erro=%s",
                    request.user.id,
                    furo_id,
                    e,
                )
                messages.error(request, "Erro ao criar a medição. Verifique os dados.")
        else:
            logger.warning(
                "Erro ao criar medição. user_id=%s, furo_id=%s, erros=%s",
                request.user.id,
                furo_id,
                form.errors,
            )
            messages.error(request, "Erro ao criar a medição. Verifique os dados.")
    else:
        form = MedicaoForm(furo=furo, empresa=empresa)

    return render(
        request,
        "projetos/medicao_form.html",
        {
            "form": form,
            "titulo": f"Nova Medição - {furo.nome}",
            "furo": furo,
        },
    )

@login_required
@admin_required
def medicao_update(request, pk):
    logger.info(
        "Entrada na view medicao_update. user_id=%s, username='%s', medicao_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_medicoes(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view medicao_update. user_id=%s", request.user.id)
        return resposta_erro

    medicao = obter_medicao(pk, empresa=empresa)

    if request.method == "POST":
        form = MedicaoForm(
            request.POST,
            request.FILES,
            instance=medicao,
            furo=medicao.furo,
            empresa=empresa,
        )
        if form.is_valid():
            try:
                atualizar_medicao(form, empresa=empresa)
                logger.info(
                    "Medição atualizada com sucesso. user_id=%s, empresa_id=%s, medicao_id=%s",
                    request.user.id,
                    empresa.id,
                    medicao.pk,
                )
                messages.success(request, "Medição atualizada com sucesso.")
                return redirect("projetos:medicao:medicao_list")

            except ValidationError as e:
                form.add_error(None, e)
                logger.warning(
                    "Erro de validação ao atualizar medição. user_id=%s, medicao_pk=%s, erro=%s",
                    request.user.id,
                    pk,
                    e,
                )
                messages.error(request, "Erro ao atualizar a medição. Verifique os dados.")
        else:
            logger.warning(
                "Erro ao atualizar medição. user_id=%s, medicao_pk=%s, erros=%s",
                request.user.id,
                pk,
                form.errors,
            )
            messages.error(request, "Erro ao atualizar a medição. Verifique os dados.")
    else:
        form = MedicaoForm(
            instance=medicao,
            furo=medicao.furo,
            empresa=empresa,
        )

    return render(
        request,
        "projetos/medicao_form.html",
        {
            "form": form,
            "titulo": f"Editar Medição - {medicao.furo.nome}",
            "medicao": medicao,
            "furo": medicao.furo,
        },
    )

@login_required
@admin_required
def medicao_delete(request, pk):
    logger.info(
        "Entrada na view medicao_delete. user_id=%s, username='%s', medicao_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_medicoes(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view medicao_delete. user_id=%s", request.user.id)
        return resposta_erro

    medicao = obter_medicao(pk, empresa=empresa)

    if request.method == "POST":
        medicao_id = medicao.pk
        medicao.delete()
        logger.info(
            "Medição apagada com sucesso. user_id=%s, empresa_id=%s, medicao_id=%s",
            request.user.id,
            empresa.id,
            medicao_id,
        )
        messages.success(request, "Medição apagada com sucesso.")
        return redirect("projetos:medicao:medicao_list")

    return render(
        request,
        "projetos/medicao_confirm_delete.html",
        {
            "medicao": medicao,
            "furo": medicao.furo,
        },
    )