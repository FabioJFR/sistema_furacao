from django.urls import path

from projetos.api.views import (
    FuroDetailAPIView,
    FuroListAPIView,
    FuroUltimaVersaoAPIView,
    FuroVersaoListAPIView,
)


urlpatterns = [
    path("furos/", FuroListAPIView.as_view(), name="api_v1_furos_list"),
    path("furos/<uuid:pk>/", FuroDetailAPIView.as_view(), name="api_v1_furos_detail"),
    path("furos/<uuid:pk>/versoes/", FuroVersaoListAPIView.as_view(), name="api_v1_furos_versoes"),
    path("furos/<uuid:pk>/versoes/ultima/", FuroUltimaVersaoAPIView.as_view(), name="api_v1_furos_versao_ultima"),
]

