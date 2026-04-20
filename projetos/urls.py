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
]