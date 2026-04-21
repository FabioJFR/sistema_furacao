import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from core.permissions import admin_required
from ..decorators import empregado_required

from plataforma.models import PerfilPlataforma
from projetos.forms.registo import (
    RegistoDiarioEmpregadoAdminForm,
    RegistoDiarioEmpregadoForm,
)
from projetos.models import (
    Empregados,
    Furo,
    Projeto,
    RegistoDiarioEmpregado,
    RegistoDiarioFotoAmostra,
)
from projetos.services.registos import criar_registo_diario, atualizar_registo_diario
from ..services.empregados import recalcular_resumo_empregado
from ..services.furos import recalcular_resumo_furo

logger = logging.getLogger("core")


ADMIN_TIPOS_ACESSO_EMPRESA = ["empresa_admin", "empresa_gestor"]


# -------- REGISTOS --------------


# ---------------- HELPERS ----------------
def _obter_contexto_admin_registos(request):
    logger.debug(
        "A resolver contexto administrativo em registos.py. user_id=%s, username='%s'",
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
            "Contexto administrativo resolvido via PerfilPlataforma em registos.py. user_id=%s, empresa_id=%s, tipo_acesso=%s",
            request.user.id,
            perfil.empresa_id,
            perfil.tipo_acesso,
        )
        return perfil

    logger.warning(
        "Falha ao resolver contexto administrativo em registos.py. user_id=%s",
        request.user.id,
    )
    return None



def _obter_empresa_admin_registos(request):
    contexto_admin = _obter_contexto_admin_registos(request)
    if not contexto_admin:
        messages.error(request, "Não tens permissão para aceder a esta área.")
        return None, redirect("projetos:dashboard_projetos:redirect_after_login")

    empresa = getattr(contexto_admin, "empresa", None)
    empresa_id = getattr(contexto_admin, "empresa_id", None)

    if not empresa_id or not empresa:
        logger.warning(
            "Contexto administrativo sem empresa em registos.py. user_id=%s",
            request.user.id,
        )
        messages.error(request, "O utilizador administrador não está associado a uma empresa.")
        return None, redirect("projetos:dashboard_projetos:dashboard")

    return empresa, None



def _obter_empregado_autenticado_registos(request):
    logger.debug(
        "A resolver empregado autenticado em registos.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    empregado = Empregados.objects.filter(user=request.user).select_related("empresa").first()
    if not empregado:
        logger.warning(
            "Utilizador autenticado sem registo em Empregados em registos.py. user_id=%s",
            request.user.id,
        )
        messages.error(
            request,
            "A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        )
        return None, redirect("projetos:dashboard_projetos:redirect_after_login")

    if not empregado.empresa_id:
        logger.warning(
            "Empregado sem empresa associada em registos.py. user_id=%s, empregado_id=%s",
            request.user.id,
            empregado.id,
        )
        messages.error(request, "A tua conta não está associada a uma empresa. Contacta o administrador.")
        return None, redirect("projetos:dashboard_projetos:redirect_after_login")

    return empregado, None


@login_required
@empregado_required
def criar_registo_view(request):
    logger.info(
        "Entrada na view criar_registo_view. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    messages.info(
        request,
        "Este atalho antigo foi descontinuado. Use o formulário completo de registo diário."
    )
    return redirect("projetos:registos:create")


@login_required
@empregado_required
def registo_diario_list(request):
    logger.info(
        "Entrada na view registo_diario_list. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_registos(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view registo_diario_list. user_id=%s", request.user.id)
        return resposta_erro

    registos = empregado.registos_diarios.select_related("projeto", "furo").filter(
        empresa_id=empregado.empresa_id
    )

    logger.info(
        "View registo_diario_list carregada com sucesso. user_id=%s, empregado_id=%s, total_registos=%s",
        request.user.id,
        empregado.id,
        registos.count() if hasattr(registos, "count") else "n/a",
    )
    return render(
        request,
        "projetos/registo_diario_list.html",
        {
            "empregado": empregado,
            "registos": registos,
        },
    )


@login_required
@empregado_required
def registo_diario_create(request):
    logger.info(
        "Entrada na view registo_diario_create. user_id=%s, username='%s', method=%s",
        request.user.id,
        request.user.username,
        request.method,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_registos(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view registo_diario_create. user_id=%s", request.user.id)
        return resposta_erro

    if request.method == "POST":
        form = RegistoDiarioEmpregadoForm(
            request.POST,
            request.FILES,
            empregado=empregado,
        )
        form.instance.empregado = empregado
        form.instance.empresa = empregado.empresa

        if form.is_valid():
            registo = criar_registo_diario(form=form, empregado=empregado)

            fotos_amostra = request.FILES.getlist("fotos_amostra")
            for foto in fotos_amostra:
                RegistoDiarioFotoAmostra.objects.create(
                    registo=registo,
                    empresa=empregado.empresa,
                    imagem=foto,
                )

            logger.info(
                "Registo diário criado com sucesso. user_id=%s, empregado_id=%s, registo_id=%s",
                request.user.id,
                empregado.id,
                registo.id,
            )
            messages.success(request, "Registo diário guardado com sucesso.")
            return redirect("projetos:area_empregado")

        logger.warning(
            "Erro ao guardar registo diário. user_id=%s, empregado_id=%s, erros=%s",
            request.user.id,
            empregado.id,
            form.errors,
        )
        messages.error(request, "Erro ao guardar o registo diário. Verifique os dados.")
    else:
        form = RegistoDiarioEmpregadoForm(
            empregado=empregado,
            initial={"data": timezone.now().date()},
        )
        form.instance.empregado = empregado
        form.instance.empresa = empregado.empresa

    return render(
        request,
        "projetos/registo_diario_form.html",
        {
            "form": form,
            "empregado": empregado,
            "titulo": "Novo Registo Diário",
        },
    )


@login_required
@empregado_required
def registo_diario_update(request, pk):
    logger.info(
        "Entrada na view registo_diario_update. user_id=%s, username='%s', registo_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empregado, resposta_erro = _obter_empregado_autenticado_registos(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view registo_diario_update. user_id=%s", request.user.id)
        return resposta_erro

    registo = get_object_or_404(
        RegistoDiarioEmpregado,
        pk=pk,
        empregado=empregado,
        empresa_id=empregado.empresa_id,
    )

    furo_antigo = registo.furo

    if request.method == "POST":
        form = RegistoDiarioEmpregadoForm(
            request.POST,
            request.FILES,
            instance=registo,
            empregado=empregado,
        )
        form.instance.empregado = empregado
        form.instance.empresa = empregado.empresa

        if form.is_valid():
            registo.editado_por_empregado = True
            registo.editado_em = timezone.now()
            registo = atualizar_registo_diario(registo, form)

            fotos_amostra = request.FILES.getlist("fotos_amostra")
            for foto in fotos_amostra:
                RegistoDiarioFotoAmostra.objects.create(
                    registo=registo,
                    empresa_id=empregado.empresa_id,
                    imagem=foto,
                )

            recalcular_resumo_empregado(empregado, empresa=empregado.empresa)

            if furo_antigo:
                recalcular_resumo_furo(furo_antigo)

            if registo.furo:
                recalcular_resumo_furo(registo.furo)

            logger.info(
                "Registo diário atualizado com sucesso por empregado. user_id=%s, empregado_id=%s, registo_id=%s",
                request.user.id,
                empregado.id,
                registo.id,
            )
            messages.success(request, "Registo diário atualizado com sucesso.")
            return redirect("projetos:registo_diario_list")

        logger.warning(
            "Erro ao atualizar registo diário por empregado. user_id=%s, registo_pk=%s, erros=%s",
            request.user.id,
            pk,
            form.errors,
        )
        messages.error(request, "Erro ao atualizar o registo diário.")
    else:
        form = RegistoDiarioEmpregadoForm(instance=registo, empregado=empregado)
        form.instance.empregado = empregado
        form.instance.empresa = empregado.empresa

    return render(
        request,
        "projetos/registo_diario_form.html",
        {
            "form": form,
            "empregado": empregado,
            "titulo": "Editar Registo Diário",
            "registo": registo,
        },
    )


# Multiempresa: o administrador só pode listar registos da sua própria empresa.
@login_required
@admin_required
def registos_admin_list(request):
    logger.info(
        "Entrada na view registos_admin_list. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empresa, resposta_erro = _obter_empresa_admin_registos(request)
    empresa_id = getattr(empresa, "pk", empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view registos_admin_list. user_id=%s", request.user.id)
        return resposta_erro

    registos = RegistoDiarioEmpregado.objects.select_related(
        "empregado",
        "projeto",
        "furo",
    ).filter(
        empresa_id=empresa_id,
        empregado__empresa_id=empresa_id,
    )

    empregado_id = request.GET.get("empregado")
    projeto_id = request.GET.get("projeto")
    furo_id = request.GET.get("furo")
    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")

    if empregado_id:
        registos = registos.filter(empregado_id=empregado_id)

    if projeto_id:
        registos = registos.filter(projeto_id=projeto_id)

    if furo_id:
        registos = registos.filter(furo_id=furo_id)

    if data_inicio:
        data_inicio_parsed = parse_date(data_inicio)
        if data_inicio_parsed:
            registos = registos.filter(data__gte=data_inicio_parsed)

    if data_fim:
        data_fim_parsed = parse_date(data_fim)
        if data_fim_parsed:
            registos = registos.filter(data__lte=data_fim_parsed)

    totais = registos.aggregate(
        total_horas=Sum("horas_trabalhadas"),
        total_metros=Sum("metros_furados"),
        total_paragem=Sum("horas_paragem"),
    )

    empregados = Empregados.objects.filter(empresa_id=empresa_id).order_by("nome")
    projetos = Projeto.objects.filter(empresa_id=empresa_id).order_by("nome")
    furos = Furo.objects.filter(empresa_id=empresa_id).order_by("nome")

    logger.info(
        "View registos_admin_list carregada com sucesso. user_id=%s, empresa_id=%s, total_registos=%s",
        request.user.id,
        empresa.id,
        registos.count() if hasattr(registos, "count") else "n/a",
    )
    return render(
        request,
        "projetos/registos_admin_list.html",
        {
            "registos": registos,
            "empregados": empregados,
            "projetos": projetos,
            "furos": furos,
            "filtros": {
                "empregado": empregado_id or "",
                "projeto": projeto_id or "",
                "furo": furo_id or "",
                "data_inicio": data_inicio or "",
                "data_fim": data_fim or "",
            },
            "total_horas": totais["total_horas"] or 0,
            "total_metros": totais["total_metros"] or 0,
            "total_paragem": totais["total_paragem"] or 0,
        },
    )


@login_required
@admin_required
def registo_admin_update(request, pk):
    logger.info(
        "Entrada na view registo_admin_update. user_id=%s, username='%s', registo_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_registos(request)
    empresa_id = getattr(empresa, "pk", empresa) if empresa is not None else None
    if resposta_erro:
        logger.warning("Acesso bloqueado na view registo_admin_update. user_id=%s", request.user.id)
        return resposta_erro

    registo = get_object_or_404(
        RegistoDiarioEmpregado.objects.select_related("empregado", "projeto", "furo"),
        pk=pk,
        empresa_id=empresa_id,
        empregado__empresa_id=empresa_id,
    )

    if request.method == "POST":
        form = RegistoDiarioEmpregadoAdminForm(
            request.POST,
            request.FILES,
            instance=registo,
        )

        if form.is_valid():
            atualizar_registo_diario(registo, form)
            recalcular_resumo_empregado(registo.empregado, empresa=empresa)

            fotos_amostra = request.FILES.getlist("fotos_amostra")
            for foto in fotos_amostra:
                RegistoDiarioFotoAmostra.objects.create(
                    registo=registo,
                    empresa_id=empresa_id,
                    imagem=foto,
                )

            logger.info(
                "Registo corrigido com sucesso por admin. user_id=%s, empresa_id=%s, registo_id=%s",
                request.user.id,
                empresa.id,
                registo.id,
            )
            messages.success(request, "Registo corrigido com sucesso.")
            return redirect("projetos:registos_admin_list")

        logger.warning(
            "Erro ao corrigir registo por admin. user_id=%s, registo_pk=%s, erros=%s",
            request.user.id,
            pk,
            form.errors,
        )
        messages.error(request, "Erro ao corrigir o registo.")
    else:
        form = RegistoDiarioEmpregadoAdminForm(instance=registo)

    return render(
        request,
        "projetos/registo_admin_form.html",
        {
            "form": form,
            "registo": registo,
            "titulo": "Corrigir Registo de Produção",
        },
    )
