from django.urls import path

from projetos import views

urlpatterns = [
    path("", views.cliente_contrato_list, name="cliente_contrato_list"),
    path("novo/", views.cliente_contrato_create, name="cliente_contrato_create"),
    path("<uuid:pk>/", views.cliente_contrato_detail, name="cliente_contrato_detail"),
    path("<uuid:pk>/editar/", views.cliente_contrato_update, name="cliente_contrato_update"),
    path("<uuid:pk>/apagar/", views.cliente_contrato_delete, name="cliente_contrato_delete"),
]
