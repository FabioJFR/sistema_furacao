from plataforma.feature_flags import obter_catalogo_features, obter_estado_base_feature
from plataforma.models import ConfiguracaoFeatureAcesso
from plataforma.selectors.features import obter_filtro_override_features


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
