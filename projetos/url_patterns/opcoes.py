from django.urls import path

from projetos import views


urlpatterns = [
    path("procurar/", views.procurar_dashboard, name="procurar_dashboard"),
    path("relatorios/", views.relatorios_exportacao, name="relatorios_exportacao"),
    path(
        "relatorios/tudo/<str:formato>/",
        views.relatorios_download_tudo,
        name="relatorios_download_tudo",
    ),
    path(
        "relatorios/<str:dataset>/<str:formato>/",
        views.relatorios_download,
        name="relatorios_download",
    ),
    path("definicoes/", views.definicoes_admin, name="definicoes_admin"),
    path(
        "definicoes-financeiras/",
        views.definicoes_financeiras_admin,
        name="definicoes_financeiras_admin",
    ),
]
