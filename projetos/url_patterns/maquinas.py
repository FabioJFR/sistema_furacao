# =============================
# projetos/urls/maquinas.py
# =============================
from django.urls import path
from projetos import views


urlpatterns = [
    # ---------------- MÁQUINAS ----------------
    path("", views.maquina_list, name="maquina_list"),
    path("novo/", views.maquina_create, name="maquina_create"),
    path("<uuid:maquina_id>/", views.maquina_detail, name="maquina_detail"),
    path("<uuid:maquina_id>/editar/", views.maquina_update, name="maquina_update"),
    path("<uuid:maquina_id>/apagar/", views.maquina_delete, name="maquina_delete"),
]