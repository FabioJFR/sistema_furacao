# =============================
# projetos/urls/maquinas.py
# =============================
from django.urls import path
from projetos import views


urlpatterns = [
    # ---------------- MÁQUINAS ----------------
    path("", views.maquina_list, name="maquina_list"),
    path("novo/", views.maquina_create, name="maquina_create"),
    path("avarias/nova/", views.avaria_maquina_create_admin, name="avaria_maquina_create_admin"),
    path("avarias/", views.avaria_maquina_list_admin, name="avaria_maquina_list_admin"),
    path("avarias/<uuid:pk>/editar/", views.avaria_maquina_update_admin, name="avaria_maquina_update_admin"),
    path("<uuid:maquina_id>/", views.maquina_detail, name="maquina_detail"),
    path("<uuid:maquina_id>/editar/", views.maquina_update, name="maquina_update"),
    path("<uuid:maquina_id>/apagar/", views.maquina_delete, name="maquina_delete"),
]
