from django.contrib import admin
from django.urls import path, include, reverse_lazy
from django.views.i18n import set_language
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from website import views as website_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("set-language/", set_language, name="set_language"),

    # AUTH
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="website/login.html",
            redirect_authenticated_user=False,
            next_page="/app/redirect-after-login/",
        ),
        name="login",
    ),
    path(
        "logout/",
        website_views.logout_user,
        name="logout",
    ),

    # RESET PASSWORD
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
            success_url=reverse_lazy("password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url=reverse_lazy("password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    # WEBSITE / APP
    path("", include("website.urls")),
    path("app/", include("projetos.urls")),
    path("app/dispositivos/", include("dispositivos.urls")),
    path("plataforma/", include("plataforma.urls")),

    # API Dispositivos
    path("api/dispositivos/", include("dispositivos.api.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)