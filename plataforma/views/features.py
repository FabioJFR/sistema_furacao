from collections import OrderedDict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from plataforma.decorators import platform_admin_required
from plataforma.feature_flags import (
    feature_ativa_para_contexto,
    obter_catalogo_features,
    obter_estado_base_feature,
)
from plataforma.models import ConfiguracaoFeatureAcesso, Empresa, PerfilPlataforma


def _obter_alvo_features(request):
    tipo_alvo = (request.GET.get("tipo") or request.POST.get("tipo") or "empresa").strip()
    alvo_id = (request.GET.get("alvo") or request.POST.get("alvo") or "").strip()

    empresas = Empresa.objects.select_related("plano").order_by("nome")
    perfis_individuais = (
        PerfilPlataforma.objects.select_related("user")
        .filter(tipo_acesso="individual", ativo=True)
        .order_by("user__username")
    )

    if tipo_alvo == "individual":
        alvo = perfis_individuais.filter(pk=alvo_id).first() if alvo_id else perfis_individuais.first()
    else:
        tipo_alvo = "empresa"
        alvo = empresas.filter(pk=alvo_id).first() if alvo_id else empresas.first()

    return tipo_alvo, alvo, empresas, perfis_individuais


def _obter_filtro_override(tipo_alvo, alvo):
    if tipo_alvo == "individual":
        return {"perfil_plataforma": alvo}
    return {"empresa": alvo}


def _construir_linhas_features(*, tipo_alvo, alvo):
    overrides_qs = ConfiguracaoFeatureAcesso.objects.filter(**_obter_filtro_override(tipo_alvo, alvo))
    overrides = {item.chave_feature: item for item in overrides_qs}

    linhas = []
    for feature in obter_catalogo_features():
        chave = feature["key"]
        base_ativa = obter_estado_base_feature(
            empresa=alvo if tipo_alvo == "empresa" else None,
            perfil_plataforma=alvo if tipo_alvo == "individual" else None,
            chave_feature=chave,
        )
        override = overrides.get(chave)
        ativa_final = feature_ativa_para_contexto(
            chave_feature=chave,
            empresa=alvo if tipo_alvo == "empresa" else None,
            perfil_plataforma=alvo if tipo_alvo == "individual" else None,
        )
        linhas.append(
            {
                "key": chave,
                "label": feature["label"],
                "description": feature["description"],
                "group": feature["group"],
                "base_ativa": base_ativa,
                "ativa_final": ativa_final,
                "tem_override": override is not None,
                "override_ativa": getattr(override, "ativa", None),
            }
        )
    return linhas


def _agrupar_features(linhas):
    grupos = OrderedDict()
    for linha in linhas:
        grupos.setdefault(linha["group"], []).append(linha)
    return grupos


def _contar_features_ativas(*, tipo_alvo, alvo):
    return sum(1 for linha in _construir_linhas_features(tipo_alvo=tipo_alvo, alvo=alvo) if linha["ativa_final"])


@login_required
@platform_admin_required
def features_dashboard(request):
    if not request.user.is_superuser:
        messages.error(request, "A gestão global de features está reservada ao superuser.")
        return redirect("plataforma:dashboard")

    tipo_alvo, alvo, empresas, perfis_individuais = _obter_alvo_features(request)

    if request.method == "POST":
        if alvo is None:
            messages.error(request, "Seleciona primeiro uma entidade para gerir as features.")
            return redirect("plataforma:features_dashboard")

        features_ativas = set(request.POST.getlist("features"))
        filtro_override = _obter_filtro_override(tipo_alvo, alvo)

        for feature in obter_catalogo_features():
            chave = feature["key"]
            base_ativa = obter_estado_base_feature(
                empresa=alvo if tipo_alvo == "empresa" else None,
                perfil_plataforma=alvo if tipo_alvo == "individual" else None,
                chave_feature=chave,
            )
            ativa_desejada = chave in features_ativas

            if ativa_desejada == base_ativa:
                ConfiguracaoFeatureAcesso.objects.filter(
                    chave_feature=chave,
                    **filtro_override,
                ).delete()
            else:
                ConfiguracaoFeatureAcesso.objects.update_or_create(
                    chave_feature=chave,
                    defaults={"ativa": ativa_desejada},
                    **filtro_override,
                )

        messages.success(request, "Features atualizadas com sucesso.")
        return redirect(f"{request.path}?tipo={tipo_alvo}&alvo={alvo.pk}")

    linhas_features = _construir_linhas_features(tipo_alvo=tipo_alvo, alvo=alvo) if alvo else []

    entidades_empresa = [
        {
            "tipo": "empresa",
            "pk": empresa.pk,
            "label": empresa.nome,
            "subtitulo": empresa.plano.nome if empresa.plano_id else "Sem plano",
            "features_ativas": _contar_features_ativas(tipo_alvo="empresa", alvo=empresa),
        }
        for empresa in empresas
    ]
    entidades_individuais = [
        {
            "tipo": "individual",
            "pk": perfil.pk,
            "label": perfil.user.get_full_name() or perfil.user.username,
            "subtitulo": "Conta individual",
            "features_ativas": _contar_features_ativas(tipo_alvo="individual", alvo=perfil),
        }
        for perfil in perfis_individuais
    ]

    context = {
        "tipo_alvo": tipo_alvo,
        "alvo": alvo,
        "entidades_empresa": entidades_empresa,
        "entidades_individuais": entidades_individuais,
        "features_por_grupo": _agrupar_features(linhas_features),
        "total_features_catalogo": len(obter_catalogo_features()),
    }
    return render(request, "plataforma/features_dashboard.html", context)
