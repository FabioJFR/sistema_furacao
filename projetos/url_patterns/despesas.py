from django.urls import path

from projetos import views


urlpatterns = [
    path("minhas/", views.despesa_list_admin, name="despesa_list_admin"),
    path("adicionar/", views.despesa_create_admin, name="despesa_create_admin"),
    path("<uuid:despesa_id>/", views.despesa_detail_admin, name="despesa_detail_admin"),
    path("<uuid:despesa_id>/editar/", views.despesa_update_admin, name="despesa_update_admin"),
    path("<uuid:despesa_id>/apagar/", views.despesa_delete_admin, name="despesa_delete_admin"),
    path("minha-area/minhas/", views.despesa_list_empregado, name="despesa_list_empregado"),
    path("minha-area/adicionar/", views.despesa_create_empregado, name="despesa_create_empregado"),
]
