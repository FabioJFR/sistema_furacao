# =============================
# projetos/urls/empregado_area.py
# =============================
from django.urls import path
from projetos import views



urlpatterns = [
    path("", views.area_empregado, name="area_empregado"),

    # ---------------- DADOS PESSOAIS ----------------
    path("meus-dados/", views.meus_dados_empregado, name="meus_dados_empregado"),
    path("meus-dados/editar/", views.meus_dados_empregado_editar, name="meus_dados_empregado_editar"),

    # ---------------- FUNCIONALIDADES ----------------
    path("definicoes/", views.definicoes, name="definicoes"),
    path("diario-tecnico/", views.diario_tecnico, name="diario_tecnico"),
    path("medicoes/", views.medicao_list_empregado, name="medicao_list_empregado"),
    path("medicoes/<uuid:pk>/", views.medicao_detail_empregado, name="medicao_detail_empregado"),

    # ---------------- FUROS ----------------
    path("meus-furos/", views.meus_furos_empregado, name="meus_furos_empregado"),
    path("furos/<uuid:pk>/", views.furo_detail_empregado, name="furo_detail_empregado"),
    path("furos/<uuid:pk>/3d/", views.furo_3d_empregado, name="furo_3d_empregado"),

    # ---------------- PROJETOS ----------------
    path("meus-projetos/", views.meus_projetos_empregado, name="meus_projetos_empregado"),
    path("projetos/<uuid:pk>/", views.projeto_detail_empregado, name="projeto_detail_empregado"),

    # ---------------- MATERIAIS ----------------
    path("materiais-disponiveis/", views.materiais_disponiveis_empregado, name="materiais_disponiveis_empregado"),
    path("materiais/novo/", views.material_create_empregado, name="material_create_empregado"),
    path("maquinas/avarias/nova/", views.avaria_maquina_create_empregado, name="avaria_maquina_create_empregado"),
    path("maquinas/avarias/", views.avaria_maquina_minhas_empregado, name="avaria_maquina_minhas_empregado"),
    path("maquinas/avarias/<uuid:pk>/editar/", views.avaria_maquina_update_empregado, name="avaria_maquina_update_empregado"),
]
