import secrets
import string
import unicodedata

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..decorators import admin_required, empregado_required
from ..forms.empregado import (
    EmpregadoCreateForm,
    EmpregadoFicheiroForm,
    EmpregadoProjetoForm,
    EmpregadoRegistroForm,
    EmpregadoUpdateForm,
)
from ..models.empregado import Empregados, EmpregadoFicheiro, EmpregadoProjeto
from ..models.furo import Furo
from projetos.forms.configuracao_perfuracao import ConfiguracaoPerfuracaoEmpregadoForm
from projetos.models import ConfiguracaoPerfuracaoEmpregado
from projetos.selectors.configuracao_perfuracao import (
    obter_configuracao_perfuracao,
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


# views/empregado.py

def _normalizar_username_base(valor):
    valor = valor or "empregado"
    valor = unicodedata.normalize("NFKD", valor).encode("ascii", "ignore").decode("ascii")
    valor = valor.lower().strip().replace(" ", ".")
    permitido = string.ascii_lowercase + string.digits + ".-_"
    valor = "".join(ch for ch in valor if ch in permitido)
    return valor or "empregado"


def _gerar_username_unico(nome):
    base = _normalizar_username_base(nome)
    candidato = base
    contador = 1

    while User.objects.filter(username=candidato).exists():
        candidato = f"{base}{contador}"
        contador += 1

    return candidato


def _gerar_password_temporaria(tamanho=10):
    alfabeto = string.ascii_letters + string.digits
    return "".join(secrets.choice(alfabeto) for _ in range(tamanho))


def _criar_user_para_empregado(empregado):
    if empregado.user:
        return empregado.user, None, False

    username = _gerar_username_unico(empregado.nome)
    password = _gerar_password_temporaria()

    user = User.objects.create_user(
        username=username,
        email=empregado.email or "",
        password=password,
        first_name=(empregado.nome or "").split(" ")[0] if empregado.nome else "",
        is_active=True,
    )

    empregado.user = user
    if not empregado.aprovado:
        empregado.aprovado = True
    if not empregado.data_aprovacao:
        empregado.data_aprovacao = timezone.now()
    empregado.save(update_fields=["user", "aprovado", "data_aprovacao"])

    return user, password, True


# ---------------- EMPREGADOS ----------------
def registo_empregado(request):
    if request.method == "POST":
        form = EmpregadoRegistroForm(request.POST)
        if form.is_valid():
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
            print("ERROS REGISTO:", form.errors)
    else:
        form = EmpregadoRegistroForm()

    return render(request, "projetos/registo_empregado.html", {
        "form": form,
        "titulo": "Registo de Empregado",
    })


@login_required
@admin_required
def empregado_list(request):
    empregados = obter_lista_empregados()
    return render(request, "projetos/empregado_list.html", {
        "empregados": empregados,
    })


@login_required
@admin_required
def empregado_create(request):
    form = EmpregadoCreateForm(request.POST or None, request.FILES or None)

    if form.is_valid():
        empregado = form.save(commit=False)
        empregado.aprovado = True
        if not empregado.data_aprovacao:
            empregado.data_aprovacao = timezone.now()
        empregado.save()
        form.save_m2m()

        user, password_temporaria, criado_agora = _criar_user_para_empregado(empregado)

        if criado_agora:
            messages.success(
                request,
                (
                    f"Empregado criado com sucesso. "
                    f"Utilizador: {user.username} | Palavra-passe temporária: {password_temporaria}"
                ),
            )
        else:
            messages.success(
                request,
                f"Empregado criado com sucesso. Utilizador associado: {user.username}",
            )

        return redirect("projetos:empregado_detail", pk=empregado.id)

    return render(request, "projetos/empregado_form.html", {
        "form": form,
        "titulo": "Novo Empregado",
    })


@login_required
@admin_required
def empregado_detail(request, pk):
    empregado = get_object_or_404(Empregados, pk=pk)
    return render(request, "projetos/empregado_detail.html", {
        "empregado": empregado,
        "username_gerado": empregado.user.username if empregado.user else None,
    })


@login_required
@admin_required
def empregado_update(request, pk):
    empregado = get_object_or_404(Empregados, pk=pk)

    if request.method == "POST":
        form = EmpregadoUpdateForm(request.POST, request.FILES, instance=empregado)
        if form.is_valid():
            form.save()
            messages.success(request, "Empregado atualizado com sucesso.")
            return redirect("projetos:empregado_detail", pk=empregado.id)
        else:
            messages.error(request, "Erro ao atualizar empregado. Verifique os dados.")
            print("ERROS DO FORM:", form.errors)
    else:
        form = EmpregadoUpdateForm(instance=empregado)

    return render(request, "projetos/empregado_form.html", {
        "form": form,
        "titulo": "Editar Empregado",
        "empregado": empregado,
    })


@login_required
@admin_required
def empregado_delete(request, pk):
    empregado = get_object_or_404(Empregados, pk=pk)

    if request.method == "POST":
        empregado.delete()
        messages.success(request, "Empregado apagado com sucesso.")
        return redirect("projetos:empregado_list")

    return render(request, "projetos/empregado_confirm_delete.html", {
        "empregado": empregado,
    })


@login_required
@admin_required
def empregado_adicionar_projeto(request, pk):
    empregado = get_object_or_404(Empregados, pk=pk)

    if request.method == "POST":
        form = EmpregadoProjetoForm(request.POST)
        if form.is_valid():
            ligacao = form.save(commit=False)
            ligacao.empregado = empregado

            existe_ativa = EmpregadoProjeto.objects.filter(
                empregado=empregado,
                projeto=ligacao.projeto,
                ativo=True,
            ).exists()

            if ligacao.ativo and existe_ativa:
                form.add_error("projeto", "Este empregado já está associado de forma ativa a este projeto.")
            else:
                ligacao.save()
                messages.success(request, "Projeto associado ao empregado com sucesso.")
                return redirect("projetos:empregado_detail", pk=empregado.id)
        else:
            messages.error(request, "Erro ao associar projeto. Verifique os dados.")
    else:
        form = EmpregadoProjetoForm()

    return render(request, "projetos/empregado_projeto_form.html", {
        "form": form,
        "empregado": empregado,
        "titulo": "Associar Projeto ao Empregado",
    })


@login_required
@admin_required
def empregado_editar_projeto(request, pk, ligacao_id):
    empregado = get_object_or_404(Empregados, pk=pk)
    ligacao = get_object_or_404(EmpregadoProjeto, id=ligacao_id, empregado=empregado)

    if request.method == "POST":
        form = EmpregadoProjetoForm(request.POST, instance=ligacao)
        if form.is_valid():
            nova_ligacao = form.save(commit=False)
            nova_ligacao.empregado = empregado

            existe_ativa = empregado_ja_tem_projeto_ativo(
                empregado=empregado,
                projeto=nova_ligacao.projeto,
                excluir_ligacao_id=ligacao.id,
            )

            if nova_ligacao.ativo and existe_ativa:
                form.add_error("projeto", "Este empregado já está associado de forma ativa a este projeto.")
            else:
                nova_ligacao.save()
                messages.success(request, "Ligação projeto/empregado atualizada com sucesso.")
                return redirect("projetos:empregado_detail", pk=empregado.id)
        else:
            messages.error(request, "Erro ao atualizar ligação. Verifique os dados.")
    else:
        form = EmpregadoProjetoForm(instance=ligacao)

    return render(request, "projetos/empregado_projeto_form.html", {
        "form": form,
        "empregado": empregado,
        "titulo": "Editar Ligação de Projeto",
    })


@login_required
@admin_required
def empregado_terminar_projeto(request, pk, ligacao_id):
    empregado = get_object_or_404(Empregados, pk=pk)
    ligacao = get_object_or_404(EmpregadoProjeto, id=ligacao_id, empregado=empregado)

    if request.method == "POST":
        terminar_ligacao_projeto_empregado(ligacao)

        messages.success(request, "Projeto encerrado para este empregado com sucesso.")
        return redirect("projetos:empregado_detail", pk=empregado.id)

    return render(request, "projetos/empregado_projeto_confirm_terminar.html", {
        "empregado": empregado,
        "ligacao": ligacao,
    })


@login_required
@admin_required
def empregado_adicionar_ficheiro(request, pk):
    empregado = get_object_or_404(Empregados, pk=pk)

    if request.method == "POST":
        form = EmpregadoFicheiroForm(request.POST, request.FILES)
        if form.is_valid():
            ficheiro = form.save(commit=False)
            ficheiro.empregado = empregado
            ficheiro.save()
            messages.success(request, "Ficheiro adicionado com sucesso.")
            return redirect("projetos:empregado_detail", pk=empregado.id)
        else:
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
    empregado = get_object_or_404(Empregados, pk=pk)
    ficheiro = get_object_or_404(EmpregadoFicheiro, id=ficheiro_id, empregado=empregado)

    if request.method == "POST":
        if ficheiro.ficheiro:
            ficheiro.ficheiro.delete(save=False)
        ficheiro.delete()
        messages.success(request, "Ficheiro removido com sucesso.")
        return redirect("projetos:empregado_detail", pk=empregado.id)

    return render(request, "projetos/empregado_ficheiro_confirm_delete.html", {
        "empregado": empregado,
        "ficheiro": ficheiro,
    })


@login_required
@admin_required
def empregado_pendentes(request):
    empregados = obter_empregados_pendentes()
    return render(request, "projetos/empregado_pendentes.html", {
        "empregados": empregados,
        "titulo": "Empregados Pendentes de Aprovação",
    })


@login_required
@admin_required
def empregado_aprovar(request, pk):
    empregado = get_object_or_404(Empregados, pk=pk)

    if request.method == "POST":
        aprovar_empregado(empregado)
        user, password_temporaria, criado_agora = _criar_user_para_empregado(empregado)

        if criado_agora:
            messages.success(
                request,
                (
                    f"Empregado aprovado com sucesso. "
                    f"Utilizador: {user.username} | Palavra-passe temporária: {password_temporaria}"
                ),
            )
        else:
            messages.success(
                request,
                f"Empregado aprovado com sucesso. Utilizador associado: {user.username}",
            )

        return redirect("projetos:empregado_pendentes")

    return render(request, "projetos/empregado_aprovar_confirm.html", {
        "empregado": empregado,
    })


#-------------- AREA EMPREGADO ------------- #
@login_required
def area_empregado(request):
    empregado = Empregados.objects.filter(user=request.user).first()

    if not empregado:
        messages.error(
            request,
            "A tua conta ainda não está ligada a um registo de empregado. Contacta o administrador.",
        )
        return redirect("login")

    furos_trabalhados = Furo.objects.filter(
        registos_furo__empregado=empregado
    ).distinct()

    ultimos_registos = empregado.registos_diarios.select_related(
        "projeto", "furo"
    ).all()[:5]

    configuracoes_perfuracao = empregado.configuracoes_perfuracao.select_related(
        "furo", "atualizado_por"
    ).all().order_by("furo__nome")

    horas_hoje = empregado.horas_diarias or 0
    horas_mes = empregado.horas_trabalhadas_mes or 0
    horas_total = empregado.horas_total or 0

    metros_hoje = empregado.metros_furados_hoje or 0
    metros_total = empregado.total_metros_furados or 0

    total_furos = empregado.total_furos_trabalhados or 0
    media_metros_hora = empregado.media_metros_por_hora or 0
    media_metros_dia = empregado.media_metros_por_dia or 0

    registos_grafico = empregado.registos_diarios.order_by("data")

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
    if not request.user.is_authenticated:
        return redirect("login")

    if request.user.is_staff:
        return redirect("projetos:dashboard")

    empregado = Empregados.objects.filter(user=request.user).first()
    if empregado and empregado.aprovado:
        return redirect("projetos:area_empregado")

    messages.error(
        request,
        "A tua conta ainda não foi aprovada ou não está configurada corretamente. Contacta o administrador.",
    )
    return redirect("logout")


def redirect_view(request):
    if not request.user.is_authenticated:
        return redirect("login")

    if request.user.is_staff:
        return redirect("projetos:dashboard")

    empregado = Empregados.objects.filter(user=request.user).first()

    if empregado and empregado.aprovado:
        return redirect("projetos:area_empregado")

    return redirect("login")


@login_required
@empregado_required
def configuracao_perfuracao_list_empregado(request):
    empregado = get_object_or_404(Empregados, user=request.user)
    configuracoes = obter_lista_configuracoes_perfuracao_empregado(empregado)

    return render(request, "projetos/configuracao_perfuracao_list.html", {
        "empregado": empregado,
        "configuracoes": configuracoes,
        "modo_admin": False,
    })


@login_required
@empregado_required
def configuracao_perfuracao_create_empregado(request):
    empregado = get_object_or_404(Empregados, user=request.user)

    if request.method == "POST":
        form = ConfiguracaoPerfuracaoEmpregadoForm(request.POST, empregado=empregado)
        if form.is_valid():
            configuracao = form.save(commit=False)
            configuracao.empregado = empregado
            configuracao.atualizado_por = request.user
            configuracao.save()

            messages.success(request, "Configuração de perfuração criada com sucesso.")
            return redirect("projetos:configuracao_perfuracao_list_empregado")

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
    empregado = get_object_or_404(Empregados, user=request.user)
    configuracao = get_object_or_404(
        ConfiguracaoPerfuracaoEmpregado,
        pk=pk,
        empregado=empregado
    )

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
            configuracao.save()

            messages.success(request, "Configuração de perfuração atualizada com sucesso.")
            return redirect("projetos:configuracao_perfuracao_list_empregado")

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
        "modo_admin": False,
    })


@login_required
@admin_required
def configuracao_perfuracao_list_admin(request, pk):
    empregado = get_object_or_404(Empregados, pk=pk)
    configuracoes = obter_lista_configuracoes_perfuracao_empregado(empregado)

    return render(request, "projetos/configuracao_perfuracao_list.html", {
        "empregado": empregado,
        "configuracoes": configuracoes,
        "modo_admin": True,
    })


@login_required
@admin_required
def configuracao_perfuracao_create_admin(request, pk):
    empregado = get_object_or_404(Empregados, pk=pk)

    if request.method == "POST":
        form = ConfiguracaoPerfuracaoEmpregadoForm(request.POST, empregado=empregado)
        if form.is_valid():
            configuracao = form.save(commit=False)
            configuracao.empregado = empregado
            configuracao.atualizado_por = request.user
            configuracao.save()

            messages.success(request, "Configuração de perfuração criada com sucesso.")
            return redirect("projetos:configuracao_perfuracao_list_admin", pk=empregado.pk)

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
    configuracao = obter_configuracao_perfuracao(pk)
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
            configuracao.save()

            messages.success(request, "Configuração de perfuração atualizada com sucesso.")
            return redirect("projetos:configuracao_perfuracao_list_admin", pk=empregado.pk)

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