from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import translation

from core.permissions import admin_required

from projetos.forms import PreferenciasForm
from projetos.models import (
    Despesa,
    Empregados,
    EventoAnalytics,
    Furo,
    Maquina,
    Material,
    Medicao,
    PreferenciasUser,
    Projeto,
    RegistoDiarioEmpregado,
)

from .projetos import _obter_empresa_admin_projetos


def _empresa_id(empresa):
    return getattr(empresa, "pk", empresa)


@login_required
@admin_required
def definicoes_admin(request):
    empresa, resposta_erro = _obter_empresa_admin_projetos(request)
    if resposta_erro:
        return resposta_erro

    preferencias, _ = PreferenciasUser.objects.get_or_create(user=request.user)
    preferencias.empresa = empresa
    preferencias.save(update_fields=["empresa"])

    if request.method == "POST":
        form = PreferenciasForm(request.POST, instance=preferencias, user=request.user)
        if form.is_valid():
            preferencias = form.save(commit=False)
            preferencias.user = request.user
            preferencias.empresa = empresa
            preferencias.save()

            if preferencias.idioma:
                translation.activate(preferencias.idioma)
                request.session["django_language"] = preferencias.idioma

            messages.success(request, "Definições guardadas com sucesso.")
            return redirect("projetos:definicoes_admin")

        messages.error(request, "Erro ao guardar definições.")
    else:
        form = PreferenciasForm(instance=preferencias, user=request.user)

    return render(
        request,
        "projetos/definicoes_admin.html",
        {
            "form": form,
            "titulo": "Definições da Empresa",
            "empresa": empresa,
        },
    )


@login_required
@admin_required
def procurar_dashboard(request):
    empresa, resposta_erro = _obter_empresa_admin_projetos(request)
    if resposta_erro:
        return resposta_erro

    termo = request.GET.get("q", "").strip()
    empresa_id = _empresa_id(empresa)

    resultados = {
        "projetos": Projeto.objects.none(),
        "furos": Furo.objects.none(),
        "empregados": Empregados.objects.none(),
        "maquinas": Maquina.objects.none(),
        "materiais": Material.objects.none(),
        "registos": RegistoDiarioEmpregado.objects.none(),
        "medicoes": Medicao.objects.none(),
        "despesas": Despesa.objects.none(),
        "eventos": EventoAnalytics.objects.none(),
    }
    totais = {chave: 0 for chave in resultados}

    if termo:
        resultados["projetos"] = (
            Projeto.objects.filter(empresa_id=empresa_id)
            .filter(
                Q(nome__icontains=termo)
                | Q(cliente__icontains=termo)
                | Q(cidade__icontains=termo)
                | Q(pais__icontains=termo)
                | Q(notas__icontains=termo)
            )
            .order_by("nome")[:12]
        )
        resultados["furos"] = (
            Furo.objects.filter(empresa_id=empresa_id)
            .select_related("projeto")
            .filter(
                Q(nome__icontains=termo)
                | Q(localizacao__icontains=termo)
                | Q(local_sondagem__icontains=termo)
                | Q(detalhes__icontains=termo)
            )
            .order_by("nome")[:12]
        )
        resultados["empregados"] = (
            Empregados.objects.filter(empresa_id=empresa_id)
            .filter(
                Q(nome__icontains=termo)
                | Q(email__icontains=termo)
                | Q(telefone__icontains=termo)
                | Q(funcao__icontains=termo)
                | Q(morada__icontains=termo)
            )
            .order_by("nome")[:12]
        )
        resultados["maquinas"] = (
            Maquina.objects.filter(empresa_id=empresa_id)
            .filter(
                Q(nome__icontains=termo)
                | Q(tipo__icontains=termo)
                | Q(marca__icontains=termo)
                | Q(modelo__icontains=termo)
                | Q(numero_serie__icontains=termo)
                | Q(matricula__icontains=termo)
                | Q(localizacao_atual__icontains=termo)
            )
            .order_by("nome")[:12]
        )
        resultados["materiais"] = (
            Material.objects.filter(empresa_id=empresa_id)
            .select_related("projeto", "furo")
            .filter(
                Q(nome__icontains=termo)
                | Q(tipo__icontains=termo)
                | Q(marca__icontains=termo)
                | Q(numero_serie__icontains=termo)
                | Q(fornecedor__icontains=termo)
                | Q(localizacao__icontains=termo)
                | Q(observacoes__icontains=termo)
            )
            .order_by("nome")[:12]
        )
        resultados["registos"] = (
            RegistoDiarioEmpregado.objects.filter(empresa_id=empresa_id)
            .select_related("empregado", "projeto", "furo")
            .filter(
                Q(observacoes__icontains=termo)
                | Q(empregado__nome__icontains=termo)
                | Q(projeto__nome__icontains=termo)
                | Q(furo__nome__icontains=termo)
            )
            .order_by("-data", "-criado_em")[:12]
        )
        resultados["medicoes"] = (
            Medicao.objects.filter(empresa_id=empresa_id)
            .select_related("furo")
            .filter(
                Q(nome_furo_snapshot__icontains=termo)
                | Q(tipo_rocha__icontains=termo)
                | Q(observacoes__icontains=termo)
                | Q(furo__nome__icontains=termo)
            )
            .order_by("-criado_em")[:12]
        )
        resultados["despesas"] = (
            Despesa.objects.filter(empresa_id=empresa_id)
            .select_related("projeto", "furo", "maquina")
            .filter(
                Q(descricao__icontains=termo)
                | Q(tipo__icontains=termo)
                | Q(categoria__icontains=termo)
                | Q(observacoes__icontains=termo)
            )
            .order_by("-data", "-criado_em")[:12]
        )
        resultados["eventos"] = (
            EventoAnalytics.objects.filter(empresa_id=empresa_id)
            .select_related("projeto", "furo", "empregado", "material", "maquina")
            .filter(
                Q(entidade_tipo__icontains=termo)
                | Q(entidade_label__icontains=termo)
                | Q(actor_username__icontains=termo)
            )
            .order_by("-criado_em")[:20]
        )

        totais = {
            "projetos": Projeto.objects.filter(empresa_id=empresa_id).filter(
                Q(nome__icontains=termo)
                | Q(cliente__icontains=termo)
                | Q(cidade__icontains=termo)
                | Q(pais__icontains=termo)
                | Q(notas__icontains=termo)
            ).count(),
            "furos": Furo.objects.filter(empresa_id=empresa_id).filter(
                Q(nome__icontains=termo)
                | Q(localizacao__icontains=termo)
                | Q(local_sondagem__icontains=termo)
                | Q(detalhes__icontains=termo)
            ).count(),
            "empregados": Empregados.objects.filter(empresa_id=empresa_id).filter(
                Q(nome__icontains=termo)
                | Q(email__icontains=termo)
                | Q(telefone__icontains=termo)
                | Q(funcao__icontains=termo)
                | Q(morada__icontains=termo)
            ).count(),
            "maquinas": Maquina.objects.filter(empresa_id=empresa_id).filter(
                Q(nome__icontains=termo)
                | Q(tipo__icontains=termo)
                | Q(marca__icontains=termo)
                | Q(modelo__icontains=termo)
                | Q(numero_serie__icontains=termo)
                | Q(matricula__icontains=termo)
                | Q(localizacao_atual__icontains=termo)
            ).count(),
            "materiais": Material.objects.filter(empresa_id=empresa_id).filter(
                Q(nome__icontains=termo)
                | Q(tipo__icontains=termo)
                | Q(marca__icontains=termo)
                | Q(numero_serie__icontains=termo)
                | Q(fornecedor__icontains=termo)
                | Q(localizacao__icontains=termo)
                | Q(observacoes__icontains=termo)
            ).count(),
            "registos": RegistoDiarioEmpregado.objects.filter(empresa_id=empresa_id).filter(
                Q(observacoes__icontains=termo)
                | Q(empregado__nome__icontains=termo)
                | Q(projeto__nome__icontains=termo)
                | Q(furo__nome__icontains=termo)
            ).count(),
            "medicoes": Medicao.objects.filter(empresa_id=empresa_id).filter(
                Q(nome_furo_snapshot__icontains=termo)
                | Q(tipo_rocha__icontains=termo)
                | Q(observacoes__icontains=termo)
                | Q(furo__nome__icontains=termo)
            ).count(),
            "despesas": Despesa.objects.filter(empresa_id=empresa_id).filter(
                Q(descricao__icontains=termo)
                | Q(tipo__icontains=termo)
                | Q(categoria__icontains=termo)
                | Q(observacoes__icontains=termo)
            ).count(),
            "eventos": EventoAnalytics.objects.filter(empresa_id=empresa_id).filter(
                Q(entidade_tipo__icontains=termo)
                | Q(entidade_label__icontains=termo)
                | Q(actor_username__icontains=termo)
            ).count(),
        }

    return render(
        request,
        "projetos/procurar_dashboard.html",
        {
            "empresa": empresa,
            "termo": termo,
            "resultados": resultados,
            "totais": totais,
        },
    )
