from django.urls import path

from projetos import views

urlpatterns = [
    path("", views.assiduidade_list, name="assiduidade_list"),
    path("export/csv/", views.assiduidade_export_csv, name="assiduidade_export_csv"),
    path("export/excel/", views.assiduidade_export_excel, name="assiduidade_export_excel"),
    path("export/xlsx/", views.assiduidade_export_xlsx, name="assiduidade_export_xlsx"),
    path("novo/", views.assiduidade_create, name="assiduidade_create"),
    path("<uuid:pk>/editar/", views.assiduidade_update, name="assiduidade_update"),
    path("<uuid:pk>/apagar/", views.assiduidade_delete, name="assiduidade_delete"),
    path("<uuid:pk>/aprovar/", views.assiduidade_aprovar, name="assiduidade_aprovar"),
    path("<uuid:pk>/rejeitar/", views.assiduidade_rejeitar, name="assiduidade_rejeitar"),
]
