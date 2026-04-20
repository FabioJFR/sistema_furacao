# =============================
# projetos/urls/levantamentos.py
# =============================
from django.urls import path
from projetos import views



urlpatterns = [
    # ---------------- LEVANTAMENTOS ----------------
    path("meus/", views.levantamento_material_list, name="levantamento_list"),
    path("meus/novo/", views.levantamento_material_create, name="levantamento_create"),
    path("admin/", views.levantamento_material_admin_list, name="levantamento_material_admin_list"),
]