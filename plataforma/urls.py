from django.urls import path, include
from plataforma.views.dashboard import dashboard_plataforma
from plataforma.views.onboarding import onboarding_empresa
from plataforma.views.empresas import empresa_detail_plataforma, alterar_plano_empresa, toggle_empresa_ativa
from plataforma.views.planos import plano_list, plano_create, plano_update, plano_toggle_ativo
from plataforma.views.subscricoes import subscricao_list
from django.conf import settings
from django.conf.urls.static import static

app_name = "plataforma"

urlpatterns = [
    path("onboarding/empresa/", onboarding_empresa, name="onboarding_empresa"),
    path("dashboard/", dashboard_plataforma, name="dashboard"),
    path("empresa/<uuid:pk>/", empresa_detail_plataforma, name="empresa_detail"),
    # PLANOS (gestão de planos da plataforma)
    path("planos/", plano_list, name="plano_list"),
    path("planos/novo/", plano_create, name="plano_create"),
    path("planos/<uuid:pk>/editar/", plano_update, name="plano_update"),
    path("planos/<uuid:pk>/toggle/", plano_toggle_ativo, name="plano_toggle_ativo"),
    path("empresa/<uuid:pk>/alterar-plano/", alterar_plano_empresa, name="empresa_alterar_plano"),
    path("empresa/<uuid:pk>/toggle-ativa/", toggle_empresa_ativa, name="empresa_toggle_ativa"),
    path("subscricoes/", subscricao_list, name="subscricao_list"),
    path("dispositivos/", include("dispositivos.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)