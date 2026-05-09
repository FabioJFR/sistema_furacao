from django.urls import path

from projetos import views

urlpatterns = [
    path("", views.cliente_contrato_list, name="cliente_contrato_list"),
    path("painel-clientes/", views.cliente_contrato_painel_clientes, name="cliente_contrato_painel_clientes"),
    path("cliente/", views.cliente_comercial_detail, name="cliente_comercial_detail"),
    path("cliente/exportar-pdf/", views.cliente_comercial_exportar_pdf, name="cliente_comercial_exportar_pdf"),
    path("cliente/editar/", views.cliente_comercial_update, name="cliente_comercial_update"),
    path("novo/", views.cliente_contrato_create, name="cliente_contrato_create"),
    path("<uuid:pk>/", views.cliente_contrato_detail, name="cliente_contrato_detail"),
    path(
        "<uuid:pk>/aplicar-sugestao-workflow/",
        views.cliente_contrato_aplicar_sugestao_workflow,
        name="cliente_contrato_aplicar_sugestao_workflow",
    ),
    path("<uuid:pk>/editar/", views.cliente_contrato_update, name="cliente_contrato_update"),
    path("<uuid:pk>/apagar/", views.cliente_contrato_delete, name="cliente_contrato_delete"),
    path("<uuid:pk>/exportar-dossier/", views.cliente_contrato_exportar_dossier, name="cliente_contrato_exportar_dossier"),
    path("<uuid:pk>/anexos/novo/", views.cliente_contrato_anexo_create, name="cliente_contrato_anexo_create"),
    path(
        "<uuid:contrato_pk>/anexos/<uuid:pk>/apagar/",
        views.cliente_contrato_anexo_delete,
        name="cliente_contrato_anexo_delete",
    ),
    path("<uuid:pk>/adendas/nova/", views.cliente_contrato_adenda_create, name="cliente_contrato_adenda_create"),
    path(
        "<uuid:contrato_pk>/adendas/<uuid:pk>/editar/",
        views.cliente_contrato_adenda_update,
        name="cliente_contrato_adenda_update",
    ),
    path(
        "<uuid:contrato_pk>/adendas/<uuid:pk>/apagar/",
        views.cliente_contrato_adenda_delete,
        name="cliente_contrato_adenda_delete",
    ),
]
