from collections import OrderedDict

from plataforma.feature_flags import (
    feature_ativa_para_contexto,
    obter_catalogo_features,
    obter_estado_base_feature,
)
from plataforma.models import ConfiguracaoFeatureAcesso, Empresa, PerfilPlataforma


def normalizar_tipo_alvo_features(tipo_alvo):
    return "individual" if tipo_alvo == "individual" else "empresa"


def listar_entidades_features():
    empresas = Empresa.objects.select_related("plano").order_by("nome")
    perfis_individuais = (
        PerfilPlataforma.objects.select_related("user")
        .filter(tipo_acesso="individual", ativo=True)
        .order_by("user__username")
    )
    return empresas, perfis_individuais


def resolver_alvo_features(*, tipo_alvo, alvo_id, empresas, perfis_individuais):
    tipo_alvo_normalizado = normalizar_tipo_alvo_features(tipo_alvo)
    if tipo_alvo_normalizado == "individual":
        alvo = perfis_individuais.filter(pk=alvo_id).first() if alvo_id else perfis_individuais.first()
    else:
        alvo = empresas.filter(pk=alvo_id).first() if alvo_id else empresas.first()
    return tipo_alvo_normalizado, alvo


def obter_filtro_override_features(tipo_alvo, alvo):
    if tipo_alvo == "individual":
        return {"perfil_plataforma": alvo}
    return {"empresa": alvo}


def obter_overrides_features(tipo_alvo, alvo):
    if alvo is None:
        return {}
    queryset = ConfiguracaoFeatureAcesso.objects.filter(
        **obter_filtro_override_features(tipo_alvo, alvo),
    )
    return {item.chave_feature: item for item in queryset}


def obter_override_feature_individual(chave_feature, perfil_plataforma):
    if perfil_plataforma is None:
        return None
    return (
        ConfiguracaoFeatureAcesso.objects.filter(
            perfil_plataforma=perfil_plataforma,
            chave_feature=chave_feature,
        )
        .only("ativa")
        .first()
    )


def obter_override_feature_empresa(chave_feature, empresa):
    if empresa is None:
        return None
    return (
        ConfiguracaoFeatureAcesso.objects.filter(
            empresa=empresa,
            chave_feature=chave_feature,
        )
        .only("ativa")
        .first()
    )


def construir_linhas_features(*, tipo_alvo, alvo):
    if alvo is None:
        return []

    overrides = obter_overrides_features(tipo_alvo, alvo)
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


def agrupar_features_por_grupo(linhas):
    grupos = OrderedDict()
    for linha in linhas:
        grupos.setdefault(linha["group"], []).append(linha)
    return grupos


def contar_features_ativas(*, tipo_alvo, alvo):
    return sum(1 for linha in construir_linhas_features(tipo_alvo=tipo_alvo, alvo=alvo) if linha["ativa_final"])


def construir_entidades_empresa_features(empresas):
    return [
        {
            "tipo": "empresa",
            "pk": empresa.pk,
            "label": empresa.nome,
            "subtitulo": empresa.plano.nome if empresa.plano_id else "Sem plano",
            "features_ativas": contar_features_ativas(tipo_alvo="empresa", alvo=empresa),
        }
        for empresa in empresas
    ]


def construir_entidades_individuais_features(perfis_individuais):
    return [
        {
            "tipo": "individual",
            "pk": perfil.pk,
            "label": perfil.user.get_full_name() or perfil.user.username,
            "subtitulo": "Conta individual",
            "features_ativas": contar_features_ativas(tipo_alvo="individual", alvo=perfil),
        }
        for perfil in perfis_individuais
    ]
