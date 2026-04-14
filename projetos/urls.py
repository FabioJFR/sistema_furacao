from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "projetos"

urlpatterns = [
    # ---------------- HOME / REDIRECT ----------------
    path("", views.redirect_after_login, name="home"),
    path("redirect-after-login/", views.redirect_after_login, name="redirect_after_login"),
    path('login/', auth_views.LoginView.as_view( template_name='login.html', redirect_authenticated_user=True,
        next_page='projetos:redirect_after_login'),name='login'),
    # ---------------- DASHBOARD ----------------
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/graficos/", views.graficos_dashboard, name="graficos_dashboard"),
    path("graficos/", views.graficos_dashboard, name="graficos_dashboard"),
    path("globo/", views.globo_projetos, name="globo_projetos"),

    # ---------------- REGISTO INICIAL / GERAL ----------------
    path("registos/criar/", views.criar_registo_view, name="criar_registo"),
    path("registo/", views.registo_empregado, name="registo_empregado"),

    # ---------------- PROJETOS ----------------
    path("projetos/", views.projeto_list, name="projeto_list"),
    path("projetos/novo/", views.projeto_create, name="projeto_create"),
    path("projetos/<uuid:pk>/", views.projeto_detail, name="projeto_detail"),
    path("projetos/<uuid:pk>/3d/", views.projeto_3d, name="projeto_3d"),
    path("projetos/<uuid:pk>/editar/", views.projeto_update, name="projeto_update"),
    path("projetos/<uuid:pk>/apagar/", views.projeto_delete, name="projeto_delete"),

    # ---------------- FUROS ----------------
    path("furos/", views.furo_list, name="furo_list"),
    path("furos/novo/", views.furo_create, name="furo_create"),
    path("furos/<uuid:pk>/", views.furo_detail, name="furo_detail"),
    path("furos/<uuid:pk>/editar/", views.furo_update, name="furo_update"),
    path("furos/<uuid:pk>/apagar/", views.furo_delete, name="furo_delete"),
    path("furos/<uuid:furo_id>/3d/", views.furo_3d_geologico, name="furo_3d"),
    path("furos/<uuid:furo_id>/medicoes/nova/", views.medicao_create, name="medicao_create"),

    # ---------------- TRABALHADORES NO FURO ----------------
    path(
        "furos/<uuid:furo_id>/adicionar-trabalhador/",
        views.furo_adicionar_empregado,
        name="furo_adicionar_empregado",
    ),
    path(
        "furos/trabalhadores/<int:pk>/editar/",
        views.furo_editar_empregado,
        name="furo_editar_empregado",
    ),
    path(
        "furos/trabalhadores/<int:pk>/remover/",
        views.furo_remover_empregado,
        name="furo_remover_empregado",
    ),

    # ---------------- HISTÓRICO CONFIGURAÇÃO POR FURO ----------------
    path(
        "furos/<uuid:furo_id>/configuracoes-perfuracao/historico/",
        views.historico_configuracao_list_furo_admin,
        name="historico_configuracao_list_furo_admin",
    ),

    # ---------------- MEDIÇÕES ----------------
    path("medicoes/list/", views.medicao_list, name="medicao_list"),
    path("medicoes/<int:pk>/editar/", views.medicao_update, name="medicao_update"),
    path("medicoes/<int:pk>/apagar/", views.medicao_delete, name="medicao_delete"),

    # ---------------- MÁQUINAS ----------------
    path("maquinas/", views.maquina_list, name="maquina_list"),
    path("maquinas/novo/", views.maquina_create, name="maquina_create"),
    path("maquinas/<uuid:maquina_id>/", views.maquina_detail, name="maquina_detail"),
    path("maquinas/<uuid:maquina_id>/editar/", views.maquina_update, name="maquina_update"),
    path("maquinas/<uuid:maquina_id>/delete/", views.maquina_delete, name="maquina_delete"),

    # ---------------- MATERIAIS ----------------
    path("materiais/", views.material_list, name="material_list"),
    path("materiais/novo/", views.material_create, name="material_create"),
    path("materiais/<uuid:material_id>/", views.material_detail, name="material_detail"),
    path("materiais/<uuid:material_id>/editar/", views.material_update, name="material_update"),
    path("materiais/<uuid:material_id>/apagar/", views.material_delete, name="material_delete"),
    path("materiais/<uuid:material_id>/entrada/", views.entrada_material_view, name="entrada_material"),
    path("materiais/<uuid:material_id>/saida/", views.saida_material_view, name="saida_material"),

    # ---------------- EMPREGADOS ----------------
    path("empregados/pendentes/", views.empregado_pendentes, name="empregado_pendentes"),
    path("empregados/<uuid:pk>/aprovar/", views.empregado_aprovar, name="empregado_aprovar"),
    path("empregados/", views.empregado_list, name="empregado_list"),
    path("empregados/novo/", views.empregado_create, name="empregado_create"),
    path("empregados/<uuid:pk>/", views.empregado_detail, name="empregado_detail"),
    path("empregados/<uuid:pk>/editar/", views.empregado_update, name="empregado_update"),
    path("empregados/<uuid:pk>/apagar/", views.empregado_delete, name="empregado_delete"),
    path("empregados/<uuid:pk>/adicionar-projeto/", views.empregado_adicionar_projeto, name="empregado_adicionar_projeto"),
    path("empregados/<uuid:pk>/projetos/<int:ligacao_id>/editar/", views.empregado_editar_projeto, name="empregado_editar_projeto"),
    path("empregados/<uuid:pk>/projetos/<int:ligacao_id>/terminar/", views.empregado_terminar_projeto, name="empregado_terminar_projeto"),
    path("empregados/<uuid:pk>/adicionar-ficheiro/", views.empregado_adicionar_ficheiro, name="empregado_adicionar_ficheiro"),
    path("empregados/<uuid:pk>/ficheiros/<int:ficheiro_id>/apagar/", views.empregado_apagar_ficheiro, name="empregado_apagar_ficheiro"),

    # ---------------- CONFIGURAÇÕES PERFURAÇÃO ADMIN ----------------
    path(
        "empregados/<uuid:pk>/configuracoes-perfuracao/",
        views.configuracao_perfuracao_list_admin,
        name="configuracao_perfuracao_list_admin",
    ),
    path(
        "empregados/<uuid:pk>/configuracoes-perfuracao/nova/",
        views.configuracao_perfuracao_create_admin,
        name="configuracao_perfuracao_create_admin",
    ),
    path(
        "empregados/<uuid:pk>/configuracoes-perfuracao/historico/",
        views.historico_configuracao_list_admin,
        name="historico_configuracao_list_admin",
    ),

    path(
        "configuracoes-perfuracao/<int:pk>/",
        views.configuracao_perfuracao_detail_admin,
        name="configuracao_perfuracao_detail_admin",
    ),
    path(
        "configuracoes-perfuracao/<int:pk>/editar/",
        views.configuracao_perfuracao_update_admin,
        name="configuracao_perfuracao_update_admin",
    ),
    path(
        "configuracoes-perfuracao/<int:pk>/apagar/",
        views.configuracao_perfuracao_delete_admin,
        name="configuracao_perfuracao_delete_admin",
    ),

    # ---------------- ÁREA DO EMPREGADO ----------------
    path("minha-area/", views.area_empregado, name="area_empregado"),
    path("minha-area/diario-tecnico/", views.diario_tecnico, name="diario_tecnico"),
    path("minha-area/meus-dados/", views.meus_dados_empregado, name="meus_dados_empregado"),
    path("minha-area/meus-dados/editar/", views.meus_dados_empregado_editar, name="meus_dados_empregado_editar"),
    path("minha-area/furos/<uuid:pk>/", views.furo_detail_empregado, name="furo_detail_empregado"),

    # ---------------- CONFIGURAÇÕES PERFURAÇÃO EMPREGADO ----------------
    path(
        "minha-area/configuracoes-perfuracao/",
        views.configuracao_perfuracao_list_empregado,
        name="configuracao_perfuracao_list_empregado",
    ),
    path(
        "minha-area/configuracoes-perfuracao/nova/",
        views.configuracao_perfuracao_create_empregado,
        name="configuracao_perfuracao_create_empregado",
    ),
    path(
        "minha-area/configuracoes-perfuracao/<int:pk>/",
        views.configuracao_perfuracao_detail_empregado,
        name="configuracao_perfuracao_detail_empregado",
    ),
    path(
        "minha-area/configuracoes-perfuracao/<int:pk>/editar/",
        views.configuracao_perfuracao_update_empregado,
        name="configuracao_perfuracao_update_empregado",
    ),
    path(
        "minha-area/configuracoes-perfuracao/<int:pk>/apagar/",
        views.configuracao_perfuracao_delete_empregado,
        name="configuracao_perfuracao_delete_empregado",
    ),
    path(
        "minha-area/configuracoes-perfuracao/historico/",
        views.historico_configuracao_list_empregado,
        name="historico_configuracao_list_empregado",
    ),

    # ---------------- HISTÓRICO CONFIGURAÇÃO ----------------
    path(
        "historico-configuracao/<int:pk>/",
        views.historico_configuracao_detail,
        name="historico_configuracao_detail",
    ),
    path(
        "historico-configuracao/<int:pk>/comparar/",
        views.historico_configuracao_comparar,
        name="historico_configuracao_comparar",
    ),
    path(
        "historico-configuracao/<int:pk>/restaurar/",
        views.historico_configuracao_restaurar,
        name="historico_configuracao_restaurar",
    ),

    # ---------------- REGISTOS DIÁRIOS EMPREGADO ----------------
    path("meus-registos/", views.registo_diario_list, name="registo_diario_list"),
    path("meus-registos/novo/", views.registo_diario_create, name="registo_diario_create"),
    path("meus-registos/<uuid:pk>/editar/", views.registo_diario_update, name="registo_diario_update"),

    # ---------------- REGISTOS DIÁRIOS ADMIN ----------------
    path("registos/novo/", views.registo_diario_create, name="registo_diario_create"),
    path("registos/admin/", views.registos_admin_list, name="registos_admin_list"),
    path("registos/admin/<uuid:pk>/editar/", views.registo_admin_update, name="registo_admin_update"),

    # ---------------- LEVANTAMENTOS ----------------
    path("meus-levantamentos/", views.levantamento_material_list, name="levantamento_material_list"),
    path("meus-levantamentos/novo/", views.levantamento_material_create, name="levantamento_material_create"),
    path("levantamentos/admin/", views.levantamento_material_admin_list, name="levantamento_material_admin_list"),

    # ---------------- DEVOLUÇÕES ----------------
    path("minhas-devolucoes/", views.devolucao_material_list, name="devolucao_material_list"),
    path("minhas-devolucoes/nova/", views.devolucao_material_create, name="devolucao_material_create"),
    path("devolucoes/admin/", views.devolucao_material_admin_list, name="devolucao_material_admin_list"),
]