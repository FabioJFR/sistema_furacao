# =============================
# projetos/urls/medicao.py
# =============================
from django.urls import path
from projetos import views


urlpatterns = [
    path("list/", views.medicao_list, name="medicao_list"),
    path("", views.medicao_list),
    path("<uuid:pk>/editar/", views.medicao_update, name="medicao_update"),
    path("<uuid:pk>/apagar/", views.medicao_delete, name="medicao_delete"),
]
