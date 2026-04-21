from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render

from core.permissions import admin_required

from projetos.models import EventoAnalytics

from .projetos import _obter_empresa_admin_projetos


@login_required
@admin_required
def analytics_eventos(request):
    empresa, resposta_erro = _obter_empresa_admin_projetos(request)
    if resposta_erro:
        return resposta_erro

    filtros = {
        "tipo_evento": request.GET.get("tipo_evento", "").strip(),
        "entidade_tipo": request.GET.get("entidade_tipo", "").strip(),
        "projeto": request.GET.get("projeto", "").strip(),
        "furo": request.GET.get("furo", "").strip(),
    }

    eventos = (
        EventoAnalytics.objects.filter(empresa_id=getattr(empresa, "pk", empresa))
        .select_related("projeto", "furo", "empregado", "material", "maquina", "actor_user")
        .order_by("-criado_em")
    )

    if filtros["tipo_evento"]:
        eventos = eventos.filter(tipo_evento=filtros["tipo_evento"])
    if filtros["entidade_tipo"]:
        eventos = eventos.filter(entidade_tipo=filtros["entidade_tipo"])
    if filtros["projeto"]:
        eventos = eventos.filter(projeto_id=filtros["projeto"])
    if filtros["furo"]:
        eventos = eventos.filter(furo_id=filtros["furo"])

    entidades_disponiveis = (
        EventoAnalytics.objects.filter(empresa_id=getattr(empresa, "pk", empresa))
        .values_list("entidade_tipo", flat=True)
        .distinct()
        .order_by("entidade_tipo")
    )

    resumo_tipo = {
        item["tipo_evento"]: item["total"]
        for item in (
            EventoAnalytics.objects.filter(empresa_id=getattr(empresa, "pk", empresa))
            .values("tipo_evento")
            .annotate(total=Count("id"))
        )
    }

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
