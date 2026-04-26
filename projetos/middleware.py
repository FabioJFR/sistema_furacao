from django.utils import translation

from projetos.request_context import clear_current_user, set_current_user
from projetos.selectors.preferencias import obter_ou_criar_preferencias_user


class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            preferencias, _ = obter_ou_criar_preferencias_user(
                user=request.user,
                defaults={
                    "idioma": "pt-pt",
                    "tema": "claro",
                    "tamanho_texto": "normal",
                },
            )
            request.sf_preferencias = preferencias

            if preferencias.idioma:
                translation.activate(preferencias.idioma)
                request.LANGUAGE_CODE = preferencias.idioma
                request.session["django_language"] = preferencias.idioma

        response = self.get_response(request)
        translation.deactivate()
        return response


class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_user(request.user if getattr(request, "user", None) and request.user.is_authenticated else None)
        try:
            return self.get_response(request)
        finally:
            clear_current_user()
