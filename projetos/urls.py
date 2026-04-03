from django.urls import path
from . import views

app_name = "projetos"

urlpatterns = [

    # 🔥 HOME
    #path('', views.home, name='home'),
    path('globo/', views.globo_projetos, name='globo_projetos'),
    path('', views.dashboard, name='dashboard'),

    # ---------------- PROJETOS ----------------
    # ---------------- PROJETOS ----------------
    path('projetos/', views.projeto_list, name='projeto_list'),
    path('projetos/novo/', views.projeto_create, name='projeto_create'),

    path('projetos/<uuid:pk>/', views.projeto_detail, name='projeto_detail'),
    path('projetos/<uuid:pk>/3d/', views.projeto_3d, name='projeto_3d'),
    path('projetos/<uuid:pk>/editar/', views.projeto_update, name='projeto_update'),
    path('projetos/<uuid:pk>/apagar/', views.projeto_delete, name='projeto_delete'),

    # ---------------- FUROS ----------------
    path('furos/', views.furo_list, name='furo_list'),
    path('furos/novo/', views.furo_create, name='furo_create'),
    path('furos/<uuid:pk>/', views.furo_detail, name='furo_detail'),
    path('furos/<uuid:pk>/editar/', views.furo_update, name='furo_update'),
    path('furos/<uuid:pk>/apagar/', views.furo_delete, name='furo_delete'),
    path('furos/<uuid:furo_id>/3d/', views.furo_3d_geologico, name='furo_3d'),

    # JSON (usado no dashboard)
    path('furo/<uuid:furo_id>/dados/', views.medicoes_json, name='medicoes_json'),

    # ---------------- MAQUINAS ----------------
    path('maquinas/', views.maquina_list, name='maquina_list'),
    path('maquinas/novo/', views.maquina_create, name='maquina_create'),
    path('maquinas/<uuid:maquina_id>/', views.maquina_detail, name='maquina_detail'),
    path('maquinas/<uuid:maquina_id>/editar/', views.maquina_update, name='maquina_update'),
    path('maquinas/<uuid:maquina_id>/delete/', views.maquina_delete, name='maquina_delete'),

    # ---------------- EMPREGADOS ----------------
    path('empregados/', views.empregado_list, name='empregado_list'),
    path('empregados/novo/', views.empregado_create, name='empregado_create'),
    path('empregados/<uuid:empregado_id>/', views.empregado_detail, name='empregado_detail'),
    
    #----------------- MATERIAL ----------------
    path('materiais/', views.material_list, name='material_list'),
    path('materiais/novo/', views.material_create, name='material_create'),

    #----------------- MEDICAO ------------------
    path('medicoes/list/', views.medicao_list, name='medicao_list'),
    path('medicoes/novo/', views.medicao_create, name='medicao_create'),
    path('medicoes/<int:pk>/editar/', views.medicao_update, name='medicao_update'),
    path('medicoes/<int:pk>/apagar/', views.medicao_delete, name='medicao_delete'),
]