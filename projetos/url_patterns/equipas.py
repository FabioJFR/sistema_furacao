from django.urls import path

from projetos import views


urlpatterns = [
    path("", views.equipa_list, name="equipa_list"),
    path("nova/", views.equipa_create, name="equipa_create"),
    path("<uuid:pk>/editar/", views.equipa_update, name="equipa_update"),
    path("<uuid:pk>/apagar/", views.equipa_delete, name="equipa_delete"),
]
