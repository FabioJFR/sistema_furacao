from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db.models import OuterRef, Subquery
from django.utils import timezone

from plataforma.models import Empresa, FuroArquivadoPlataforma, PerfilPlataforma, Plano, SubscricaoEmpresa

User = get_user_model()


def obter_empresas_dashboard_qs():
    subscricao_atual_qs = (
        SubscricaoEmpresa.objects
        .filter(empresa=OuterRef("pk"))
        .order_by("-data_inicio", "-criado_em")
    )
    return (
        Empresa.objects
        .select_related("plano")
        .annotate(
            subscricao_atual_estado=Subquery(subscricao_atual_qs.values("estado")[:1]),
        )
        .order_by("-criado_em")
    )


def obter_alertas_renovacao_qs():
    hoje = timezone.now().date()
    return (
        SubscricaoEmpresa.objects
        .select_related("empresa", "plano")
        .filter(
            estado__in=["ativa", "pendente"],
            proxima_renovacao__isnull=False,
            proxima_renovacao__lte=hoje + timedelta(days=7),
        )
        .order_by("proxima_renovacao", "empresa__nome")[:8]
    )


def resolver_estado_comercial_empresa(*, status_empresa, estado_subscricao):
    status_empresa = (status_empresa or "").strip()
    estado_subscricao = (estado_subscricao or "").strip()

    if status_empresa in {"suspensa", "cancelada"}:
        return status_empresa

    if estado_subscricao == "ativa":
        return "ativa"
    if estado_subscricao == "pendente":
        return "teste"
    if estado_subscricao in {"expirada", "suspensa"}:
        return "suspensa"
    if estado_subscricao == "cancelada":
        return "cancelada"

    return status_empresa or "teste"


def enriquecer_empresas_dashboard(empresas):
    labels_empresa = dict(Empresa.STATUS_CHOICES)
    labels_subscricao = dict(SubscricaoEmpresa.ESTADO_CHOICES)

    for empresa in empresas:
        estado_comercial = resolver_estado_comercial_empresa(
            status_empresa=empresa.status,
            estado_subscricao=getattr(empresa, "subscricao_atual_estado", ""),
        )
        empresa.estado_comercial = estado_comercial
        empresa.estado_comercial_label = labels_empresa.get(estado_comercial, estado_comercial.title())

        estado_subscricao = getattr(empresa, "subscricao_atual_estado", "")
        empresa.subscricao_atual_estado_label = (
            labels_subscricao.get(estado_subscricao, estado_subscricao.title())
            if estado_subscricao
            else ""
        )

    return empresas


def obter_metricas_empresas_dashboard(empresas_qs):
    furos_arquivados_qs = FuroArquivadoPlataforma.objects.values("furo_id_origem").distinct()
    contagens = {
        "ativa": 0,
        "teste": 0,
        "suspensa": 0,
        "cancelada": 0,
    }
    for status_empresa, estado_subscricao in empresas_qs.values_list("status", "subscricao_atual_estado"):
        estado_comercial = resolver_estado_comercial_empresa(
            status_empresa=status_empresa,
            estado_subscricao=estado_subscricao,
        )
        contagens[estado_comercial] = contagens.get(estado_comercial, 0) + 1

    return {
        "total_empresas": empresas_qs.count(),
        "empresas_ativas": contagens["ativa"],
        "empresas_teste": contagens["teste"],
        "empresas_suspensas": contagens["suspensa"],
        "empresas_canceladas": contagens["cancelada"],
        "planos_ativos": Plano.objects.filter(ativo=True).count(),
        "total_furos_arquivados_plataforma": furos_arquivados_qs.count(),
    }


def _obter_user_ids_online():
    user_ids = set()
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        user_id = session.get_decoded().get("_auth_user_id")
        if user_id:
            user_ids.add(int(user_id))
    return user_ids


def obter_metricas_contas_dashboard():
    perfis_qs = PerfilPlataforma.objects.exclude(
        tipo_acesso__in=["platform_owner", "platform_admin"]
    )
    return {
        "contas_ativadas": perfis_qs.filter(user__is_active=True).count(),
        "contas_por_ativar": perfis_qs.filter(user__is_active=False).count(),
        "utilizadores_online_total": len(_obter_user_ids_online()),
    }


def listar_utilizadores_online(limit=8):
    user_ids = _obter_user_ids_online()
    if not user_ids:
        return []

    return list(
        User.objects
        .filter(pk__in=user_ids)
        .select_related("perfil_plataforma", "perfil_plataforma__empresa")
        .order_by("username")[:limit]
    )


def listar_ultimos_logins(limit=10):
    return list(
        User.objects
        .filter(last_login__isnull=False)
        .select_related("perfil_plataforma", "perfil_plataforma__empresa")
        .order_by("-last_login")[:limit]
    )
