from django.urls import path
from . import views

app_name = "website"

urlpatterns = [
    path("", views.home, name="home"),
    path("sobre/", views.sobre, name="sobre"),
    path("contactos/", views.contactos, name="contactos"),
    path("feedback/", views.feedback, name="feedback"),
    path("termos-condicoes/", views.termos_condicoes, name="termos_condicoes"),
    path("politica-privacidade/", views.politica_privacidade, name="politica_privacidade"),
    path("planos/", views.planos, name="planos"),
    path("registo/", views.registo, name="registo"),
    path("confirmar-conta/<uidb64>/<token>/", views.confirmar_conta, name="confirmar_conta"),
    path("reenviar-confirmacao/", views.reenviar_confirmacao, name="reenviar_confirmacao"),
]
