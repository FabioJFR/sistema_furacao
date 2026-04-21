import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.permissions import admin_required
from plataforma.models import PerfilPlataforma
from projetos.forms.empregado_furo import EmpregadoFuroForm
from projetos.models import EmpregadoFuro, Empregados, Furo
from projetos.services.empregados import garantir_ligacao_projeto_por_furo

logger = logging.getLogger("core")


ADMIN_TIPOS_ACESSO_EMPRESA = ["empresa_admin", "empresa_gestor"]


# ---------------- HELPERS ----------------
def _obter_contexto_admin_empregado_furo(request):
    logger.debug(
        "A resolver contexto administrativo em empregado_furo.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    perfil = PerfilPlataforma.objects.filter(
        user=request.user,
        ativo=True,
        tipo_acesso__in=ADMIN_TIPOS_ACESSO_EMPRESA,
    ).select_related("empresa").first()
    if perfil:
        logger.info(
            "Contexto administrativo resolvido via PerfilPlataforma em empregado_furo.py. user_id=%s, empresa_id=%s, tipo_acesso=%s",
            request.user.id,
            perfil.empresa_id,
            perfil.tipo_acesso,
        )
        return perfil

    logger.warning(
        "Falha ao resolver contexto administrativo em empregado_furo.py. user_id=%s",
        request.user.id,
    )
    return None



def _obter_empresa_admin_empregado_furo(request):
    contexto_admin = _obter_contexto_admin_empregado_furo(request)
    if not contexto_admin:
        messages.error(request, "Não tens permissão para aceder a esta área.")
        return None, redirect("projetos:redirect_after_login")

    empresa = getattr(contexto_admin, "empresa", None)
    empresa_id = getattr(contexto_admin, "empresa_id", None)

    if not empresa_id or not empresa:
        logger.warning(
            "Contexto administrativo sem empresa em empregado_furo.py. user_id=%s",
            request.user.id,
        )
        messages.error(request, "O utilizador administrador não está associado a uma empresa.")
        return None, redirect("projetos:dashboard")

    return empresa, None


# Multiempresa: a gestão de trabalhadores por furo deve acontecer sempre dentro da empresa do administrador.
@login_required
@admin_required
def furo_adicionar_empregado(request, furo_id):
    logger.info(
        "Entrada na view furo_adicionar_empregado. user_id=%s, username='%s', furo_id=%s, method=%s",
        request.user.id,
        request.user.username,
        furo_id,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregado_furo(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_adicionar_empregado. user_id=%s", request.user.id)
        return resposta_erro

    furo = get_object_or_404(Furo, pk=furo_id, empresa=empresa)

    if request.method == "POST":
        form = EmpregadoFuroForm(request.POST, empresa=empresa, furo=furo)
        form.instance.furo = furo
        form.instance.empresa = empresa
        empregado_id = request.POST.get("empregado")
        if empregado_id:
            form.instance.empregado_id = empregado_id
        if form.is_valid():
            empregado = form.cleaned_data["empregado"]
            ligacao = EmpregadoFuro.objects.create(
                empregado=empregado,
                furo=furo,
                funcao=form.cleaned_data["funcao"],
                data_inicio=form.cleaned_data.get("data_inicio"),
                data_fim=form.cleaned_data.get("data_fim"),
                ativo=form.cleaned_data.get("ativo", True),
                observacoes=form.cleaned_data.get("observacoes"),
                empresa=empresa,
            )
            ligacao_projeto, projeto_criado = garantir_ligacao_projeto_por_furo(
                empregado=empregado,
                furo=furo,
                empresa=empresa,
                data_inicio=form.cleaned_data.get("data_inicio"),
            )

            logger.info(
                "Trabalhador associado ao furo com sucesso. user_id=%s, empresa_id=%s, furo_id=%s, ligacao_id=%s, ligacao_projeto_id=%s, ligacao_projeto_criada=%s",
                request.user.id,
                empresa.id,
                furo.id,
                ligacao.id,
                ligacao_projeto.id,
                projeto_criado,
            )
            if projeto_criado:
                messages.success(request, "Trabalhador associado ao furo e automaticamente ligado ao projeto.")
            else:
                messages.success(request, "Trabalhador associado ao furo com sucesso.")
            return redirect(reverse("projetos:furo_detail", args=[furo.pk]))

        logger.warning(
            "Erro ao associar trabalhador ao furo. user_id=%s, furo_id=%s, erros=%s",
            request.user.id,
            furo_id,
            form.errors,
        )
        messages.error(request, "Erro ao associar trabalhador ao furo. Verifique os dados.")
    else:
        form = EmpregadoFuroForm(empresa=empresa, furo=furo)

    return render(request, "projetos/furo_adicionar_empregado.html", {
        "form": form,
        "furo": furo,
        "titulo": f"Adicionar Trabalhador ao Furo {furo.nome}"
    })


@login_required
@admin_required
def furo_editar_empregado(request, pk):
    logger.info(
        "Entrada na view furo_editar_empregado. user_id=%s, username='%s', ligacao_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregado_furo(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_editar_empregado. user_id=%s", request.user.id)
        return resposta_erro

    ligacao = get_object_or_404(
        EmpregadoFuro.objects.select_related("furo", "empregado"),
        pk=pk,
        empresa=empresa,
    )

    if request.method == "POST":
        form = EmpregadoFuroForm(
            request.POST,
            instance=ligacao,
            empresa=empresa,
            furo=ligacao.furo,
        )
        form.instance.furo = ligacao.furo
        form.instance.empresa = empresa
        empregado_id = request.POST.get("empregado")
        if empregado_id:
            form.instance.empregado_id = empregado_id
        if form.is_valid():
            empregado = form.cleaned_data["empregado"]
            ligacao.empregado = empregado
            ligacao.funcao = form.cleaned_data["funcao"]
            ligacao.data_inicio = form.cleaned_data.get("data_inicio")
            ligacao.data_fim = form.cleaned_data.get("data_fim")
            ligacao.ativo = form.cleaned_data.get("ativo", ligacao.ativo)
            ligacao.observacoes = form.cleaned_data.get("observacoes")
            ligacao.empresa = empresa
            ligacao.save()
            ligacao_projeto, projeto_criado = garantir_ligacao_projeto_por_furo(
                empregado=empregado,
                furo=ligacao.furo,
                empresa=empresa,
                data_inicio=form.cleaned_data.get("data_inicio"),
            )
            logger.info(
                "Ligação trabalhador/furo atualizada com sucesso. user_id=%s, empresa_id=%s, ligacao_id=%s, furo_id=%s, ligacao_projeto_id=%s, ligacao_projeto_criada=%s",
                request.user.id,
                empresa.id,
                ligacao.id,
                ligacao.furo.pk,
                ligacao_projeto.id,
                projeto_criado,
            )
            if projeto_criado:
                messages.success(request, "Ligação trabalhador/furo atualizada e projeto associado automaticamente.")
            else:
                messages.success(request, "Ligação trabalhador/furo atualizada com sucesso.")
            return redirect(reverse("projetos:furo_detail", args=[ligacao.furo.pk]))

        logger.warning(
            "Erro ao atualizar ligação trabalhador/furo. user_id=%s, ligacao_pk=%s, erros=%s",
            request.user.id,
            pk,
            form.errors,
        )
        messages.error(request, "Erro ao atualizar ligação trabalhador/furo. Verifique os dados.")
    else:
        form = EmpregadoFuroForm(
            instance=ligacao,
            empresa=empresa,
            furo=ligacao.furo,
        )

    return render(request, "projetos/furo_adicionar_empregado.html", {
        "form": form,
        "furo": ligacao.furo,
        "ligacao": ligacao,
        "titulo": f"Editar Trabalhador no Furo {ligacao.furo.nome}"
    })


@login_required
@admin_required
def furo_remover_empregado(request, pk):
    logger.info(
        "Entrada na view furo_remover_empregado. user_id=%s, username='%s', ligacao_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregado_furo(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_remover_empregado. user_id=%s", request.user.id)
        return resposta_erro

    ligacao = get_object_or_404(
        EmpregadoFuro.objects.select_related("furo", "empregado"),
        pk=pk,
        empresa=empresa,
    )
    furo = ligacao.furo

    if request.method == "POST":
        ligacao_id = ligacao.id
        ligacao.delete()
        logger.info(
            "Trabalhador removido do furo com sucesso. user_id=%s, empresa_id=%s, ligacao_id=%s, furo_id=%s",
            request.user.id,
            empresa.id,
            ligacao_id,
            furo.pk,
        )
        messages.success(request, "Trabalhador removido do furo com sucesso.")
        return redirect(reverse("projetos:furo_detail", args=[furo.pk]))

    return render(request, "projetos/furo_remover_empregado.html", {
        "ligacao": ligacao,
        "furo": furo,
    })
