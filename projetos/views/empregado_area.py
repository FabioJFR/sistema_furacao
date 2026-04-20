import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render

from projetos.decorators import empregado_required
from projetos.forms.empregado_area import MeusDadosEmpregadoForm
from projetos.models import (
    ConfiguracaoPerfuracaoEmpregado,
    DevolucaoMaterial,
    Empregados,
    LevantamentoMaterial,
    RegistoDiarioEmpregado,
)

logger = logging.getLogger("core")


# ---------------- HELPERS ----------------
def _obter_empregado_autenticado_area(request):
    logger.debug(
        "A resolver empregado autenticado em empregado_area.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    empregado = Empregados.objects.filter(user=request.user).select_related("empresa", "user").first()
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


# Multiempresa: a área pessoal do empregado só pode mostrar e editar dados da sua própria empresa.
@login_required
@empregado_required
def meus_dados_empregado(request):
    logger.info(
        "Entrada na view meus_dados_empregado. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_area(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view meus_dados_empregado. user_id=%s", request.user.id)
        return resposta_erro

    projetos_historico = (
        empregado.ligacoes_projetos
        .select_related("projeto")
        .filter(empresa=empregado.empresa)
        .order_by("-ativo", "-data_inicio")
    )

    furos_resumo = (
        RegistoDiarioEmpregado.objects
        .filter(
            empregado=empregado,
            empresa=empregado.empresa,
            furo__isnull=False,
        )
        .values("furo__id", "furo__nome", "projeto__nome")
        .annotate(
            total_metros=Sum("metros_furados"),
            total_horas=Sum("horas_trabalhadas"),
        )
        .order_by("-total_metros", "furo__nome")
    )

    context = {
        "empregado": empregado,
        "projetos_historico": projetos_historico,
        "furos_resumo": furos_resumo,
        "total_registos": RegistoDiarioEmpregado.objects.filter(
            empregado=empregado,
            empresa=empregado.empresa,
        ).count(),
        "total_levantamentos": LevantamentoMaterial.objects.filter(
            empregado=empregado,
            empresa=empregado.empresa,
        ).count(),
        "total_devolucoes": DevolucaoMaterial.objects.filter(
            empregado=empregado,
            empresa=empregado.empresa,
        ).count(),
        "total_configuracoes": ConfiguracaoPerfuracaoEmpregado.objects.filter(
            empregado=empregado,
            empresa=empregado.empresa,
        ).count(),
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