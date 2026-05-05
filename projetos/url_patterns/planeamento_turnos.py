from django.urls import path

from projetos import views

urlpatterns = [
    path("", views.planeamento_turno_list, name="planeamento_turno_list"),
    path("novo/", views.planeamento_turno_create, name="planeamento_turno_create"),
    path("<uuid:pk>/editar/", views.planeamento_turno_update, name="planeamento_turno_update"),
    path("<uuid:pk>/apagar/", views.planeamento_turno_delete, name="planeamento_turno_delete"),
    path(
        "conflitos/<uuid:a_pk>/<uuid:b_pk>/",
        views.planeamento_turno_resolver_conflito,
        name="planeamento_turno_resolver_conflito",
    ),
]
