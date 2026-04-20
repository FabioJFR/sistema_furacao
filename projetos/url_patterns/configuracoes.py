# =============================
# projetos/urls/configuracoes.py
# =============================
from django.urls import path
from projetos import views



urlpatterns = [
    path("admin/", views.configuracao_perfuracao_list_admin, name="configuracao_list"),

    # ---------------- CONFIGURAÇÕES PERFURAÇÃO EMPREGADO ----------------
    path("configuracoes-perfuracao/", views.configuracao_perfuracao_list_empregado, name="configuracao_perfuracao_list_empregado"),
    path("configuracoes-perfuracao/nova/", views.configuracao_perfuracao_create_empregado, name="configuracao_perfuracao_create_empregado"),
    path("configuracoes-perfuracao/<int:pk>/", views.configuracao_perfuracao_detail_empregado, name="configuracao_perfuracao_detail_empregado"),
    path("configuracoes-perfuracao/<int:pk>/editar/", views.configuracao_perfuracao_update_empregado, name="configuracao_perfuracao_update_empregado"),
    path("configuracoes-perfuracao/<int:pk>/apagar/", views.configuracao_perfuracao_delete_empregado, name="configuracao_perfuracao_delete_empregado"),
    path("configuracoes-perfuracao/historico/", views.historico_configuracao_list_empregado, name="historico_configuracao_list_empregado"),

    # ---------------- CONFIGURAÇÕES PERFURAÇÃO ADMIN ----------------
    path("empregados/<uuid:pk>/configuracoes-perfuracao/", views.configuracao_perfuracao_list_admin, name="configuracao_perfuracao_list_admin"),
    path("empregados/<uuid:pk>/configuracoes-perfuracao/nova/", views.configuracao_perfuracao_create_admin, name="configuracao_perfuracao_create_admin"),
    path("empregados/<uuid:pk>/configuracoes-perfuracao/historico/", views.historico_configuracao_list_admin, name="historico_configuracao_list_admin"),

    path("configuracoes-perfuracao/<int:pk>/", views.configuracao_perfuracao_detail_admin, name="configuracao_perfuracao_detail_admin"),
    path("configuracoes-perfuracao/<int:pk>/editar/", views.configuracao_perfuracao_update_admin, name="configuracao_perfuracao_update_admin"),
    path("configuracoes-perfuracao/<int:pk>/apagar/", views.configuracao_perfuracao_delete_admin, name="configuracao_perfuracao_delete_admin"),

    # ---------------- HISTÓRICO CONFIGURAÇÃO ----------------
    path("historico-configuracao/<int:pk>/", views.historico_configuracao_detail, name="historico_configuracao_detail"),
    path("historico-configuracao/<int:pk>/comparar/", views.historico_configuracao_comparar, name="historico_configuracao_comparar"),
    path("historico-configuracao/<int:pk>/restaurar/", views.historico_configuracao_restaurar, name="historico_configuracao_restaurar"),
]