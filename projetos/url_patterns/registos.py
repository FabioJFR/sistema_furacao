# projetos/urls/registos.py
from django.urls import path
from projetos import views


urlpatterns = [
    # ---------------- REGISTOS DIÁRIOS EMPREGADO ----------------
    path("meus/", views.registo_diario_list, name="registo_diario_list"),
    path("meus/novo/", views.registo_diario_create, name="registo_diario_create"),
    path("meus/<uuid:pk>/editar/", views.registo_diario_update, name="registo_diario_update"),

    # ---------------- REGISTOS DIÁRIOS ADMIN ----------------
    path("admin/", views.registos_admin_list, name="registos_admin_list"),
    path("admin/novo/", views.registo_diario_create, name="registo_admin_create"),
    path("admin/<uuid:pk>/editar/", views.registo_admin_update, name="registo_admin_update"),
]