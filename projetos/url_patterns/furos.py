# =============================
# projetos/urls/furos.py
# =============================
from django.urls import path, re_path
from projetos import views



urlpatterns = [
    # ---------------- FUROS ----------------
    path("", views.furo_list, name="furo_list"),
    path("novo/", views.furo_create, name="furo_create"),
    path("<uuid:pk>/terminar/", views.furo_terminar, name="furo_terminar"),
    path("<uuid:pk>/reativar/", views.furo_reativar, name="furo_reativar"),
    path("<uuid:pk>/editar/", views.furo_update, name="furo_update"),
    path("<uuid:pk>/apagar/", views.furo_delete, name="furo_delete"),
    path("<uuid:furo_id>/3d/", views.furo_3d_geologico, name="furo_3d"),
    path("<uuid:furo_id>/3d/export/<str:formato>/", views.furo_3d_export, name="furo_3d_export"),
    path("3d/importar/", views.furo_3d_importar_externo, name="furo_3d_importar_externo"),
    path("<uuid:pk>/", views.furo_detail_legacy, name="furo_detail_legacy"),
    re_path(
        r"^(?P<pk>[0-9a-f-]{36})/(?P<slug>(?!editar$|apagar$|3d$|terminar$|reativar$)[-a-zA-Z0-9_]+)/$",
        views.furo_detail,
        name="furo_detail",
    ),
    path("<uuid:pk>/<slug:slug>/3d/", views.furo_3d_geologico, name="furo_3d_detail"),

    # ---------------- MEDIÇÕES DO FURO ----------------
    path("<uuid:furo_id>/medicoes/nova/", views.medicao_create, name="medicao_create"),

    # ---------------- TRABALHADORES NO FURO ----------------
    path("<uuid:furo_id>/trabalhadores/adicionar/", views.furo_adicionar_empregado, name="furo_adicionar_empregado"),
    path("trabalhadores/<int:pk>/editar/", views.furo_editar_empregado, name="furo_editar_empregado"),
    path("trabalhadores/<int:pk>/remover/", views.furo_remover_empregado, name="furo_remover_empregado"),
]
