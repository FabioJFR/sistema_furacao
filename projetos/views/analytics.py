from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.permissions import admin_required

from projetos.services.acesso_contexto import obter_empresa_admin_contexto
from projetos.selectors.analytics import (
    obter_entidades_analytics_disponiveis,
    obter_eventos_analytics_filtrados,
    obter_resumo_tipos_evento_analytics,
)


def _obter_empresa_admin_analytics(request):
    return obter_empresa_admin_contexto(
        request=request,
        mensagem_sem_permissao="Não tens permissão para aceder a esta área.",
        mensagem_sem_empresa="O utilizador administrador não está associado a uma empresa.",
        redirect_sem_permissao="projetos:redirect_after_login",
        redirect_sem_empresa="projetos:dashboard",
    )


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
