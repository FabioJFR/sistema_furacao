from collections import defaultdict
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


def _percentual(parte, total):
    if not total:
        return 0
    return round((parte / total) * 100)


def obter_metricas_comerciais_dashboard(empresas_qs):
    empresas = list(
        empresas_qs.values(
            "id",
            "nome",
            "plano_id",
            "plano__nome",
            "status",
            "subscricao_atual_estado",
        )
    )
    perfis_admin = list(
        PerfilPlataforma.objects
        .filter(tipo_acesso="empresa_admin", empresa_id__isnull=False)
        .values("empresa_id", "user__is_active")
    )

    ativacao_por_empresa = defaultdict(lambda: {"ativadas": 0, "total": 0})
    for perfil in perfis_admin:
        bucket = ativacao_por_empresa[perfil["empresa_id"]]
        bucket["total"] += 1
        if perfil["user__is_active"]:
            bucket["ativadas"] += 1

    linhas_planos = {}
    totais = {
        "empresas": 0,
        "ativas": 0,
        "retidas": 0,
        "admins_total": 0,
        "admins_ativados": 0,
    }

    for empresa in empresas:
        plano_id = empresa["plano_id"] or "sem-plano"
        estado_comercial = resolver_estado_comercial_empresa(
            status_empresa=empresa["status"],
            estado_subscricao=empresa["subscricao_atual_estado"],
        )
        linha = linhas_planos.setdefault(
            plano_id,
            {
                "plano_nome": empresa["plano__nome"] or "Sem plano",
                "empresas_total": 0,
                "empresas_ativas": 0,
                "empresas_em_teste": 0,
                "empresas_retidas": 0,
                "admins_total": 0,
                "admins_ativados": 0,
            },
        )
        linha["empresas_total"] += 1
        totais["empresas"] += 1

        if estado_comercial == "ativa":
            linha["empresas_ativas"] += 1
            totais["ativas"] += 1
        if estado_comercial == "teste":
            linha["empresas_em_teste"] += 1
        if estado_comercial != "cancelada":
            linha["empresas_retidas"] += 1
            totais["retidas"] += 1

        ativacao = ativacao_por_empresa.get(empresa["id"], {"ativadas": 0, "total": 0})
        linha["admins_total"] += ativacao["total"]
        linha["admins_ativados"] += ativacao["ativadas"]
        totais["admins_total"] += ativacao["total"]
        totais["admins_ativados"] += ativacao["ativadas"]

    planos = []
    for linha in linhas_planos.values():
        linha["taxa_conversao"] = _percentual(linha["empresas_ativas"], linha["empresas_total"])
        linha["taxa_retencao"] = _percentual(linha["empresas_retidas"], linha["empresas_total"])
        linha["taxa_ativacao"] = _percentual(linha["admins_ativados"], linha["admins_total"])
        planos.append(linha)

    planos.sort(key=lambda item: (-item["empresas_total"], item["plano_nome"].lower()))

    return {
        "metricas_comerciais": {
            "taxa_ativacao_contas": _percentual(totais["admins_ativados"], totais["admins_total"]),
            "taxa_conversao_operacional": _percentual(totais["ativas"], totais["empresas"]),
            "taxa_retencao_base": _percentual(totais["retidas"], totais["empresas"]),
            "total_admins_cliente": totais["admins_total"],
            "total_planos_comerciais": len(planos),
        },
        "planos_comerciais": planos,
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
