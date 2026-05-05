from django.urls import path

from projetos import views


urlpatterns = [
    path("", views.modelos_3d_hub, name="modelos_3d_hub"),
    path("block-model/profissional/", views.block_model_list, name="block_model_list"),
    path("block-model/profissional/novo/", views.block_model_create, name="block_model_create"),
    path("block-model/profissional/<uuid:pk>/", views.block_model_detail, name="block_model_detail"),
    path("block-model/profissional/<uuid:pk>/3d/", views.block_model_3d, name="block_model_3d"),
    path("block-model/profissional/<uuid:pk>/export-json/", views.block_model_export_json, name="block_model_export_json"),
    path("block-model/profissional/<uuid:pk>/export-csv/", views.block_model_export_csv, name="block_model_export_csv"),
    path("block-model/profissional/<uuid:pk>/regenerar-celulas/", views.block_model_regenerate_cells, name="block_model_regenerate_cells"),
    path("block-model/profissional/<uuid:pk>/apagar/", views.block_model_delete, name="block_model_delete"),
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
