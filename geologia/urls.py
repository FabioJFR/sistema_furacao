from django.urls import path

from geologia import views


app_name = "geologia"

urlpatterns = [
    path("", views.geologia_hub, name="hub"),
    path("drone/", views.drone_hub, name="drone_hub"),
    path("furos/<uuid:furo_id>/", views.furo_geologia_dashboard, name="furo_dashboard"),
    path("furos/<uuid:furo_id>/logs/novo/", views.log_geologico_create, name="log_create"),
    path("logs/<uuid:pk>/", views.log_geologico_detail, name="log_detail"),
    path("logs/<uuid:pk>/editar/", views.log_geologico_update, name="log_update"),
    path("furos/<uuid:furo_id>/drone/nova/", views.missao_drone_create, name="missao_create"),
    path("drone/<uuid:pk>/", views.missao_drone_detail, name="missao_detail"),
    path("drone/<uuid:pk>/editar/", views.missao_drone_update, name="missao_update"),
    path("logs/<uuid:pk>/anexos/novo/", views.anexo_log_create, name="anexo_create"),
]
