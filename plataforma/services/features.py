from plataforma.feature_flags import obter_catalogo_features, obter_estado_base_feature
from plataforma.models import ConfiguracaoFeatureAcesso
from plataforma.selectors.features import (
    agrupar_features_por_grupo,
    construir_entidades_empresa_features,
    construir_entidades_individuais_features,
    construir_linhas_features,
    listar_entidades_features,
    obter_filtro_override_features,
    resolver_alvo_features,
)


def atualizar_overrides_features(*, tipo_alvo, alvo, features_ativas):
    filtro_override = obter_filtro_override_features(tipo_alvo, alvo)

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


def resolver_contexto_features_dashboard(*, tipo_param, alvo_param):
    empresas, perfis_individuais = listar_entidades_features()
    tipo_alvo, alvo = resolver_alvo_features(
        tipo_alvo=tipo_param,
        alvo_id=alvo_param,
        empresas=empresas,
        perfis_individuais=perfis_individuais,
    )
    linhas_features = construir_linhas_features(tipo_alvo=tipo_alvo, alvo=alvo) if alvo else []

    return {
        "tipo_alvo": tipo_alvo,
        "alvo": alvo,
        "entidades_empresa": construir_entidades_empresa_features(empresas),
        "entidades_individuais": construir_entidades_individuais_features(perfis_individuais),
        "features_por_grupo": agrupar_features_por_grupo(linhas_features),
        "total_features_catalogo": len(obter_catalogo_features()),
    }


def processar_submissao_features_dashboard(*, post_data, tipo_alvo, alvo):
    if alvo is None:
        return {
            "ok": False,
            "mensagem_erro": "Seleciona primeiro uma entidade para gerir as features.",
            "redirect_url": None,
        }

    features_ativas = set(post_data.getlist("features"))
    atualizar_overrides_features(
        tipo_alvo=tipo_alvo,
        alvo=alvo,
        features_ativas=features_ativas,
    )

    return {
        "ok": True,
        "mensagem_sucesso": "Features atualizadas com sucesso.",
        "redirect_url": f"?tipo={tipo_alvo}&alvo={alvo.pk}",
    }
