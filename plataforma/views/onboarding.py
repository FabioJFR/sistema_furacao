import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from plataforma.decorators import platform_admin_required
from plataforma.forms.onboarding import OnboardingEmpresaForm
from plataforma import selectors
from plataforma.services.onboarding import criar_empresa_com_admin


logger = logging.getLogger("core")


# TODO futuro:
# - adicionar auditoria detalhada do onboarding
# - permitir convite por email em vez de password manual
# - reservar partes sensíveis do onboarding apenas ao platform_owner, se necessário


@platform_admin_required
@login_required
def onboarding_empresa(request):
    logger.info(
        "Entrada em onboarding_empresa. user_id=%s, method=%s",
        getattr(request.user, "id", None),
        request.method,
    )

    if request.method == "POST":
        form = OnboardingEmpresaForm(request.POST)

        logger.info(
            "POST recebido em onboarding_empresa. nome_empresa=%r, email_admin=%r, tipo_acesso=%r, criar_subscricao_inicial=%r",
            request.POST.get("nome_empresa"),
            request.POST.get("email_admin"),
            request.POST.get("tipo_acesso"),
            request.POST.get("criar_subscricao_inicial"),
        )

        if form.is_valid():
            logger.info(
                "Formulário de onboarding_empresa válido. user_id=%s, nome_empresa=%r, email_admin=%r",
                getattr(request.user, "id", None),
                form.cleaned_data.get("nome_empresa"),
                form.cleaned_data.get("email_admin"),
            )

            try:
                resultado = criar_empresa_com_admin(
                    nome_empresa=form.cleaned_data["nome_empresa"],
                    nome_admin=form.cleaned_data["nome_admin"],
                    email_admin=form.cleaned_data["email_admin"],
                    password_admin=form.cleaned_data["password_admin"],
                    username_admin=form.cleaned_data.get("username_admin"),
                    nif=form.cleaned_data.get("nif"),
                    telefone=form.cleaned_data.get("telefone"),
                    morada=form.cleaned_data.get("morada"),
                    pais=form.cleaned_data.get("pais"),
                    cidade=form.cleaned_data.get("cidade"),
                    observacoes=form.cleaned_data.get("observacoes"),
                    plano=form.cleaned_data.get("plano"),
                    ciclo_subscricao=form.cleaned_data.get("ciclo_subscricao") or "mensal",
                    tipo_acesso=form.cleaned_data.get("tipo_acesso") or "empresa_admin",
                    estado_empresa=form.cleaned_data.get("estado_empresa") or "teste",
                    ativa=True,
                    criar_subscricao_inicial=form.cleaned_data.get("criar_subscricao_inicial") or False,
                    valor_subscricao=form.cleaned_data.get("valor_subscricao"),
                    criar_pagamento_inicial=False,
                    valor_pagamento=None,
                )

                empresa = resultado["empresa"]
                user_admin = resultado["user_admin"]

                logger.info(
                    "Onboarding de empresa concluído com sucesso. empresa_id=%s, empresa_nome=%r, user_admin_id=%s, user_admin_username=%r",
                    getattr(empresa, "id", None),
                    getattr(empresa, "nome", None),
                    getattr(user_admin, "id", None),
                    getattr(user_admin, "username", None),
                )

                messages.success(
                    request,
                    f"Empresa '{empresa.nome}' criada com sucesso. Administrador inicial: {user_admin.username}"
                )
                return redirect("plataforma:onboarding_empresa")

            except Exception as e:
                logger.error(
                    "Erro ao criar empresa no onboarding. user_id=%s, erro=%s",
                    getattr(request.user, "id", None),
                    e,
                    exc_info=True,
                )
                messages.error(request, f"Erro ao criar empresa: {e}")
        else:
            logger.warning(
                "Formulário onboarding_empresa inválido. user_id=%s, erros=%s",
                getattr(request.user, "id", None),
                form.errors.as_json(),
            )
            messages.error(request, "Existem erros no formulário. Verifique os campos.")
    else:
        form = OnboardingEmpresaForm()
        logger.debug(
            "Formulário onboarding_empresa aberto em GET. user_id=%s",
            getattr(request.user, "id", None),
        )

    planos = selectors.listar_planos_ativos()
    planos_periodos, planos_precos = selectors.construir_planos_periodos_precos(planos)

    return render(request, "plataforma/onboarding_empresa.html", {
        "form": form,
        "titulo": "Onboarding de Empresa",
        "planos_periodos": planos_periodos,
        "planos_precos": planos_precos,
    })
