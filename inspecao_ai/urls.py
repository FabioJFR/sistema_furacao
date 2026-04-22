from django.urls import path

from . import views


app_name = "inspecao_ai"

urlpatterns = [
    path("", views.hub, name="hub"),
    path("chatbox/", views.chatbox, name="chatbox"),
    path("analises/", views.analise_list, name="analise_list"),
    path("analises/nova/", views.analise_create, name="analise_create"),
    path("analises/<uuid:pk>/", views.analise_detail, name="analise_detail"),
    path("analises/<uuid:pk>/reprocessar/", views.analise_reprocessar, name="analise_reprocessar"),
]
