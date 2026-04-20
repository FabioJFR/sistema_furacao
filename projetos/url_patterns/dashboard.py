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
    path("globo/", views.globo_projetos, name="globo_projetos"),
]