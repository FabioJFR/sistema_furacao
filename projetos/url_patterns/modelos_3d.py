from django.urls import path

from projetos import views


urlpatterns = [
    path("", views.modelos_3d_hub, name="modelos_3d_hub"),
    path("wireframe/", views.modelo_3d_wireframe, name="modelo_3d_wireframe"),
    path("wireframe/<uuid:pk>/conteudo/", views.modelo_3d_wireframe_conteudo, name="modelo_3d_wireframe_conteudo"),
    path("wireframe/<uuid:pk>/download/", views.modelo_3d_wireframe_download, name="modelo_3d_wireframe_download"),
    path("wireframe/<uuid:pk>/apagar/", views.modelo_3d_wireframe_apagar, name="modelo_3d_wireframe_apagar"),
    path("block-model/", views.modelo_3d_block_model, name="modelo_3d_block_model"),
    path("block-model/<uuid:pk>/conteudo/", views.modelo_3d_block_conteudo, name="modelo_3d_block_conteudo"),
    path("block-model/<uuid:pk>/config/", views.modelo_3d_block_config, name="modelo_3d_block_config"),
    path("block-model/<uuid:pk>/download/", views.modelo_3d_block_download, name="modelo_3d_block_download"),
    path("block-model/<uuid:pk>/apagar/", views.modelo_3d_block_apagar, name="modelo_3d_block_apagar"),
    path("implicit/", views.modelo_3d_implicit, name="modelo_3d_implicit"),
    path("implicit/<uuid:pk>/conteudo/", views.modelo_3d_implicit_conteudo, name="modelo_3d_implicit_conteudo"),
    path("implicit/<uuid:pk>/config/", views.modelo_3d_implicit_config, name="modelo_3d_implicit_config"),
    path("implicit/<uuid:pk>/download/", views.modelo_3d_implicit_download, name="modelo_3d_implicit_download"),
    path("implicit/<uuid:pk>/apagar/", views.modelo_3d_implicit_apagar, name="modelo_3d_implicit_apagar"),
]
