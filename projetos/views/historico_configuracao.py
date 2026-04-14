from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect

from core.permissions import admin_required
from projetos.decorators import empregado_required
from projetos.models import (
    Empregados,
    Furo,
    HistoricoConfiguracaoPerfuracao,
    ConfiguracaoPerfuracaoEmpregado,
)
from projetos.selectors.historico_configuracao import (
    obter_historico_configuracao_por_empregado,
    obter_historico_configuracao_por_furo,
    obter_historico_anterior,
)


@login_required
@empregado_required
def historico_configuracao_list_empregado(request):
    empregado = get_object_or_404(Empregados, user=request.user)
    historicos = obter_historico_configuracao_por_empregado(empregado)

    return render(request, "projetos/historico_configuracao_list_empregado.html", {
        "empregado": empregado,
        "historicos": historicos,
    })


@login_required
@admin_required
def historico_configuracao_list_admin(request, pk):
    empregado = get_object_or_404(Empregados, pk=pk)
    historicos = obter_historico_configuracao_por_empregado(empregado)

    return render(request, "projetos/historico_configuracao_list_admin.html", {
        "empregado_obj": empregado,
        "historicos": historicos,
    })


@login_required
@admin_required
def historico_configuracao_list_furo_admin(request, furo_id):
    furo = get_object_or_404(Furo, pk=furo_id)
    historicos = obter_historico_configuracao_por_furo(furo)

    return render(request, "projetos/historico_configuracao_list_furo_admin.html", {
        "furo": furo,
        "historicos": historicos,
    })


@login_required
def historico_configuracao_detail(request, pk):
    historico = get_object_or_404(
        HistoricoConfiguracaoPerfuracao.objects.select_related(
            "empregado", "furo", "alterado_por", "configuracao"
        ),
        pk=pk
    )

    if request.user.is_staff:
        permitido = True
    else:
        empregado = Empregados.objects.filter(user=request.user).first()
        permitido = bool(empregado and historico.empregado_id == empregado.id)

    if not permitido:
        return render(request, "projetos/sem_permissao.html", status=403)

    historico_anterior = obter_historico_anterior(historico)

    return render(request, "projetos/historico_configuracao_detail.html", {
        "historico": historico,
        "historico_anterior": historico_anterior,
    })


@login_required
def historico_configuracao_comparar(request, pk):
    historico = get_object_or_404(
        HistoricoConfiguracaoPerfuracao.objects.select_related(
            "empregado", "furo", "alterado_por", "configuracao"
        ),
        pk=pk
    )

    if request.user.is_staff:
        permitido = True
    else:
        empregado = Empregados.objects.filter(user=request.user).first()
        permitido = bool(empregado and historico.empregado_id == empregado.id)

    if not permitido:
        return render(request, "projetos/sem_permissao.html", status=403)

    anterior = obter_historico_anterior(historico)

    campos = [
        ("comprimento_tubo", "Tubo"),
        ("comprimento_karoutier", "Karoutier"),
        ("comprimento_acrescento", "Acrescento"),
        ("comprimento_calibrador", "Calibrador"),
        ("comprimento_record", "Record"),
        ("comprimento_bit", "Bit"),
        ("comprimento_caixa_mola", "Caixa de mola"),
        ("comprimento_tubo_interior", "Tubo interior"),
        ("comprimento_cabeca_interior", "Cabeça de interior"),
    ]

    comparacao = []

    for campo, label in campos:
        valor_atual = getattr(historico, campo, None)
        valor_anterior = getattr(anterior, campo, None) if anterior else None
        alterado = valor_atual != valor_anterior

        comparacao.append({
            "campo": campo,
            "label": label,
            "anterior": valor_anterior,
            "atual": valor_atual,
            "alterado": alterado,
        })

    return render(request, "projetos/historico_configuracao_comparar.html", {
        "historico": historico,
        "historico_anterior": anterior,
        "comparacao": comparacao,
    })


@login_required
def historico_configuracao_restaurar(request, pk):
    historico = get_object_or_404(
        HistoricoConfiguracaoPerfuracao.objects.select_related(
            "empregado", "furo", "configuracao"
        ),
        pk=pk
    )

    if request.user.is_staff:
        permitido = True
    else:
        empregado = Empregados.objects.filter(user=request.user).first()
        permitido = bool(empregado and historico.empregado_id == empregado.id)

    if not permitido:
        return render(request, "projetos/sem_permissao.html", status=403)

    if request.method == "POST":
        configuracao = historico.configuracao

        if configuracao is None:
            configuracao = ConfiguracaoPerfuracaoEmpregado.objects.create(
                empregado=historico.empregado,
                furo=historico.furo,
                comprimento_tubo=historico.comprimento_tubo,
                comprimento_karoutier=historico.comprimento_karoutier,
                comprimento_acrescento=historico.comprimento_acrescento,
                comprimento_calibrador=historico.comprimento_calibrador,
                comprimento_record=historico.comprimento_record,
                comprimento_bit=historico.comprimento_bit,
                comprimento_caixa_mola=historico.comprimento_caixa_mola,
                comprimento_tubo_interior=historico.comprimento_tubo_interior,
                comprimento_cabeca_interior=historico.comprimento_cabeca_interior,
                atualizado_por=request.user,
            )
        else:
            configuracao.empregado = historico.empregado
            configuracao.furo = historico.furo
            configuracao.comprimento_tubo = historico.comprimento_tubo
            configuracao.comprimento_karoutier = historico.comprimento_karoutier
            configuracao.comprimento_acrescento = historico.comprimento_acrescento
            configuracao.comprimento_calibrador = historico.comprimento_calibrador
            configuracao.comprimento_record = historico.comprimento_record
            configuracao.comprimento_bit = historico.comprimento_bit
            configuracao.comprimento_caixa_mola = historico.comprimento_caixa_mola
            configuracao.comprimento_tubo_interior = historico.comprimento_tubo_interior
            configuracao.comprimento_cabeca_interior = historico.comprimento_cabeca_interior
            configuracao.atualizado_por = request.user
            configuracao.save()

        HistoricoConfiguracaoPerfuracao.registar_historico(
            configuracao=configuracao,
            acao="editado",
            utilizador=request.user,
            observacoes=f"Configuração restaurada a partir do histórico #{historico.pk}."
        )

        messages.success(request, "Versão restaurada com sucesso.")

        if request.user.is_staff:
            return redirect("projetos:configuracao_perfuracao_list_admin", pk=historico.empregado.pk)

        return redirect("projetos:configuracao_perfuracao_list_empregado")

    return render(request, "projetos/historico_configuracao_restaurar.html", {
        "historico": historico,
    })