# =============================
# projetos/urls/materiais.py
# =============================
from django.urls import path
from projetos import views


urlpatterns = [
    # ---------------- MATERIAIS ----------------
    path("", views.material_list, name="material_list"),
    path("novo/", views.material_create, name="material_create"),
    path("<uuid:material_id>/", views.material_detail, name="material_detail"),
    path("<uuid:material_id>/editar/", views.material_update, name="material_update"),
    path("<uuid:material_id>/apagar/", views.material_delete, name="material_delete"),
    path("<uuid:material_id>/entrada/", views.entrada_material_view, name="entrada_material"),
    path("<uuid:material_id>/saida/", views.saida_material_view, name="saida_material"),
]