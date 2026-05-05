from django.urls import path

from projetos import views

urlpatterns = [
    path("ajuda/", views.ajuda, name="ajuda"),
    path("sobre/", views.sobre, name="sobre"),
    path("termos-condicoes/", views.termos_condicoes, name="termos_condicoes"),
    path("politica-privacidade/", views.politica_privacidade, name="politica_privacidade"),
]
