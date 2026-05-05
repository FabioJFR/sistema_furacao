from django.urls import path, include

app_name = "projetos"

urlpatterns = [
    path("", include("projetos.url_patterns.dashboard")),
    path("projetos/", include("projetos.url_patterns.projetos")),
    path("furos/", include("projetos.url_patterns.furos")),
    path("empregados/", include("projetos.url_patterns.empregados")),
    path("materiais/", include("projetos.url_patterns.materiais")),
    path("maquinas/", include("projetos.url_patterns.maquinas")),
    path("registos/", include("projetos.url_patterns.registos")),
    path("configuracoes/", include("projetos.url_patterns.configuracoes")),
    path("minha-area/", include("projetos.url_patterns.empregado_area")),
    path("devolucoes/", include("projetos.url_patterns.devolucoes")),
    path("levantamentos/", include("projetos.url_patterns.levantamentos")),
    path("historico-configuracao/", include("projetos.url_patterns.historico_configuracao")),
    path("login-register/", include("projetos.url_patterns.login_register")),
    path("medicoes/", include("projetos.url_patterns.medicao")),
    path("despesas/", include("projetos.url_patterns.despesas")),
    path("analytics/", include("projetos.url_patterns.analytics")),
    path("opcoes/", include("projetos.url_patterns.opcoes")),
    path("3d/", include("projetos.url_patterns.modelos_3d")),
    path("gestao/clientes-contratos/", include("projetos.url_patterns.clientes_contratos")),
    path("gestao/planeamento/", include("projetos.url_patterns.planeamento_turnos")),
    path("gestao/rh-assiduidade/", include("projetos.url_patterns.assiduidade")),
    path("gestao/", include("projetos.url_patterns.gestao_empresa")),
    path("", include("projetos.url_patterns.institucional")),
]
