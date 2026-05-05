# =============================
# projetos/urls/empregados.py
# =============================
from django.urls import path, re_path
from projetos import views



urlpatterns = [
    path("", views.empregado_list, name="empregado_list"),
    path("novo/", views.empregado_create, name="empregado_create"),
    # ---------------- ESTADOS / AÇÕES ----------------
    path("pendentes/", views.empregado_pendentes, name="empregado_pendentes"),
    path("<uuid:pk>/aprovar/", views.empregado_aprovar, name="empregado_aprovar"),
    path("<uuid:pk>/rejeitar/", views.empregado_rejeitar, name="empregado_rejeitar"),
    path("<uuid:pk>/ligar-utilizador/", views.empregado_ligar_utilizador, name="empregado_ligar_utilizador"),
    path("<uuid:pk>/editar/", views.empregado_update, name="empregado_update"),
    path("<uuid:pk>/apagar/", views.empregado_delete, name="empregado_delete"),

    # ---------------- PROJETOS DO EMPREGADO ----------------
    path("<uuid:pk>/projetos/adicionar/", views.empregado_adicionar_projeto, name="empregado_adicionar_projeto"),
    path("<uuid:pk>/projetos/<int:ligacao_id>/editar/", views.empregado_editar_projeto, name="empregado_editar_projeto"),
    path("<uuid:pk>/projetos/<int:ligacao_id>/terminar/", views.empregado_terminar_projeto, name="empregado_terminar_projeto"),

    # ---------------- FICHEIROS ----------------
    path("<uuid:pk>/ficheiros/adicionar/", views.empregado_adicionar_ficheiro, name="empregado_adicionar_ficheiro"),
    path("<uuid:pk>/ficheiros/<int:ficheiro_id>/apagar/", views.empregado_apagar_ficheiro, name="empregado_apagar_ficheiro"),
    path("<uuid:pk>/", views.empregado_detail_legacy, name="empregado_detail_legacy"),
    re_path(
        r"^(?P<pk>[0-9a-f-]{36})/(?P<slug>(?!aprovar$|rejeitar$|editar$|apagar$|projetos$|ficheiros$|pendentes$)[-a-zA-Z0-9_]+)/$",
        views.empregado_detail,
        name="empregado_detail",
    ),
]
