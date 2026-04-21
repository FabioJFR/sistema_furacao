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
    path("api/portas-usb/", views.api_procurar_portas_usb, name="api_procurar_portas_usb"),
    path("api/bluetooth/", views.api_procurar_dispositivos_bluetooth, name="api_procurar_dispositivos_bluetooth"),
    path("api/bluetooth/inspecionar/", views.api_inspecionar_dispositivo_bluetooth, name="api_inspecionar_dispositivo_bluetooth"),
    path("api/dispositivos/guardar/", views.api_guardar_dispositivo_detectado, name="api_guardar_dispositivo_detectado"),
    path("api/dispositivos/escutar/", views.api_escutar_dispositivo_detectado, name="api_escutar_dispositivo_detectado"),
    path("api/testar-leitura-usb/", views.api_testar_leitura_usb, name="api_testar_leitura_usb"),
    
]
