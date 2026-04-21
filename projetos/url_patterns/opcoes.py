from django.urls import path

from projetos import views


urlpatterns = [
    path("procurar/", views.procurar_dashboard, name="procurar_dashboard"),
    path("definicoes/", views.definicoes_admin, name="definicoes_admin"),
]
