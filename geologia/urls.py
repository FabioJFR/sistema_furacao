from django.urls import path

from geologia import views


app_name = "geologia"

urlpatterns = [
    path("", views.geologia_hub, name="hub"),
    path("drone/", views.drone_hub, name="drone_hub"),
    path("drone-sf/", views.drone_sf_hub, name="drone_sf_hub"),
    path("drone-sf/novo/", views.drone_sf_create, name="drone_sf_create"),
    path("drone-sf/demo/", views.drone_sf_demo_create, name="drone_sf_demo_create"),
    path("drone-sf/<uuid:pk>/", views.drone_sf_detail, name="drone_sf_detail"),
    path("drone-sf/<uuid:drone_id>/operacao/", views.drone_sf_operacao_detail, name="drone_sf_operacao_detail"),
    path("drone-sf/<uuid:drone_id>/comandos/novo/", views.drone_sf_comando_create, name="drone_sf_comando_create"),
    path("drone-sf/<uuid:drone_id>/missoes/<uuid:missao_id>/alternar/", views.drone_sf_missao_programada_toggle, name="drone_sf_missao_programada_toggle"),
    path("drone-sf/<uuid:drone_id>/missoes/<uuid:missao_id>/executar/", views.drone_sf_missao_programada_executar, name="drone_sf_missao_programada_executar"),
    path("drone-sf/<uuid:drone_id>/missoes/<uuid:missao_id>/apagar/", views.drone_sf_missao_programada_delete, name="drone_sf_missao_programada_delete"),
    path("drone-sf/<uuid:drone_id>/modulos/novo/", views.drone_sf_modulo_create, name="drone_sf_modulo_create"),
    path("drone-sf/<uuid:drone_id>/sensores/novo/", views.drone_sf_sensor_create, name="drone_sf_sensor_create"),
    path("drone-sf/api/bridge/ingest/", views.api_drone_sf_bridge_ingest_estado, name="api_drone_sf_bridge_ingest_estado"),
    path("drone-sf/api/bridge/log/", views.api_drone_sf_bridge_log_event, name="api_drone_sf_bridge_log_event"),
    path("drone-sf/api/bridge/comandos/", views.api_drone_sf_bridge_comandos_pendentes, name="api_drone_sf_bridge_comandos_pendentes"),
    path("drone-sf/api/bridge/comandos/<uuid:comando_id>/confirmar/", views.api_drone_sf_bridge_confirmar_comando, name="api_drone_sf_bridge_confirmar_comando"),
    path("drone-sf/<uuid:drone_id>/api/estado/", views.api_drone_sf_estado, name="api_drone_sf_estado"),
    path("drone/controlo/atualizar/", views.drone_controle_update, name="drone_controle_update"),
    path("drone/comandos/novo/", views.drone_comando_create, name="drone_comando_create"),
    path("drone/api/testar-ligacao/", views.api_testar_ligacao_drone, name="api_testar_ligacao_drone"),
    path("drone/api/procurar/", views.api_procurar_drone, name="api_procurar_drone"),
    path("drone/api/estado/", views.api_estado_drone, name="api_estado_drone"),
    path("drone/api/bridge/ingest/", views.api_bridge_ingest_estado, name="api_bridge_ingest_estado"),
    path("drone/api/bridge/log/", views.api_bridge_log_event, name="api_bridge_log_event"),
    path("drone/api/bridge/comandos/", views.api_bridge_comandos_pendentes, name="api_bridge_comandos_pendentes"),
    path("drone/api/bridge/comandos/<uuid:comando_id>/confirmar/", views.api_bridge_confirmar_comando, name="api_bridge_confirmar_comando"),
    path("furos/<uuid:furo_id>/", views.furo_geologia_dashboard, name="furo_dashboard"),
    path("furos/<uuid:furo_id>/logs/novo/", views.log_geologico_create, name="log_create"),
    path("logs/<uuid:pk>/", views.log_geologico_detail, name="log_detail"),
    path("logs/<uuid:pk>/editar/", views.log_geologico_update, name="log_update"),
    path("furos/<uuid:furo_id>/drone/nova/", views.missao_drone_create, name="missao_create"),
    path("drone/<uuid:pk>/", views.missao_drone_detail, name="missao_detail"),
    path("drone/<uuid:pk>/editar/", views.missao_drone_update, name="missao_update"),
    path("logs/<uuid:pk>/anexos/novo/", views.anexo_log_create, name="anexo_create"),
]
