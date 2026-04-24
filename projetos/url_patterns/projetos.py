# =============================
# projetos/urls/projetos.py
# =============================
from django.urls import path
from projetos import views



urlpatterns = [
    path("", views.projeto_list, name="projeto_list"),
    path("novo/", views.projeto_create, name="projeto_create"),
    path("<uuid:pk>/", views.projeto_detail_legacy, name="projeto_detail_legacy"),
    path("<uuid:pk>/<slug:slug>/", views.projeto_detail, name="projeto_detail"),
    path("<uuid:pk>/empregados/adicionar/", views.projeto_adicionar_empregado, name="projeto_adicionar_empregado"),
    path("<uuid:pk>/empregados/<int:ligacao_id>/remover/", views.projeto_remover_empregado, name="projeto_remover_empregado"),
    path("<uuid:pk>/3d/", views.projeto_3d, name="projeto_3d"),
    path("<uuid:pk>/editar/", views.projeto_update, name="projeto_update"),
    path("<uuid:pk>/apagar/", views.projeto_delete, name="projeto_delete"),
]
