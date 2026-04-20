import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Count, Sum

from django.urls import reverse

from projetos.models import (
    Empregados,
    Projeto,
    Furo,
    Material,
    EmpregadoFuro,
    EmpregadoProjeto,
    EmpregadoFicheiro,
    Medicao,
    RegistoDiarioEmpregado,
)
from ..decorators import admin_required, empregado_required
from ..forms.empregado import (
    EmpregadoCreateForm,
    EmpregadoFicheiroForm,
    EmpregadoProjetoForm,
    EmpregadoRegistroForm,
    EmpregadoUpdateForm,
)
from projetos.forms.configuracao_perfuracao import ConfiguracaoPerfuracaoEmpregadoForm
from projetos.models import ConfiguracaoPerfuracaoEmpregado
from projetos.selectors.configuracao_perfuracao import (
    obter_lista_configuracoes_perfuracao_empregado,
)
from projetos.selectors.empregados import (
    obter_empregados_pendentes,
    obter_lista_empregados,
)
from projetos.services.empregados import (
    aprovar_empregado,
    empregado_ja_tem_projeto_ativo,
    terminar_ligacao_projeto_empregado,
)

from plataforma.models import PerfilPlataforma

logger = logging.getLogger("core")


ADMIN_TIPOS_ACESSO_EMPRESA = ["empresa_admin", "empresa_gestor"]


# ---------------- HELPERS ----------------
def _obter_contexto_admin_empregados(request):
    logger.debug(
        "A resolver contexto administrativo em empregados.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    admin_empregado = Empregados.objects.filter(user=request.user).select_related("empresa").first()
    if admin_empregado:
        logger.info(
            "Contexto administrativo resolvido via Empregados em empregados.py. user_id=%s, empresa_id=%s",
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
            "Contexto administrativo resolvido via PerfilPlataforma em empregados.py. user_id=%s, empresa_id=%s, tipo_acesso=%s",
            request.user.id,
            perfil.empresa_id,
            perfil.tipo_acesso,
        )
        return perfil

    logger.warning(
        "Falha ao resolver contexto administrativo em empregados.py. user_id=%s",
        request.user.id,
    )
    return None



def _obter_empresa_admin_empregados(request):
    contexto_admin = _obter_contexto_admin_empregados(request)
    if not contexto_admin:
        messages.error(request, "Não tens permissão para aceder a esta área.")
        return None, redirect("projetos:redirect_after_login")

    empresa = getattr(contexto_admin, "empresa", None)
    empresa_id = getattr(contexto_admin, "empresa_id", None)

    if not empresa_id or not empresa:
        logger.warning(
            "Contexto administrativo sem empresa em empregados.py. user_id=%s",
            request.user.id,
        )
        messages.error(request, "O utilizador administrador não está associado a uma empresa.")
        return None, redirect("projetos:dashboard")

    return empresa, None



def _obter_empregado_autenticado(request):
    logger.debug(
        "A resolver empregado autenticado em empregados.py. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )

    empregado = _resolver_empregado_por_user_ou_email(request.user)
    if not empregado:
        logger.warning(
            "Utilizador autenticado sem registo em Empregados em empregados.py. user_id=%s",
            request.user.id,
        )
        messages.error(
            request,
            "A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        )
        return None, redirect("projetos:redirect_after_login")

    if not empregado.empresa_id:
        logger.warning(
            "Empregado sem empresa associada em empregados.py. user_id=%s, empregado_id=%s",
            request.user.id,
            empregado.id,
        )
        messages.error(request, "A tua conta não está associada a uma empresa. Contacta o administrador.")
        return None, redirect("projetos:redirect_after_login")

    return empregado, None

# Helper: resolve empregado por user ou email
def _resolver_empregado_por_user_ou_email(user):
    empregado = Empregados.objects.filter(user=user).select_related("empresa").first()
    if empregado:
        return empregado

    email = (getattr(user, "email", "") or "").strip()
    if not email:
        return None

    candidatos = Empregados.objects.filter(
        email__iexact=email,
        user__isnull=True,
    ).select_related("empresa")

    total_candidatos = candidatos.count()
    if total_candidatos != 1:
        logger.warning(
            "Fallback por email não aplicado em empregados.py. user_id=%s, email='%s', total_candidatos=%s",
            getattr(user, "id", None),
            email,
            total_candidatos,
        )
        return None

    empregado = candidatos.first()
    empregado.user = user
    empregado.save(update_fields=["user"])

    logger.warning(
        "Ligação automática User -> Empregados executada em empregados.py. user_id=%s, empregado_id=%s, empresa_id=%s, email='%s'",
        user.id,
        empregado.id,
        empregado.empresa_id,
        email,
    )
    return empregado

# ---------------- EMPREGADOS ----------------
# TODO futuro:
# - quando o fluxo multiempresa estiver fechado, associar o registo inicial a uma empresa/contexto controlado
# - validar convites ou código da empresa no onboarding, se essa regra for adotada
def registo_empregado(request):
    logger.info(
        "Entrada na view registo_empregado. method=%s, authenticated=%s",
        request.method,
        request.user.is_authenticated,
    )
    if request.method == "POST":
        form = EmpregadoRegistroForm(request.POST)
        if form.is_valid():
            logger.info("Formulário de registo de empregado válido. email='%s'", form.cleaned_data.get("email"))
            user = form.save(commit=False)
            user.email = form.cleaned_data["email"]
            user.is_active = False
            user.save()

            Empregados.objects.create(
                user=user,
                nome=form.cleaned_data["nome"],
                email=form.cleaned_data["email"],
                telefone=form.cleaned_data.get("telefone"),
                funcao=form.cleaned_data.get("funcao"),
                aprovado=False,
            )

            messages.success(
                request,
                "Registo enviado com sucesso. Aguarde aprovação do administrador para receber acesso à plataforma.",
            )
            return redirect("login")
        else:
            messages.error(request, "Existem erros no formulário. Corrija os campos assinalados.")
            logger.warning("Erros no formulário de registo de empregado: %s", form.errors)
    else:
        form = EmpregadoRegistroForm()

    logger.info("Render da view registo_empregado concluído.")
    return render(request, "projetos/registo_empregado.html", {
        "form": form,
        "titulo": "Registo de Empregado",
    })


@login_required
@admin_required
def empregado_list(request):
    logger.info(
        "Entrada na view empregado_list. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_list. user_id=%s", request.user.id)
        return resposta_erro

    empregados = obter_lista_empregados(empresa=empresa)
    logger.info(
        "View empregado_list carregada com sucesso. user_id=%s, empresa_id=%s, total_empregados=%s",
        request.user.id,
        empresa.id,
        empregados.count() if hasattr(empregados, "count") else "n/a",
    )
    return render(request, "projetos/empregado_list.html", {
        "empregados": empregados,
    })


@login_required
@admin_required
def empregado_create(request):
    logger.info(
        "Entrada na view empregado_create. user_id=%s, username='%s', method=%s",
        request.user.id,
        request.user.username,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_create. user_id=%s", request.user.id)
        return resposta_erro

    form = EmpregadoCreateForm(
        request.POST or None,
        request.FILES or None,
        empresa=empresa,
    )

    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                username = form.cleaned_data["username"]
                password = form.cleaned_data["password"]

                user = User.objects.create_user(
                    username=username,
                    email=form.cleaned_data.get("email") or "",
                    password=password,
                    first_name=(form.cleaned_data.get("nome") or "").split(" ")[0],
                    is_active=True,
                )

                empregado = form.save(commit=False)
                empregado.user = user
                empregado.empresa = empresa
                empregado.aprovado = True
                if not empregado.data_aprovacao:
                    empregado.data_aprovacao = timezone.now()
                empregado.save()
                form.save_m2m()
                logger.info(
                    "Ligação criada em empregado_create. user_id=%s, empregado_id=%s, empregado_user_id=%s, empresa_id=%s",
                    user.id,
                    empregado.id,
                    empregado.user_id,
                    empregado.empresa_id,
                )

            logger.info(
                "Empregado criado com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s, novo_username='%s'",
                request.user.id,
                empresa.id,
                empregado.id,
                user.username,
            )
            messages.success(
                request,
                f"Empregado criado com sucesso. Utilizador: {user.username}",
            )
            return redirect(reverse("projetos:empregado_detail", args=[empregado.id]))
        except Exception as e:
            logger.exception(
                "Erro ao criar empregado com utilizador. admin_user_id=%s, empresa_id=%s, erro=%s",
                request.user.id,
                empresa.id,
                e,
            )
            messages.error(request, "Erro ao criar empregado. Verifique os dados e tente novamente.")

    if request.method == "POST":
        logger.warning("Formulário inválido em empregado_create. user_id=%s, erros=%s", request.user.id, form.errors)

    return render(request, "projetos/empregado_form.html", {
        "form": form,
        "titulo": "Novo Empregado",
    })


@login_required
@admin_required
def empregado_detail(request, pk):
    logger.info(
        "Entrada na view empregado_detail. user_id=%s, username='%s', empregado_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_detail. user_id=%s", request.user.id)
        return resposta_erro

    empregado = get_object_or_404(Empregados, pk=pk, empresa=empresa)
    logger.info(
        "View empregado_detail carregada com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s",
        request.user.id,
        empresa.id,
        empregado.id,
    )
    return render(request, "projetos/empregado_detail.html", {
        "empregado": empregado,
    })


@login_required
@admin_required
def empregado_update(request, pk):
    logger.info(
        "Entrada na view empregado_update. user_id=%s, username='%s', empregado_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_update. user_id=%s", request.user.id)
        return resposta_erro

    empregado = get_object_or_404(Empregados, pk=pk, empresa=empresa)

    if request.method == "POST":
        form = EmpregadoUpdateForm(
            request.POST,
            request.FILES,
            instance=empregado,
            empresa=empresa,
        )
        if form.is_valid():
            empregado = form.save(commit=False)
            empregado.empresa = empresa
            empregado.save()
            form.save_m2m()
            logger.info(
                "Empregado atualizado com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s",
                request.user.id,
                empresa.id,
                empregado.id,
            )
            messages.success(request, "Empregado atualizado com sucesso.")
            return redirect(reverse("projetos:empregado_detail", args=[empregado.id]))

        logger.warning("Erro ao atualizar empregado. user_id=%s, empregado_pk=%s, erros=%s", request.user.id, pk, form.errors)
        messages.error(request, "Erro ao atualizar empregado. Verifique os dados.")
    else:
        form = EmpregadoUpdateForm(instance=empregado, empresa=empresa)

    return render(request, "projetos/empregado_form.html", {
        "form": form,
        "titulo": "Editar Empregado",
        "empregado": empregado,
    })


@login_required
@admin_required
def empregado_delete(request, pk):
    logger.info(
        "Entrada na view empregado_delete. user_id=%s, username='%s', empregado_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_delete. user_id=%s", request.user.id)
        return resposta_erro

    empregado = get_object_or_404(Empregados, pk=pk, empresa=empresa)

    if request.method == "POST":
        empregado_id = empregado.id
        empregado.delete()
        logger.info(
            "Empregado apagado com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s",
            request.user.id,
            empresa.id,
            empregado_id,
        )
        messages.success(request, "Empregado apagado com sucesso.")
        return redirect(reverse("projetos:empregado_list"))

    return render(request, "projetos/empregado_confirm_delete.html", {
        "empregado": empregado,
    })


@login_required
@admin_required
def empregado_adicionar_projeto(request, pk):
    logger.info(
        "Entrada na view empregado_adicionar_projeto. user_id=%s, username='%s', empregado_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_adicionar_projeto. user_id=%s", request.user.id)
        return resposta_erro

    empregado = get_object_or_404(Empregados, pk=pk, empresa=empresa)

    if request.method == "POST":
        form = EmpregadoProjetoForm(request.POST, empresa=empresa, empregado=empregado)
        if form.is_valid():
            ligacao = form.save(commit=False)
            ligacao.empregado = empregado
            ligacao.empresa = empresa

            existe_ativa = EmpregadoProjeto.objects.filter(
                empregado=empregado,
                projeto=ligacao.projeto,
                ativo=True,
                empresa=empresa,
            ).exists()

            if ligacao.ativo and existe_ativa:
                logger.warning(
                    "Tentativa de associação duplicada ativa em empregado_adicionar_projeto. user_id=%s, empregado_id=%s, projeto_id=%s",
                    request.user.id,
                    empregado.id,
                    ligacao.projeto_id,
                )
                form.add_error("projeto", "Este empregado já está associado de forma ativa a este projeto.")
            else:
                ligacao.save()
                logger.info(
                    "Projeto associado ao empregado com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s, ligacao_id=%s",
                    request.user.id,
                    empresa.id,
                    empregado.id,
                    ligacao.id,
                )
                messages.success(request, "Projeto associado ao empregado com sucesso.")
                return redirect(reverse("projetos:empregado_detail", args=[empregado.id]))
        else:
            logger.warning(
                "Erro ao associar projeto ao empregado. user_id=%s, empregado_pk=%s, erros=%s",
                request.user.id,
                pk,
                form.errors,
            )
            messages.error(request, "Erro ao associar projeto. Verifique os dados.")
    else:
        form = EmpregadoProjetoForm(empresa=empresa, empregado=empregado)

    return render(request, "projetos/empregado_projeto_form.html", {
        "form": form,
        "empregado": empregado,
        "titulo": "Associar Projeto ao Empregado",
    })


@login_required
@admin_required
def empregado_editar_projeto(request, pk, ligacao_id):
    logger.info(
        "Entrada na view empregado_editar_projeto. user_id=%s, username='%s', empregado_pk=%s, ligacao_id=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        ligacao_id,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_editar_projeto. user_id=%s", request.user.id)
        return resposta_erro

    empregado = get_object_or_404(Empregados, pk=pk, empresa=empresa)
    ligacao = get_object_or_404(
        EmpregadoProjeto,
        id=ligacao_id,
        empregado=empregado,
        empresa=empresa,
    )

    if request.method == "POST":
        form = EmpregadoProjetoForm(
            request.POST,
            instance=ligacao,
            empresa=empresa,
            empregado=empregado,
        )
        if form.is_valid():
            nova_ligacao = form.save(commit=False)
            nova_ligacao.empregado = empregado
            nova_ligacao.empresa = empresa

            existe_ativa = empregado_ja_tem_projeto_ativo(
                empregado=empregado,
                projeto=nova_ligacao.projeto,
                excluir_ligacao_id=ligacao.id,
                empresa=empresa,
            )

            if nova_ligacao.ativo and existe_ativa:
                logger.warning(
                    "Tentativa de edição com associação ativa duplicada em empregado_editar_projeto. user_id=%s, empregado_id=%s, projeto_id=%s",
                    request.user.id,
                    empregado.id,
                    nova_ligacao.projeto_id,
                )
                form.add_error("projeto", "Este empregado já está associado de forma ativa a este projeto.")
            else:
                nova_ligacao.save()
                logger.info(
                    "Ligação projeto/empregado atualizada com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s, ligacao_id=%s",
                    request.user.id,
                    empresa.id,
                    empregado.id,
                    nova_ligacao.id,
                )
                messages.success(request, "Ligação projeto/empregado atualizada com sucesso.")
                return redirect(reverse("projetos:empregado_detail", args=[empregado.id]))
        else:
            logger.warning(
                "Erro ao atualizar ligação projeto/empregado. user_id=%s, empregado_pk=%s, ligacao_id=%s, erros=%s",
                request.user.id,
                pk,
                ligacao_id,
                form.errors,
            )
            messages.error(request, "Erro ao atualizar ligação. Verifique os dados.")
    else:
        form = EmpregadoProjetoForm(
            instance=ligacao,
            empresa=empresa,
            empregado=empregado,
        )

    return render(request, "projetos/empregado_projeto_form.html", {
        "form": form,
        "empregado": empregado,
        "titulo": "Editar Ligação de Projeto",
    })


@login_required
@admin_required
def empregado_terminar_projeto(request, pk, ligacao_id):
    logger.info(
        "Entrada na view empregado_terminar_projeto. user_id=%s, username='%s', empregado_pk=%s, ligacao_id=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        ligacao_id,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_terminar_projeto. user_id=%s", request.user.id)
        return resposta_erro

    empregado = get_object_or_404(Empregados, pk=pk, empresa=empresa)
    ligacao = get_object_or_404(
        EmpregadoProjeto,
        id=ligacao_id,
        empregado=empregado,
        empresa=empresa,
    )

    if request.method == "POST":
        terminar_ligacao_projeto_empregado(ligacao, empresa=empresa)
        logger.info(
            "Projeto encerrado para empregado com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s, ligacao_id=%s",
            request.user.id,
            empresa.id,
            empregado.id,
            ligacao.id,
        )
        messages.success(request, "Projeto encerrado para este empregado com sucesso.")
        return redirect(reverse("projetos:empregado_detail", args=[empregado.id]))

    return render(request, "projetos/empregado_projeto_confirm_terminar.html", {
        "empregado": empregado,
        "ligacao": ligacao,
    })


@login_required
@admin_required
def empregado_adicionar_ficheiro(request, pk):
    logger.info(
        "Entrada na view empregado_adicionar_ficheiro. user_id=%s, username='%s', empregado_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_adicionar_ficheiro. user_id=%s", request.user.id)
        return resposta_erro

    empregado = get_object_or_404(Empregados, pk=pk, empresa=empresa)

    if request.method == "POST":
        form = EmpregadoFicheiroForm(request.POST, request.FILES)
        if form.is_valid():
            ficheiro = form.save(commit=False)
            ficheiro.empregado = empregado
            ficheiro.empresa = empresa
            ficheiro.save()
            logger.info(
                "Ficheiro adicionado ao empregado com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s, ficheiro_id=%s",
                request.user.id,
                empresa.id,
                empregado.id,
                ficheiro.id,
            )
            messages.success(request, "Ficheiro adicionado com sucesso.")
            return redirect(reverse("projetos:empregado_detail", args=[empregado.id]))
        else:
            logger.warning(
                "Erro ao adicionar ficheiro ao empregado. user_id=%s, empregado_pk=%s, erros=%s",
                request.user.id,
                pk,
                form.errors,
            )
            messages.error(request, "Erro ao adicionar ficheiro. Verifique os dados.")
    else:
        form = EmpregadoFicheiroForm()

    return render(request, "projetos/empregado_ficheiro_form.html", {
        "form": form,
        "empregado": empregado,
        "titulo": "Adicionar Ficheiro ao Empregado",
    })


@login_required
@admin_required
def empregado_apagar_ficheiro(request, pk, ficheiro_id):
    logger.info(
        "Entrada na view empregado_apagar_ficheiro. user_id=%s, username='%s', empregado_pk=%s, ficheiro_id=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        ficheiro_id,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_apagar_ficheiro. user_id=%s", request.user.id)
        return resposta_erro

    empregado = get_object_or_404(Empregados, pk=pk, empresa=empresa)
    ficheiro = get_object_or_404(
        EmpregadoFicheiro,
        id=ficheiro_id,
        empregado=empregado,
        empresa=empresa,
    )

    if request.method == "POST":
        ficheiro_id_removido = ficheiro.id
        if ficheiro.ficheiro:
            ficheiro.ficheiro.delete(save=False)
        ficheiro.delete()
        logger.info(
            "Ficheiro removido do empregado com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s, ficheiro_id=%s",
            request.user.id,
            empresa.id,
            empregado.id,
            ficheiro_id_removido,
        )
        messages.success(request, "Ficheiro removido com sucesso.")
        return redirect(reverse("projetos:empregado_detail", args=[empregado.id]))

    return render(request, "projetos/empregado_ficheiro_confirm_delete.html", {
        "empregado": empregado,
        "ficheiro": ficheiro,
    })


@login_required
@admin_required
def empregado_pendentes(request):
    logger.info(
        "Entrada na view empregado_pendentes. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_pendentes. user_id=%s", request.user.id)
        return resposta_erro

    empregados = obter_empregados_pendentes(empresa=empresa)
    logger.info(
        "View empregado_pendentes carregada com sucesso. user_id=%s, empresa_id=%s, total_pendentes=%s",
        request.user.id,
        empresa.id,
        empregados.count() if hasattr(empregados, "count") else "n/a",
    )
    return render(request, "projetos/empregado_pendentes.html", {
        "empregados": empregados,
        "titulo": "Empregados Pendentes de Aprovação",
    })


@login_required
@admin_required
def empregado_aprovar(request, pk):
    logger.info(
        "Entrada na view empregado_aprovar. user_id=%s, username='%s', empregado_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view empregado_aprovar. user_id=%s", request.user.id)
        return resposta_erro

    empregado = get_object_or_404(Empregados, pk=pk, empresa=empresa)

    if request.method == "POST":
        aprovar_empregado(empregado, empresa=empresa)
        logger.info(
            "Empregado aprovado com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s",
            request.user.id,
            empresa.id,
            empregado.id,
        )
        messages.success(request, "Empregado aprovado com sucesso.")
        return redirect(reverse("projetos:empregado_pendentes"))

    return render(request, "projetos/empregado_aprovar_confirm.html", {
        "empregado": empregado,
    })

@login_required
@empregado_required
def meus_furos_empregado(request):
    logger.info(
        "Entrada na view meus_furos_empregado. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empregado, resposta_erro = _obter_empregado_autenticado(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view meus_furos_empregado. user_id=%s", request.user.id)
        return resposta_erro

    furo_ids_associados = EmpregadoFuro.objects.filter(
        empregado=empregado,
        empresa=empregado.empresa,
    ).values_list("furo_id", flat=True)

    furo_ids_registos = empregado.registos_diarios.filter(
        furo__isnull=False,
        empresa=empregado.empresa,
    ).values_list("furo_id", flat=True)

    furos = Furo.objects.select_related("projeto").filter(
        empresa=empregado.empresa,
        id__in=list(furo_ids_associados) + list(furo_ids_registos)
    ).distinct().order_by("nome")

    logger.info(
        "View meus_furos_empregado carregada com sucesso. user_id=%s, empregado_id=%s, empresa_id=%s, total_furos=%s",
        request.user.id,
        empregado.id,
        empregado.empresa_id,
        furos.count(),
    )
    return render(request, "projetos/meus_furos_empregado.html", {
        "empregado": empregado,
        "furos": furos,
        "titulo": "Meus Furos",
    })

@login_required
@empregado_required
def furo_detail_empregado(request, pk):
    logger.info(
        "Entrada na view furo_detail_empregado. user_id=%s, username='%s', furo_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empregado, resposta_erro = _obter_empregado_autenticado(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_detail_empregado. user_id=%s", request.user.id)
        return resposta_erro

    furo = get_object_or_404(
        Furo.objects.select_related("projeto"),
        pk=pk,
        empresa=empregado.empresa,
    )

    associado = EmpregadoFuro.objects.filter(
        empregado=empregado,
        furo=furo,
        empresa=empregado.empresa,
    ).exists()

    com_registos = RegistoDiarioEmpregado.objects.filter(
        empregado=empregado,
        furo=furo,
        empresa=empregado.empresa,
    ).exists()

    if not associado and not com_registos:
        logger.warning(
            "Empregado sem permissão para furo_detail_empregado. user_id=%s, empregado_id=%s, furo_id=%s",
            request.user.id,
            empregado.id,
            furo.id,
        )
        messages.error(request, "Não tens permissão para ver os detalhes deste furo.")
        return redirect("projetos:meus_furos_empregado")

    medicoes = Medicao.objects.filter(
        furo=furo,
        empresa=empregado.empresa,
    ).order_by("criado_em", "profundidade_medida")
    registos = RegistoDiarioEmpregado.objects.filter(
        empregado=empregado,
        furo=furo,
        empresa=empregado.empresa,
    ).select_related("projeto", "furo").order_by("-data", "-criado_em")

    logger.info(
        "View furo_detail_empregado carregada com sucesso. user_id=%s, empregado_id=%s, furo_id=%s",
        request.user.id,
        empregado.id,
        furo.id,
    )
    return render(request, "projetos/furo_detail_empregado.html", {
        "empregado": empregado,
        "furo": furo,
        "medicoes": medicoes,
        "registos": registos,
    })

@login_required
@empregado_required
def furo_3d_empregado(request, pk):
    logger.info(
        "Entrada na view furo_3d_empregado. user_id=%s, username='%s', furo_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empregado, resposta_erro = _obter_empregado_autenticado(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view furo_3d_empregado. user_id=%s", request.user.id)
        return resposta_erro

    furo = get_object_or_404(
        Furo.objects.select_related("projeto"),
        pk=pk,
        empresa=empregado.empresa,
    )

    associado = EmpregadoFuro.objects.filter(
        empregado=empregado,
        furo=furo,
        empresa=empregado.empresa,
    ).exists()

    com_registos = RegistoDiarioEmpregado.objects.filter(
        empregado=empregado,
        furo=furo,
        empresa=empregado.empresa,
    ).exists()

    if not associado and not com_registos:
        logger.warning(
            "Empregado sem permissão para furo_3d_empregado. user_id=%s, empregado_id=%s, furo_id=%s",
            request.user.id,
            empregado.id,
            furo.id,
        )
        messages.error(request, "Não tens permissão para ver o 3D deste furo.")
        return redirect("projetos:meus_furos_empregado")

    medicoes = list(
        Medicao.objects.filter(furo=furo, empresa=empregado.empresa)
        .order_by("criado_em", "profundidade_medida")
        .values(
            "profundidade_medida",
            "inclinacao_real_medida",
            "azimute_real_medido",
        )
    )

    logger.info(
        "View furo_3d_empregado carregada com sucesso. user_id=%s, empregado_id=%s, furo_id=%s, total_medicoes=%s",
        request.user.id,
        empregado.id,
        furo.id,
        len(medicoes),
    )
    return render(request, "projetos/furo_3d_empregado.html", {
        "empregado": empregado,
        "furo": furo,
        "medicoes": medicoes,
    })

# -------  MEUS PROJETOS ------------- #
@login_required
@empregado_required
def meus_projetos_empregado(request):
    logger.info(
        "Entrada na view meus_projetos_empregado. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empregado, resposta_erro = _obter_empregado_autenticado(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view meus_projetos_empregado. user_id=%s", request.user.id)
        return resposta_erro

    projetos_associados_ids = empregado.ligacoes_projetos.filter(
        empresa=empregado.empresa,
    ).values_list("projeto_id", flat=True)

    projetos_registos_ids = empregado.registos_diarios.filter(
        projeto__isnull=False,
        empresa=empregado.empresa,
    ).values_list("projeto_id", flat=True)

    projetos = Projeto.objects.filter(
        empresa=empregado.empresa,
        id__in=list(projetos_associados_ids) + list(projetos_registos_ids)
    ).distinct().annotate(
        total_furos_projeto=Count("furos", distinct=True)
    ).order_by("nome")

    resumo_registos = (
        empregado.registos_diarios
        .filter(projeto__in=projetos, empresa=empregado.empresa)
        .values("projeto_id")
        .annotate(
            total_metros=Sum("metros_furados"),
            total_horas=Sum("horas_trabalhadas"),
        )
    )

    resumo_por_projeto = {
        item["projeto_id"]: item
        for item in resumo_registos
    }

    logger.info(
        "View meus_projetos_empregado carregada com sucesso. user_id=%s, empregado_id=%s, empresa_id=%s, total_projetos=%s",
        request.user.id,
        empregado.id,
        empregado.empresa_id,
        projetos.count(),
    )
    return render(request, "projetos/meus_projetos_empregado.html", {
        "empregado": empregado,
        "projetos": projetos,
        "resumo_por_projeto": resumo_por_projeto,
        "titulo": "Meus Projetos",
    })

@login_required
@empregado_required
def projeto_detail_empregado(request, pk):
    logger.info(
        "Entrada na view projeto_detail_empregado. user_id=%s, username='%s', projeto_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empregado, resposta_erro = _obter_empregado_autenticado(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view projeto_detail_empregado. user_id=%s", request.user.id)
        return resposta_erro

    projeto = get_object_or_404(Projeto, pk=pk, empresa=empregado.empresa)

    associado_ao_projeto = empregado.ligacoes_projetos.filter(
        projeto=projeto,
        empresa=empregado.empresa,
    ).exists()
    com_registos_no_projeto = empregado.registos_diarios.filter(
        projeto=projeto,
        empresa=empregado.empresa,
    ).exists()

    if not associado_ao_projeto and not com_registos_no_projeto:
        logger.warning(
            "Empregado sem permissão para projeto_detail_empregado. user_id=%s, empregado_id=%s, projeto_id=%s",
            request.user.id,
            empregado.id,
            projeto.id,
        )
        messages.error(request, "Não tens permissão para ver este projeto.")
        return redirect("projetos:meus_projetos_empregado")

    furo_ids_associados = EmpregadoFuro.objects.filter(
        empregado=empregado,
        empresa=empregado.empresa,
        furo__projeto=projeto
    ).values_list("furo_id", flat=True)

    furo_ids_registos = empregado.registos_diarios.filter(
        projeto=projeto,
        furo__isnull=False,
        empresa=empregado.empresa,
    ).values_list("furo_id", flat=True)

    furos = Furo.objects.filter(
        empresa=empregado.empresa,
        projeto=projeto,
        id__in=list(furo_ids_associados) + list(furo_ids_registos)
    ).distinct().order_by("nome")

    registos = empregado.registos_diarios.filter(projeto=projeto, empresa=empregado.empresa)

    total_metros = sum(r.metros_furados or 0 for r in registos)
    total_horas = sum(r.horas_trabalhadas or 0 for r in registos)
    total_registos = registos.count()
    media_metros_hora = round(total_metros / total_horas, 2) if total_horas else 0

    logger.info(
        "View projeto_detail_empregado carregada com sucesso. user_id=%s, empregado_id=%s, projeto_id=%s",
        request.user.id,
        empregado.id,
        projeto.id,
    )
    return render(request, "projetos/projeto_detail_empregado.html", {
        "empregado": empregado,
        "projeto": projeto,
        "furos": furos,
        "total_metros": round(total_metros, 2),
        "total_horas": round(total_horas, 2),
        "total_registos": total_registos,
        "media_metros_hora": media_metros_hora,
    })

@login_required
@empregado_required
def area_empregado(request):
    logger.info(
        "Entrada na view area_empregado. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empregado, resposta_erro = _obter_empregado_autenticado(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view area_empregado. user_id=%s", request.user.id)
        return resposta_erro

    furo_ids_associados = EmpregadoFuro.objects.filter(
        empregado=empregado,
        empresa=empregado.empresa,
    ).values_list("furo_id", flat=True)

    furo_ids_registos = empregado.registos_diarios.filter(
        furo__isnull=False,
        empresa=empregado.empresa,
    ).values_list("furo_id", flat=True)

    furos_trabalhados = Furo.objects.filter(
        empresa=empregado.empresa,
        id__in=list(furo_ids_associados) + list(furo_ids_registos)
    ).distinct().order_by("nome")

    ultimos_registos = empregado.registos_diarios.select_related(
        "projeto", "furo"
    ).filter(empresa=empregado.empresa)[:5]

    configuracoes_perfuracao = empregado.configuracoes_perfuracao.select_related(
        "furo", "atualizado_por"
    ).filter(empresa=empregado.empresa).order_by("furo__nome")

    horas_hoje = empregado.horas_diarias or 0
    horas_mes = empregado.horas_trabalhadas_mes or 0
    horas_total = empregado.horas_total or 0

    metros_hoje = empregado.metros_furados_hoje or 0
    metros_total = empregado.total_metros_furados or 0

    total_furos = empregado.total_furos_trabalhados or 0
    media_metros_hora = empregado.media_metros_por_hora or 0
    media_metros_dia = empregado.media_metros_por_dia or 0

    registos_grafico = empregado.registos_diarios.filter(empresa=empregado.empresa).order_by("data")

    labels = []
    metros_por_dia = []
    horas_por_dia = []
    produtividade_por_dia = []

    agregados = {}

    for registo in registos_grafico:
        if not registo.data:
            continue

        chave = registo.data.strftime("%d/%m/%Y")

        if chave not in agregados:
            agregados[chave] = {
                "metros": 0,
                "horas": 0,
            }

        agregados[chave]["metros"] += registo.metros_furados or 0
        agregados[chave]["horas"] += registo.horas_trabalhadas or 0

    for data_label, valores in agregados.items():
        labels.append(data_label)
        metros = valores["metros"]
        horas = valores["horas"]
        produtividade = (metros / horas) if horas > 0 else 0

        metros_por_dia.append(round(metros, 2))
        horas_por_dia.append(round(horas, 2))
        produtividade_por_dia.append(round(produtividade, 2))

    logger.info(
        "View area_empregado carregada com sucesso. user_id=%s, empregado_id=%s, empresa_id=%s",
        request.user.id,
        empregado.id,
        empregado.empresa_id,
    )
    return render(request, "projetos/area_empregado.html", {
        "empregado": empregado,
        "horas_hoje": horas_hoje,
        "horas_mes": horas_mes,
        "horas_total": horas_total,
        "metros_hoje": metros_hoje,
        "metros_total": metros_total,
        "total_furos": total_furos,
        "media_metros_hora": media_metros_hora,
        "media_metros_dia": media_metros_dia,
        "ultimos_registos": ultimos_registos,
        "grafico_labels": labels,
        "grafico_metros": metros_por_dia,
        "grafico_horas": horas_por_dia,
        "grafico_produtividade": produtividade_por_dia,
        "furos_trabalhados": furos_trabalhados,
        "configuracoes_perfuracao": configuracoes_perfuracao,
    })

# --------- REDIRECT ------------

def redirect_after_login(request):
    logger.info(
        "Entrada na view redirect_after_login. authenticated=%s, user_id=%s",
        request.user.is_authenticated,
        getattr(request.user, "id", None),
    )

    if not request.user.is_authenticated:
        logger.warning("redirect_after_login chamado sem utilizador autenticado.")
        return redirect("login")

    if request.user.is_superuser:
        logger.info(
            "Acesso total via superuser em redirect_after_login. user_id=%s",
            request.user.id,
        )
        return redirect("plataforma:dashboard")

    perfil = PerfilPlataforma.objects.filter(
        user=request.user,
        ativo=True,
    ).first()

    if perfil:
        logger.info(
            "PerfilPlataforma encontrado em redirect_after_login. user_id=%s, tipo_acesso=%s, empresa_id=%s",
            request.user.id,
            perfil.tipo_acesso,
            perfil.empresa_id,
        )

        if perfil.tipo_acesso in ["platform_owner", "platform_admin"]:
            return redirect("plataforma:dashboard")

        if perfil.tipo_acesso in ["empresa_admin", "empresa_gestor"]:
            return redirect(reverse("projetos:dashboard"))

        if perfil.tipo_acesso in ["empregado", "individual"]:
            return redirect(reverse("projetos:area_empregado"))

    empregado = _resolver_empregado_por_user_ou_email(request.user)
    if empregado:
        logger.info(
            "Empregado encontrado em redirect_after_login. user_id=%s, empregado_id=%s, aprovado=%s, empresa_id=%s",
            request.user.id,
            empregado.id,
            empregado.aprovado,
            empregado.empresa_id,
        )

        if not empregado.aprovado:
            logger.warning(
                "Empregado encontrado mas não aprovado em redirect_after_login. user_id=%s, empregado_id=%s",
                request.user.id,
                empregado.id,
            )

        if not empregado.empresa_id:
            logger.warning(
                "Empregado encontrado mas sem empresa em redirect_after_login. user_id=%s, empregado_id=%s",
                request.user.id,
                empregado.id,
            )
    else:
        logger.warning(
            "Nenhum Empregados ligado ao utilizador em redirect_after_login. user_id=%s, email='%s'",
            request.user.id,
            getattr(request.user, "email", ""),
        )

    if empregado and empregado.aprovado and empregado.empresa_id:
        logger.info(
            "Fallback via Empregados em redirect_after_login. user_id=%s, empregado_id=%s, empresa_id=%s",
            request.user.id,
            empregado.id,
            empregado.empresa_id,
        )
        return redirect(reverse("projetos:area_empregado"))

    logger.warning(
        "Conta sem contexto válido em redirect_after_login. user_id=%s",
        request.user.id,
    )
    messages.error(
        request,
        "A tua conta não está configurada corretamente. Contacta o administrador.",
    )
    return redirect("website:home")


def redirect_view(request):
    return redirect_after_login(request)



# -------- CONFIGURAÇÃO PERFURAÇÃO ------------------

@login_required
@empregado_required
def configuracao_perfuracao_list_empregado(request):
    logger.info(
        "Entrada na view configuracao_perfuracao_list_empregado. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empregado, resposta_erro = _obter_empregado_autenticado(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view configuracao_perfuracao_list_empregado. user_id=%s", request.user.id)
        return resposta_erro

    configuracoes = obter_lista_configuracoes_perfuracao_empregado(
        empregado,
        empresa=empregado.empresa,
    )

    logger.info(
        "View configuracao_perfuracao_list_empregado carregada com sucesso. user_id=%s, empregado_id=%s, empresa_id=%s, total_configuracoes=%s",
        request.user.id,
        empregado.id,
        empregado.empresa_id,
        configuracoes.count() if hasattr(configuracoes, "count") else "n/a",
    )
    return render(request, "projetos/configuracao_perfuracao_list.html", {
        "empregado": empregado,
        "configuracoes": configuracoes,
        "modo_admin": False,
    })


@login_required
@empregado_required
def configuracao_perfuracao_create_empregado(request):
    logger.info(
        "Entrada na view configuracao_perfuracao_create_empregado. user_id=%s, username='%s', method=%s",
        request.user.id,
        request.user.username,
        request.method,
    )
    empregado, resposta_erro = _obter_empregado_autenticado(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view configuracao_perfuracao_create_empregado. user_id=%s", request.user.id)
        return resposta_erro

    if request.method == "POST":
        form = ConfiguracaoPerfuracaoEmpregadoForm(request.POST, empregado=empregado)
        if form.is_valid():
            configuracao = form.save(commit=False)
            configuracao.empregado = empregado
            configuracao.atualizado_por = request.user
            configuracao.empresa = empregado.empresa
            configuracao.save()

            logger.info(
                "Configuração de perfuração criada com sucesso por empregado. user_id=%s, empregado_id=%s, empresa_id=%s, configuracao_id=%s",
                request.user.id,
                empregado.id,
                empregado.empresa_id,
                configuracao.id,
            )
            messages.success(request, "Configuração de perfuração criada com sucesso.")
            return redirect("projetos:configuracao_perfuracao_list_empregado")

        logger.warning(
            "Erro ao criar configuração de perfuração por empregado. user_id=%s, empregado_id=%s, erros=%s",
            request.user.id,
            empregado.id,
            form.errors,
        )
        messages.error(request, "Erro ao criar a configuração de perfuração.")
    else:
        form = ConfiguracaoPerfuracaoEmpregadoForm(empregado=empregado)

    return render(request, "projetos/configuracao_perfuracao_form.html", {
        "form": form,
        "empregado": empregado,
        "titulo": "Nova Configuração de Perfuração",
        "modo_admin": False,
    })


@login_required
@empregado_required
def configuracao_perfuracao_update_empregado(request, pk):
    logger.info(
        "Entrada na view configuracao_perfuracao_update_empregado. user_id=%s, username='%s', configuracao_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empregado, resposta_erro = _obter_empregado_autenticado(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view configuracao_perfuracao_update_empregado. user_id=%s", request.user.id)
        return resposta_erro

    configuracao = get_object_or_404(
        ConfiguracaoPerfuracaoEmpregado,
        pk=pk,
        empregado=empregado,
        empresa=empregado.empresa,
    )

    if request.method == "POST":
        form = ConfiguracaoPerfuracaoEmpregadoForm(
            request.POST,
            instance=configuracao,
            empregado=empregado,
        )
        if form.is_valid():
            configuracao = form.save(commit=False)
            configuracao.empregado = empregado
            configuracao.atualizado_por = request.user
            configuracao.empresa = empregado.empresa
            configuracao.save()

            logger.info(
                "Configuração de perfuração atualizada com sucesso por empregado. user_id=%s, empregado_id=%s, empresa_id=%s, configuracao_id=%s",
                request.user.id,
                empregado.id,
                empregado.empresa_id,
                configuracao.id,
            )
            messages.success(request, "Configuração de perfuração atualizada com sucesso.")
            return redirect("projetos:configuracao_perfuracao_list_empregado")

        logger.warning(
            "Erro ao atualizar configuração de perfuração por empregado. user_id=%s, configuracao_pk=%s, erros=%s",
            request.user.id,
            pk,
            form.errors,
        )
        messages.error(request, "Erro ao atualizar a configuração de perfuração.")
    else:
        form = ConfiguracaoPerfuracaoEmpregadoForm(
            instance=configuracao,
            empregado=empregado,
        )

    return render(request, "projetos/configuracao_perfuracao_form.html", {
        "form": form,
        "empregado": empregado,
        "titulo": f"Editar Configuração - {configuracao.furo.nome}",
        "modo_admin": False,
    })


@login_required
@admin_required
def configuracao_perfuracao_list_admin(request, pk):
    logger.info(
        "Entrada na view configuracao_perfuracao_list_admin. user_id=%s, username='%s', empregado_pk=%s",
        request.user.id,
        request.user.username,
        pk,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view configuracao_perfuracao_list_admin. user_id=%s", request.user.id)
        return resposta_erro

    empregado = get_object_or_404(Empregados, pk=pk, empresa=empresa)
    configuracoes = obter_lista_configuracoes_perfuracao_empregado(
        empregado,
        empresa=empresa,
    )

    logger.info(
        "View configuracao_perfuracao_list_admin carregada com sucesso. user_id=%s, empresa_id=%s, empregado_id=%s",
        request.user.id,
        empresa.id,
        empregado.id,
    )
    return render(request, "projetos/configuracao_perfuracao_list.html", {
        "empregado": empregado,
        "configuracoes": configuracoes,
        "modo_admin": True,
    })


@login_required
@admin_required
def configuracao_perfuracao_create_admin(request, pk):
    logger.info(
        "Entrada na view configuracao_perfuracao_create_admin. user_id=%s, username='%s', empregado_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view configuracao_perfuracao_create_admin. user_id=%s", request.user.id)
        return resposta_erro

    empregado = get_object_or_404(Empregados, pk=pk, empresa=empresa)

    if request.method == "POST":
        form = ConfiguracaoPerfuracaoEmpregadoForm(request.POST, empregado=empregado)
        if form.is_valid():
            configuracao = form.save(commit=False)
            configuracao.empregado = empregado
            configuracao.atualizado_por = request.user
            configuracao.empresa = empresa
            configuracao.save()

            logger.info(
                "Configuração de perfuração criada com sucesso por admin. user_id=%s, empresa_id=%s, configuracao_id=%s, empregado_id=%s",
                request.user.id,
                empresa.id,
                configuracao.id,
                empregado.id,
            )
            messages.success(request, "Configuração de perfuração criada com sucesso.")
            return redirect("projetos:configuracao_perfuracao_list_admin", pk=empregado.pk)

        logger.warning("Erro ao criar configuração de perfuração por admin. user_id=%s, erros=%s", request.user.id, form.errors)
        messages.error(request, "Erro ao criar a configuração de perfuração.")
    else:
        form = ConfiguracaoPerfuracaoEmpregadoForm(empregado=empregado)

    return render(request, "projetos/configuracao_perfuracao_form.html", {
        "form": form,
        "empregado": empregado,
        "titulo": f"Nova Configuração - {empregado.nome}",
        "modo_admin": True,
    })


@login_required
@admin_required
def configuracao_perfuracao_update_admin(request, pk):
    logger.info(
        "Entrada na view configuracao_perfuracao_update_admin. user_id=%s, username='%s', configuracao_pk=%s, method=%s",
        request.user.id,
        request.user.username,
        pk,
        request.method,
    )
    empresa, resposta_erro = _obter_empresa_admin_empregados(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view configuracao_perfuracao_update_admin. user_id=%s", request.user.id)
        return resposta_erro

    configuracao = get_object_or_404(ConfiguracaoPerfuracaoEmpregado, pk=pk, empresa=empresa)
    empregado = configuracao.empregado

    if request.method == "POST":
        form = ConfiguracaoPerfuracaoEmpregadoForm(
            request.POST,
            instance=configuracao,
            empregado=empregado
        )
        if form.is_valid():
            configuracao = form.save(commit=False)
            configuracao.empregado = empregado
            configuracao.atualizado_por = request.user
            configuracao.empresa = empresa
            configuracao.save()

            logger.info(
                "Configuração de perfuração atualizada com sucesso por admin. user_id=%s, empresa_id=%s, configuracao_id=%s, empregado_id=%s",
                request.user.id,
                empresa.id,
                configuracao.id,
                empregado.id,
            )
            messages.success(request, "Configuração de perfuração atualizada com sucesso.")
            return redirect("projetos:configuracao_perfuracao_list_admin", pk=empregado.pk)

        logger.warning("Erro ao atualizar configuração de perfuração por admin. user_id=%s, configuracao_pk=%s, erros=%s", request.user.id, pk, form.errors)
        messages.error(request, "Erro ao atualizar a configuração de perfuração.")
    else:
        form = ConfiguracaoPerfuracaoEmpregadoForm(
            instance=configuracao,
            empregado=empregado
        )

    return render(request, "projetos/configuracao_perfuracao_form.html", {
        "form": form,
        "empregado": empregado,
        "titulo": f"Editar Configuração - {configuracao.furo.nome}",
        "modo_admin": True,
    })


# ------ MATERIAIS EMPREGADO ------- # 
@login_required
@empregado_required
def materiais_disponiveis_empregado(request):
    logger.info(
        "Entrada na view materiais_disponiveis_empregado. user_id=%s, username='%s'",
        request.user.id,
        request.user.username,
    )
    empregado, resposta_erro = _obter_empregado_autenticado(request)
    if resposta_erro:
        logger.warning("Acesso bloqueado na view materiais_disponiveis_empregado. user_id=%s", request.user.id)
        return resposta_erro

    projetos_ids = list(
        empregado.ligacoes_projetos.filter(empresa=empregado.empresa).values_list("projeto_id", flat=True)
    )

    furos_ids_associados = list(
        EmpregadoFuro.objects.filter(
            empregado=empregado,
            empresa=empregado.empresa,
        ).values_list("furo_id", flat=True)
    )

    furos_ids_registos = list(
        empregado.registos_diarios.filter(
            furo__isnull=False,
            empresa=empregado.empresa,
        ).values_list("furo_id", flat=True)
    )

    furos_ids = list(set(furos_ids_associados + furos_ids_registos))

    projeto_id = request.GET.get("projeto")
    furo_id = request.GET.get("furo")
    nome = (request.GET.get("nome") or "").strip()

    materiais = Material.objects.filter(ativo=True)

    if empregado.empresa_id:
        materiais = materiais.filter(empresa=empregado.empresa)

    materiais = materiais.filter(
        Q(projeto_id__in=projetos_ids) | Q(furo_id__in=furos_ids)
    ).distinct()

    if projeto_id:
        materiais = materiais.filter(projeto_id=projeto_id)

    if furo_id:
        materiais = materiais.filter(furo_id=furo_id)

    if nome:
        materiais = materiais.filter(nome__icontains=nome)

    materiais = materiais.select_related("projeto", "furo").order_by("nome")

    projetos = Projeto.objects.filter(
        empresa=empregado.empresa,
        id__in=projetos_ids
    ).distinct().order_by("nome")

    furos = Furo.objects.filter(
        empresa=empregado.empresa,
        id__in=furos_ids
    ).distinct().order_by("nome")

    logger.info(
        "View materiais_disponiveis_empregado carregada com sucesso. user_id=%s, empregado_id=%s, empresa_id=%s, total_materiais=%s, filtro_nome='%s'",
        request.user.id,
        empregado.id,
        empregado.empresa_id,
        materiais.count(),
        nome,
    )
    return render(request, "projetos/materiais_disponiveis_empregado.html", {
        "empregado": empregado,
        "materiais": materiais,
        "projetos": projetos,
        "furos": furos,
        "filtros": {
            "projeto": projeto_id or "",
            "furo": furo_id or "",
            "nome": nome,
        },
        "titulo": "Materiais Disponíveis",
    })