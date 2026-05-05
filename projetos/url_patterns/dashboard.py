# =============================
# projetos/urls/dashboard.py
# =============================
from django.urls import path
from projetos import views



urlpatterns = [
    path("", views.redirect_after_login, name="home"),
    path("redirect-after-login/", views.redirect_after_login, name="redirect_after_login"),

    # ---------------- DASHBOARD ----------------
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/graficos/", views.graficos_dashboard, name="graficos_dashboard"),
    path("dashboard/graficos/operacionais/", views.graficos_operacionais_dashboard, name="graficos_operacionais_dashboard"),
    path("dashboard/graficos/financeiros/", views.graficos_financeiros_dashboard, name="graficos_financeiros_dashboard"),
    path("dashboard/graficos/rentabilidade/", views.graficos_rentabilidade_dashboard, name="graficos_rentabilidade_dashboard"),
    path("dashboard/graficos/produtividade/", views.graficos_produtividade_dashboard, name="graficos_produtividade_dashboard"),
    path("dashboard/graficos/alertas/", views.graficos_alertas_dashboard, name="graficos_alertas_dashboard"),
    path("globo/", views.globo_projetos, name="globo_projetos"),
]
