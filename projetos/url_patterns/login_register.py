# =============================
# projetos/urls/login_register.py (DEPRECATED)
# =============================
from django.urls import path
from django.shortcuts import redirect

app_name = "login_register"

urlpatterns = [
    # Temporary redirects to website app (auth moved out of projetos)
    path("", lambda request: redirect("/")),
    path("redirect-after-login/", lambda request: redirect("/")),

    path("registos/criar/", lambda request: redirect("/registo/")),
    path("registo/", lambda request: redirect("/registo/")),
]