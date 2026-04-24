from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render

from core.permissions import admin_required

from projetos.selectors.acesso import obter_contexto_admin_projetos
from projetos.selectors.analytics import (
    obter_entidades_analytics_disponiveis,
    obter_eventos_analytics_filtrados,
    obter_resumo_tipos_evento_analytics,
)


def _obter_empresa_admin_analytics(request):
    contexto_admin = obter_contexto_admin_projetos(request.user)
    if not contexto_admin:
        messages.error(request, "Não tens permissão para aceder a esta área.")
        return None, redirect("projetos:redirect_after_login")

    empresa = getattr(contexto_admin, "empresa", None)
    empresa_id = getattr(contexto_admin, "empresa_id", None)
    if not empresa_id or not empresa:
        messages.error(request, "O utilizador administrador não está associado a uma empresa.")
        return None, redirect("projetos:dashboard")

    return empresa, None


@login_required
@admin_required
def analytics_eventos(request):
    empresa, resposta_erro = _obter_empresa_admin_analytics(request)
    if resposta_erro:
        return resposta_erro

    filtros = {
        "tipo_evento": request.GET.get("tipo_evento", "").strip(),
        "entidade_tipo": request.GET.get("entidade_tipo", "").strip(),
        "projeto": request.GET.get("projeto", "").strip(),
        "furo": request.GET.get("furo", "").strip(),
    }

    eventos = obter_eventos_analytics_filtrados(empresa, filtros)
    entidades_disponiveis = obter_entidades_analytics_disponiveis(empresa)
    resumo_tipo = obter_resumo_tipos_evento_analytics(empresa)

    context = {
        "eventos": eventos[:150],
        "entidades_disponiveis": entidades_disponiveis,
        "filtros": filtros,
        "total_eventos": eventos.count(),
        "total_criacoes": resumo_tipo.get("create", 0),
        "total_atualizacoes": resumo_tipo.get("update", 0),
        "total_eliminacoes": resumo_tipo.get("delete", 0),
        "projetos_filtro": empresa.projetos.all().order_by("nome"),
        "furos_filtro": empresa.furos.all().order_by("nome"),
    }
    return render(request, "projetos/analytics_eventos.html", context)
