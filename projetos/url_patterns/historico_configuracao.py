# =============================
# projetos/url_patterns/historico_configuracao.py
# =============================
from django.urls import path
from projetos import views



urlpatterns = [
    path(
        "empregado/",
        views.historico_configuracao_list_empregado,
        name="historico_empregado_list",
    ),
    path(
        "empregado/<uuid:pk>/",
        views.historico_configuracao_list_admin,
        name="historico_empregado_admin_list",
    ),
    path(
        "<uuid:furo_id>/",
        views.historico_configuracao_list_furo_admin,
        name="historico_furo_list",
    ),
    path(
        "detalhe/<int:pk>/",
        views.historico_configuracao_detail,
        name="historico_detail",
    ),
    path(
        "comparar/<int:pk>/",
        views.historico_configuracao_comparar,
        name="historico_comparar",
    ),
    path(
        "restaurar/<int:pk>/",
        views.historico_configuracao_restaurar,
        name="historico_restaurar",
    ),
]