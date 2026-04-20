from django.utils import translation

from projetos.models import PreferenciasUser


class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            preferencias, _ = PreferenciasUser.objects.get_or_create(
                user=request.user,
                defaults={
                    "idioma": "pt-pt",
                    "tema": "claro",
                },
            )

            if preferencias.idioma:
                translation.activate(preferencias.idioma)
                request.LANGUAGE_CODE = preferencias.idioma
                request.session["django_language"] = preferencias.idioma

        response = self.get_response(request)
        translation.deactivate()
        return response