from django.urls import path

from dispositivos import views

app_name = "dispositivos"

urlpatterns = [
    path("", views.dispositivos_dashboard, name="dashboard"),
    path("lista/", views.dispositivo_list, name="dispositivo_list"),
    path("sessoes/", views.sessao_dispositivo_list, name="sessao_list"),
    path("leituras-brutas/", views.leitura_bruta_list, name="leitura_bruta_list"),
    path("shots/", views.survey_shot_list, name="survey_shot_list"),
]