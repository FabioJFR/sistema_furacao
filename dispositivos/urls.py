# dispositivos/urls.py
from django.urls import path

from dispositivos import views

app_name = "dispositivos"

urlpatterns = [
    path("", views.dispositivos_dashboard, name="dashboard"),
    path("lista/", views.dispositivo_list, name="dispositivo_list"),

    path("sessoes/", views.sessao_dispositivo_list, name="sessao_list"),
    path("sessoes/<uuid:pk>/", views.sessao_dispositivo_detail, name="sessao_detail"),
    path("sessoes/<uuid:pk>/capturar-serial/", views.capturar_leitura_serial_view, name="capturar_leitura_serial"),

    path("leituras-brutas/", views.leitura_bruta_list, name="leitura_bruta_list"),
    path("leituras-brutas/<uuid:pk>/", views.leitura_bruta_detail, name="leitura_bruta_detail"),

    path("captura/", views.captura_dispositivo, name="captura"),

    path("shots/", views.survey_shot_list, name="survey_shot_list"),
    
    path("api/testar/", views.api_testar),
    path("api/capturar/", views.api_capturar),
    
]