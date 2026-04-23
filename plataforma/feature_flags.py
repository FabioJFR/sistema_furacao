FEATURE_FLAGS = [
    {
        "key": "dashboard_empresa",
        "label": "Dashboard da empresa",
        "description": "Acesso ao dashboard operacional principal de projetos.",
        "group": "Projetos",
        "plan_field": "acesso_dashboard_empresa",
        "default_enabled": False,
    },
    {
        "key": "painel_empregado",
        "label": "Painel do empregado",
        "description": "Permite usar a área operacional do empregado.",
        "group": "Projetos",
        "plan_field": "acesso_painel_empregado",
        "default_enabled": False,
    },
    {
        "key": "multiplos_utilizadores",
        "label": "Múltiplos utilizadores",
        "description": "Permite contas e gestão colaborativa dentro da mesma entidade.",
        "group": "Projetos",
        "plan_field": "permite_multiplos_utilizadores",
        "default_enabled": False,
    },
    {
        "key": "geologia",
        "label": "Geologia",
        "description": "Centro de geologia, logs e dashboards geológicos.",
        "group": "Geologia",
        "default_enabled": True,
    },
    {
        "key": "dji",
        "label": "DJI",
        "description": "Interface DJI Mini 4 Pro e respetiva bridge.",
        "group": "Geologia",
        "default_enabled": True,
    },
    {
        "key": "drone_sf",
        "label": "Drone S_F",
        "description": "Interface do drone próprio, sensores, bridge e missões.",
        "group": "Geologia",
        "default_enabled": True,
    },
    {
        "key": "ai_visual",
        "label": "AI Visual",
        "description": "Hub AI visual, análises e OCR experimental.",
        "group": "AI",
        "default_enabled": True,
    },
    {
        "key": "chatbox_ai",
        "label": "Chatbox AI",
        "description": "Assistente conversacional com memória operacional da empresa.",
        "group": "AI",
        "default_enabled": True,
    },
    {
        "key": "memoria_operacional_ai",
        "label": "Memória Operacional AI",
        "description": "Consulta de histórico de furos, zonas e contexto operacional.",
        "group": "AI",
        "default_enabled": True,
    },
    {
        "key": "analises_ai",
        "label": "Análises AI",
        "description": "Criação, histórico e reprocessamento de análises visuais.",
        "group": "AI",
        "default_enabled": True,
    },
    {
        "key": "dispositivos",
        "label": "Dispositivos",
        "description": "Dashboard de dispositivos, sessões e leituras brutas.",
        "group": "Plataforma",
        "default_enabled": True,
    },
    {
        "key": "uteis_exportacao",
        "label": "Úteis / exportação",
        "description": "Backups, exports e limpeza técnica de datasets.",
        "group": "Plataforma",
        "default_enabled": True,
    },
]

FEATURE_FLAGS_BY_KEY = {item["key"]: item for item in FEATURE_FLAGS}


def obter_catalogo_features():
    return FEATURE_FLAGS


def obter_definicao_feature(chave_feature):
    return FEATURE_FLAGS_BY_KEY.get(chave_feature)


def obter_estado_base_feature(*, empresa=None, perfil_plataforma=None, chave_feature):
    definicao = obter_definicao_feature(chave_feature)
    if not definicao:
        return False

    plan_field = definicao.get("plan_field")
    if empresa is not None and plan_field:
        plano = getattr(empresa, "plano", None)
        if plano is None:
            return False
        return bool(getattr(plano, plan_field, False))

    return bool(definicao.get("default_enabled", False))


def feature_ativa_para_contexto(*, chave_feature, user=None, empresa=None, perfil_plataforma=None):
    if user is not None and getattr(user, "is_superuser", False):
        return True

    from plataforma.models import ConfiguracaoFeatureAcesso

    override = None
    if perfil_plataforma is not None:
        override = (
            ConfiguracaoFeatureAcesso.objects.filter(
                perfil_plataforma=perfil_plataforma,
                chave_feature=chave_feature,
            )
            .only("ativa")
            .first()
        )

    if override is None and empresa is not None:
        override = (
            ConfiguracaoFeatureAcesso.objects.filter(
                empresa=empresa,
                chave_feature=chave_feature,
            )
            .only("ativa")
            .first()
        )

    if override is not None:
        return bool(override.ativa)

    return obter_estado_base_feature(
        empresa=empresa,
        perfil_plataforma=perfil_plataforma,
        chave_feature=chave_feature,
    )
