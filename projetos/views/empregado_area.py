import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from projetos.decorators import empregado_required
from projetos.forms.empregado_area import MeusDadosEmpregadoForm
from projetos.selectors.acesso import (
    obter_empregado_por_user,
    obter_individual_por_user,
)
from projetos.selectors.empregados import (
    obter_historico_projetos_empregado_area,
    obter_resumo_furos_empregado_area,
    obter_totais_empregado_area,
)

logger = logging.getLogger("core")


# ---------------- HELPERS ----------------
def _obter_empregado_autenticado_area(request):
    logger.debug(
        "A resolver empregado autenticado em empregado_area.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    empregado = obter_empregado_por_user(request.user)
    if not empregado:
        logger.warning(
            "Utilizador autenticado sem registo em Empregados em empregado_area.py. user_id=%s",
            request.user.id,
        )
        messages.error(
            request,
            "A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        )
        return None, redirect("projetos:redirect_after_login")

    if not empregado.empresa_id:
        logger.warning(
            "Empregado sem empresa associada em empregado_area.py. user_id=%s, empregado_id=%s",
            request.user.id,
            empregado.id,
        )
        messages.error(request, "A tua conta não está associada a uma empresa. Contacta o administrador.")
        return None, redirect("projetos:redirect_after_login")

    return empregado, None


def _obter_individual_autenticado_area(request):
    logger.debug(
        "A resolver individual autenticado em empregado_area.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    individual = obter_individual_por_user(request.user)
    if not individual:
        logger.warning(
            "Utilizador autenticado sem registo em Individual em empregado_area.py. user_id=%s",
            request.user.id,
        )
        messages.error(request, "A tua conta individual não está configurada corretamente.")
        return None, redirect("projetos:redirect_after_login")

    return individual, None


# Multiempresa: a área pessoal do empregado só pode mostrar e editar dados da sua própria empresa.
@login_required
@empregado_required
def meus_dados_empregado(request):
    logger.info(
        "Entrada na view meus_dados_empregado. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    perfil = getattr(request.user, "perfil_plataforma", None)
    if perfil and perfil.tipo_acesso == "individual":
        individual, resposta_erro = _obter_individual_autenticado_area(request)
        if resposta_erro:
            return resposta_erro

        context = {
            "individual": individual,
            "total_registos": individual.total_registos or 0,
            "total_horas": individual.total_horas or 0,
            "total_metros": individual.total_metros or 0,
        }
        return render(request, "projetos/meus_dados_individual.html", context)

    empregado, resposta_erro = _obter_empregado_autenticado_area(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view meus_dados_empregado. user_id=%s", request.user.id)
        return resposta_erro

    projetos_historico = obter_historico_projetos_empregado_area(empregado)
    furos_resumo = obter_resumo_furos_empregado_area(empregado)
    totais_area = obter_totais_empregado_area(empregado)

    context = {
        "empregado": empregado,
        "projetos_historico": projetos_historico,
        "furos_resumo": furos_resumo,
        **totais_area,
    }

    logger.info(
        "View meus_dados_empregado carregada com sucesso. user_id=%s, empregado_id=%s, total_registos=%s",
        request.user.id,
        empregado.id,
        context["total_registos"],
    )
    return render(request, "projetos/meus_dados_empregado.html", context)


@login_required
@empregado_required
def meus_dados_empregado_editar(request):
    logger.info(
        "Entrada na view meus_dados_empregado_editar. user_id=%s, username='%s', method=%s",
        request.user.id,
        request.user.username,
        request.method,
    )
    perfil = getattr(request.user, "perfil_plataforma", None)
    if perfil and perfil.tipo_acesso == "individual":
        from projetos.forms.empregado_area import MeusDadosIndividualForm

        individual, resposta_erro = _obter_individual_autenticado_area(request)
        if resposta_erro:
            return resposta_erro

        if request.method == "POST":
            form = MeusDadosIndividualForm(request.POST, request.FILES, instance=individual)
            if form.is_valid():
                individual = form.save(commit=False)
                individual.user = request.user
                individual.save()
                messages.success(request, "Os teus dados foram atualizados com sucesso.")
                return redirect("projetos:meus_dados_empregado")

            messages.error(request, "Erro ao atualizar os teus dados.")
        else:
            form = MeusDadosIndividualForm(instance=individual)

        return render(request, "projetos/meus_dados_individual_editar.html", {
            "individual": individual,
            "form": form,
        })

    empregado, resposta_erro = _obter_empregado_autenticado_area(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view meus_dados_empregado_editar. user_id=%s", request.user.id)
        return resposta_erro

    if request.method == "POST":
        form = MeusDadosEmpregadoForm(
            request.POST,
            request.FILES,
            instance=empregado,
        )
        if form.is_valid():
            empregado = form.save(commit=False)
            empregado.user = request.user
            empregado.empresa = empregado.empresa
            empregado.save()
            form.save_m2m()

            logger.info(
                "Dados do empregado atualizados com sucesso. user_id=%s, empregado_id=%s",
                request.user.id,
                empregado.id,
            )
            messages.success(request, "Os teus dados foram atualizados com sucesso.")
            return redirect("projetos:meus_dados_empregado")

        logger.warning(
            "Erro ao atualizar dados do empregado. user_id=%s, empregado_id=%s, erros=%s",
            request.user.id,
            empregado.id,
            form.errors,
        )
        messages.error(request, "Erro ao atualizar os teus dados.")
    else:
        form = MeusDadosEmpregadoForm(instance=empregado)

    return render(request, "projetos/meus_dados_empregado_editar.html", {
        "empregado": empregado,
        "form": form,
    })
