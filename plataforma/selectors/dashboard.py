from datetime import timedelta

from django.utils import timezone

from plataforma.models import Empresa, FuroArquivadoPlataforma, Plano, SubscricaoEmpresa


def obter_empresas_dashboard_qs():
    return Empresa.objects.select_related("plano").all().order_by("-criado_em")


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


def obter_metricas_empresas_dashboard(empresas_qs):
    furos_arquivados_qs = FuroArquivadoPlataforma.objects.values("furo_id_origem").distinct()
    return {
        "total_empresas": empresas_qs.count(),
        "empresas_ativas": empresas_qs.filter(status="ativa").count(),
        "empresas_teste": empresas_qs.filter(status="teste").count(),
        "empresas_suspensas": empresas_qs.filter(status="suspensa").count(),
        "empresas_canceladas": empresas_qs.filter(status="cancelada").count(),
        "planos_ativos": Plano.objects.filter(ativo=True).count(),
        "total_furos_arquivados_plataforma": furos_arquivados_qs.count(),
    }
