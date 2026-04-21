from django.urls import path

from projetos import views


urlpatterns = [
    path("eventos/", views.analytics_eventos, name="analytics_eventos"),
]
