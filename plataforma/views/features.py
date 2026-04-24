from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from plataforma.decorators import platform_admin_required
from plataforma.feature_flags import obter_catalogo_features
from plataforma.selectors.features import (
    agrupar_features_por_grupo,
    construir_entidades_empresa_features,
    construir_entidades_individuais_features,
    construir_linhas_features,
    listar_entidades_features,
    resolver_alvo_features,
)
from plataforma.services.features import atualizar_overrides_features


@login_required
@platform_admin_required
def features_dashboard(request):
    if not request.user.is_superuser:
        messages.error(request, "A gestão global de features está reservada ao superuser.")
        return redirect("plataforma:dashboard")

    tipo_alvo_param = (request.GET.get("tipo") or request.POST.get("tipo") or "empresa").strip()
    alvo_id_param = (request.GET.get("alvo") or request.POST.get("alvo") or "").strip()
    empresas, perfis_individuais = listar_entidades_features()
    tipo_alvo, alvo = resolver_alvo_features(
        tipo_alvo=tipo_alvo_param,
        alvo_id=alvo_id_param,
        empresas=empresas,
        perfis_individuais=perfis_individuais,
    )

    if request.method == "POST":
        if alvo is None:
            messages.error(request, "Seleciona primeiro uma entidade para gerir as features.")
            return redirect("plataforma:features_dashboard")

        features_ativas = set(request.POST.getlist("features"))
        atualizar_overrides_features(
            tipo_alvo=tipo_alvo,
            alvo=alvo,
            features_ativas=features_ativas,
        )

        messages.success(request, "Features atualizadas com sucesso.")
        return redirect(f"{request.path}?tipo={tipo_alvo}&alvo={alvo.pk}")

    linhas_features = construir_linhas_features(tipo_alvo=tipo_alvo, alvo=alvo) if alvo else []

    entidades_empresa = construir_entidades_empresa_features(empresas)
    entidades_individuais = construir_entidades_individuais_features(perfis_individuais)

    context = {
        "tipo_alvo": tipo_alvo,
        "alvo": alvo,
        "entidades_empresa": entidades_empresa,
        "entidades_individuais": entidades_individuais,
        "features_por_grupo": agrupar_features_por_grupo(linhas_features),
        "total_features_catalogo": len(obter_catalogo_features()),
    }
    return render(request, "plataforma/features_dashboard.html", context)
