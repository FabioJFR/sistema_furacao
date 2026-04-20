from django.urls import path
from dispositivos.api.views import (
    CriarSessaoDispositivoAPIView,
    LerDispositivoAPIView,
    BridgeLeituraAPIView,
)

urlpatterns = [
    path("sessoes/", CriarSessaoDispositivoAPIView.as_view(), name="api_dispositivos_criar_sessao"),
    path("sessoes/<uuid:pk>/ler/", LerDispositivoAPIView.as_view(), name="api_dispositivos_ler"),
    path("bridge/ler/", BridgeLeituraAPIView.as_view(), name="bridge_ler"),
]