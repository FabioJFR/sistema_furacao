from django.urls import path, include
from plataforma.views.dashboard import dashboard_plataforma
from plataforma.views.onboarding import onboarding_empresa
from plataforma.views.empresas import (
    empresa_detail_plataforma,
    alterar_plano_empresa,
    toggle_empresa_ativa,
    atualizar_renovacao_subscricao_empresa,
    atualizar_logo_empresa,
    remover_logo_empresa,
)
from plataforma.views.planos import plano_list, plano_create, plano_update, plano_toggle_ativo
from plataforma.views.subscricoes import subscricao_list
from plataforma.views.financas import (
    financas_analytics,
    financas_paypal_cancelado,
    financas_entrada_list,
    financas_paypal_config,
    financas_paypal_checkout_pagamento,
    financas_paypal_retorno,
    financas_saida_list,
)
from plataforma.views.features import features_dashboard
from plataforma.views.uteis import (
    uteis_arquivo_furos,
    uteis_arquivo_furo_detail,
    uteis_dashboard,
    uteis_export_ai_json,
    uteis_clear_scope,
)
from plataforma.views.todo import todo_dashboard, todo_area_detail

app_name = "plataforma"

urlpatterns = [
    path("", dashboard_plataforma, name="home"),
    path("onboarding/empresa/", onboarding_empresa, name="onboarding_empresa"),
    path("dashboard/", dashboard_plataforma, name="dashboard"),
    path("empresa/<uuid:pk>/", empresa_detail_plataforma, name="empresa_detail"),
    # PLANOS (gestão de planos da plataforma)
    path("planos/", plano_list, name="plano_list"),
    path("planos/novo/", plano_create, name="plano_create"),
    path("planos/<uuid:pk>/editar/", plano_update, name="plano_update"),
    path("planos/<uuid:pk>/toggle/", plano_toggle_ativo, name="plano_toggle_ativo"),
    path("empresa/<uuid:pk>/alterar-plano/", alterar_plano_empresa, name="empresa_alterar_plano"),
    path("empresa/<uuid:pk>/atualizar-renovacao/", atualizar_renovacao_subscricao_empresa, name="empresa_atualizar_renovacao"),
    path("empresa/<uuid:pk>/toggle-ativa/", toggle_empresa_ativa, name="empresa_toggle_ativa"),
    path("empresa/<uuid:pk>/logo/atualizar/", atualizar_logo_empresa, name="empresa_logo_atualizar"),
    path("empresa/<uuid:pk>/logo/remover/", remover_logo_empresa, name="empresa_logo_remover"),
    path("subscricoes/", subscricao_list, name="subscricao_list"),
    path("financas/entradas/", financas_entrada_list, name="financas_entrada_list"),
    path("financas/saidas/", financas_saida_list, name="financas_saida_list"),
    path("financas/saidas/<uuid:pk>/editar/", financas_saida_list, name="financas_saida_update"),
    path("financas/analytics/", financas_analytics, name="financas_analytics"),
    path("financas/paypal/config/", financas_paypal_config, name="financas_paypal_config"),
    path(
        "financas/paypal/pagamento/<uuid:pk>/checkout/",
        financas_paypal_checkout_pagamento,
        name="financas_paypal_checkout_pagamento",
    ),
    path("financas/paypal/retorno/", financas_paypal_retorno, name="financas_paypal_retorno"),
    path("financas/paypal/cancelado/", financas_paypal_cancelado, name="financas_paypal_cancelado"),
    path("features/", features_dashboard, name="features_dashboard"),
    path("todo/", todo_dashboard, name="todo_dashboard"),
    path("todo/<slug:area_slug>/", todo_area_detail, name="todo_area_detail"),
    path("uteis/", uteis_dashboard, name="uteis_dashboard"),
    path("uteis/arquivo-furos/", uteis_arquivo_furos, name="uteis_arquivo_furos"),
    path("uteis/arquivo-furos/<uuid:pk>/", uteis_arquivo_furo_detail, name="uteis_arquivo_furo_detail"),
    path("uteis/export-ai/<slug:scope>/", uteis_export_ai_json, name="uteis_export_ai_json"),
    path("uteis/clear/<slug:scope>/", uteis_clear_scope, name="uteis_clear_scope"),
    path("dispositivos/", include("dispositivos.urls")),
]
