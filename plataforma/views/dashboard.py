from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from plataforma.decorators import platform_admin_required
from plataforma.models import Empresa, Plano, SubscricaoEmpresa

# TODO futuro:
# - substituir este padrão por selector/service dedicado para dashboard da plataforma
# - quando Empresa.plano passar para ForeignKey real, rever queries e métricas


@login_required
@platform_admin_required
def dashboard_plataforma(request):
    perfil = request.perfil_plataforma

    empresas_qs = Empresa.objects.select_related("plano").all().order_by("-criado_em")

    total_empresas = empresas_qs.count()
    empresas_ativas = empresas_qs.filter(status="ativa").count()
    empresas_teste = empresas_qs.filter(status="teste").count()
    empresas_suspensas = empresas_qs.filter(status="suspensa").count()
    empresas_canceladas = empresas_qs.filter(status="cancelada").count()
    hoje = timezone.now().date()
    alertas_renovacao = (
        SubscricaoEmpresa.objects
        .select_related("empresa", "plano")
        .filter(
            estado__in=["ativa", "pendente"],
            proxima_renovacao__isnull=False,
            proxima_renovacao__lte=hoje + timedelta(days=7),
        )
        .order_by("proxima_renovacao", "empresa__nome")[:8]
    )


    context = {
        "perfil": perfil,
        "total_empresas": total_empresas,
        "empresas_ativas": empresas_ativas,
        "empresas_teste": empresas_teste,
        "empresas_suspensas": empresas_suspensas,
        "empresas_canceladas": empresas_canceladas,
        "empresas": empresas_qs[:12],
        "planos_ativos": Plano.objects.filter(ativo=True).count(),
        "alertas_renovacao": alertas_renovacao,
    }

    return render(request, "plataforma/dashboard.html", context)
