from datetime import timedelta

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from core.permissions import user_is_empresa_admin, user_is_empregado, user_is_platform_admin
from projetos.models import AssiduidadeRegisto, MaquinaAvaria, NotificacaoGestao
from projetos.selectors.acesso import obter_empregado_por_user, obter_perfil_ativo_por_user
from projetos.selectors.preferencias import obter_ou_criar_preferencias_user
from projetos.views.institucional import obter_ajuda_contextual


AJUDA_CONTEXTUAL_JANELA_UTILIZADOR_RECENTE_DIAS = 30


def menu_context(request):
    user = request.user

    if not user.is_authenticated:
        return {
            "is_admin_user": False,
            "is_empregado_user": False,
            "is_platform_admin": False,
            "is_empresa_admin": False,
            "is_platform_owner": False,
            "perfil_plataforma": None,
            "empregado_menu_obj": None,
            "empregado_menu_funcao": "",
            "tamanho_texto": "normal",
            "empresa_menu_logo_url": "",
            "total_pedidos_ferias_pendentes_menu": 0,
            "total_notificacoes_empregado_abertas_menu": 0,
            "ajuda_contextual_atual": None,
            "sf_mvp_operacional_focus": getattr(settings, "SF_MVP_OPERACIONAL_FOCUS", True),
        }

    perfil = obter_perfil_ativo_por_user(user)

    perfil_ativo = perfil is not None

    is_platform_owner = perfil_ativo and perfil.tipo_acesso == "platform_owner"
    is_platform_admin = user_is_platform_admin(user)
    is_empresa_admin = user_is_empresa_admin(user) and not is_platform_admin

    empregado_menu_obj = obter_empregado_por_user(user)

    is_admin_user = is_empresa_admin
    is_empregado_user = user_is_empregado(user)
    total_avarias_maquinas_abertas_menu = 0
    total_minhas_avarias_maquinas_abertas_menu = 0
    total_pedidos_ferias_pendentes_menu = 0
    total_notificacoes_empregado_abertas_menu = 0

    empresa_id_menu = getattr(perfil, "empresa_id", None) or getattr(empregado_menu_obj, "empresa_id", None)
    if is_admin_user and empresa_id_menu:
        total_avarias_maquinas_abertas_menu = MaquinaAvaria.objects.filter(
            empresa_id=empresa_id_menu,
            status__in=["aberta", "em_reparacao"],
        ).count()
        total_pedidos_ferias_pendentes_menu = AssiduidadeRegisto.objects.filter(
            empresa_id=empresa_id_menu,
            tipo="ferias",
            estado="pendente",
        ).count()
    elif is_platform_admin and empresa_id_menu:
        total_pedidos_ferias_pendentes_menu = AssiduidadeRegisto.objects.filter(
            empresa_id=empresa_id_menu,
            tipo="ferias",
            estado="pendente",
        ).count()
    if is_empregado_user and empregado_menu_obj and empregado_menu_obj.empresa_id:
        total_minhas_avarias_maquinas_abertas_menu = MaquinaAvaria.objects.filter(
            empresa_id=empregado_menu_obj.empresa_id,
            responsavel_empregado_id=empregado_menu_obj.id,
            status__in=["aberta", "em_reparacao"],
        ).count()
        total_notificacoes_empregado_abertas_menu = NotificacaoGestao.objects.filter(
            empresa_id=empregado_menu_obj.empresa_id,
            responsavel_id=empregado_menu_obj.id,
            estado__in=["aberta", "em_andamento"],
        ).count()

    preferencias = getattr(request, "sf_preferencias", None)
    if preferencias is None:
        preferencias, _ = obter_ou_criar_preferencias_user(user)

    empresa_menu = getattr(perfil, "empresa", None) or getattr(empregado_menu_obj, "empresa", None)
    empresa_menu_logo_url = ""
    if empresa_menu and getattr(empresa_menu, "logo", None):
        try:
            empresa_menu_logo_url = empresa_menu.logo.url
        except Exception:
            empresa_menu_logo_url = ""

    ajuda_contextual_atual = None
    if getattr(preferencias, "ajuda_contextual_ativa", True):
        resolver_match = getattr(request, "resolver_match", None)
        nome_rota_atual = getattr(resolver_match, "view_name", "")
        ajuda_contextual = obter_ajuda_contextual(nome_rota_atual)
        if ajuda_contextual:
            mostrar_ajuda = True
            if (
                getattr(preferencias, "ajuda_contextual_apenas_paginas_novas", False)
                and ajuda_contextual.get("contexto_tipo") != "novo"
            ):
                mostrar_ajuda = False

            if (
                mostrar_ajuda
                and getattr(preferencias, "ajuda_contextual_apenas_utilizadores_recentes", False)
            ):
                data_limite = timezone.now() - timedelta(days=AJUDA_CONTEXTUAL_JANELA_UTILIZADOR_RECENTE_DIAS)
                if not getattr(user, "date_joined", None) or user.date_joined < data_limite:
                    mostrar_ajuda = False

            if mostrar_ajuda:
                ajuda_contextual_atual = {
                    **ajuda_contextual,
                    "url": f"{reverse('projetos:ajuda')}#{ajuda_contextual['anchor']}",
                    "url_passos": f"{reverse('projetos:ajuda')}#{ajuda_contextual['anchor']}-passos",
                }

    return {
        "is_admin_user": is_admin_user,
        "is_empregado_user": is_empregado_user,
        "is_platform_admin": is_platform_admin,
        "is_platform_owner": is_platform_owner,
        "is_empresa_admin": is_empresa_admin,
        "perfil_plataforma": perfil,
        "empregado_menu_obj": empregado_menu_obj,
        "empregado_menu_funcao": (getattr(empregado_menu_obj, "funcao", "") or "").strip().lower(),
        "total_avarias_maquinas_abertas_menu": total_avarias_maquinas_abertas_menu,
        "total_minhas_avarias_maquinas_abertas_menu": total_minhas_avarias_maquinas_abertas_menu,
        "total_pedidos_ferias_pendentes_menu": total_pedidos_ferias_pendentes_menu,
        "total_notificacoes_empregado_abertas_menu": total_notificacoes_empregado_abertas_menu,
        "tamanho_texto": getattr(preferencias, "tamanho_texto", "normal"),
        "ajuda_contextual_ativa": getattr(preferencias, "ajuda_contextual_ativa", True),
        "ajuda_contextual_apenas_paginas_novas": getattr(preferencias, "ajuda_contextual_apenas_paginas_novas", False),
        "ajuda_contextual_apenas_utilizadores_recentes": getattr(preferencias, "ajuda_contextual_apenas_utilizadores_recentes", False),
        "empresa_menu_logo_url": empresa_menu_logo_url,
        "ajuda_contextual_atual": ajuda_contextual_atual,
        "sf_mvp_operacional_focus": getattr(settings, "SF_MVP_OPERACIONAL_FOCUS", True),
    }
