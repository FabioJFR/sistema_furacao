
# =============================
# projetos/urls/devolucoes.py
# =============================
from django.urls import path
from projetos import views



urlpatterns = [
    path("admin/", views.devolucao_material_admin_list, name="devolucao_material_admin_list"),
    path("criar/", views.devolucao_material_create, name="devolucao_material_create"),
    path("minhas/", views.devolucao_material_list, name="devolucao_material_list"),
]