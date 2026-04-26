from django.urls import path
from . import views

app_name = "website"

urlpatterns = [
    path("", views.home, name="home"),
    path("planos/", views.planos, name="planos"),
    path("registo/", views.registo, name="registo"),
    path("confirmar-conta/<uidb64>/<token>/", views.confirmar_conta, name="confirmar_conta"),
    path("reenviar-confirmacao/", views.reenviar_confirmacao, name="reenviar_confirmacao"),
]
