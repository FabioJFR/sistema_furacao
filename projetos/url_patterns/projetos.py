# =============================
# projetos/urls/projetos.py
# =============================
from django.urls import path
from projetos import views



urlpatterns = [
    path("", views.projeto_list, name="projeto_list"),
    path("novo/", views.projeto_create, name="projeto_create"),
    path("<uuid:pk>/", views.projeto_detail, name="projeto_detail"),
    path("<uuid:pk>/3d/", views.projeto_3d, name="projeto_3d"),
    path("<uuid:pk>/editar/", views.projeto_update, name="projeto_update"),
    path("<uuid:pk>/apagar/", views.projeto_delete, name="projeto_delete"),
]