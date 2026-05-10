from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse


def _client_ip(request):
    forwarded_for = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return (request.META.get("REMOTE_ADDR") or "unknown").strip() or "unknown"


class SensitivePostRateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        regra = self._obter_regra(request)
        cache_key = None

        if regra is not None:
            cache_key = self._cache_key(request, regra["scope"])
            tentativas = cache.get(cache_key, 0)
            if tentativas >= regra["limit"]:
                return HttpResponse(
                    regra["message"],
                    status=429,
                    content_type="text/plain; charset=utf-8",
                )
            if not cache.add(cache_key, 1, regra["window"]):
                try:
                    cache.incr(cache_key)
                except ValueError:
                    cache.set(cache_key, 1, regra["window"])

        response = self.get_response(request)

        if (
            regra is not None
            and cache_key is not None
            and regra.get("reset_on_redirect", False)
            and 300 <= response.status_code < 400
        ):
            cache.delete(cache_key)

        return response

    def _obter_regra(self, request):
        if request.method != "POST":
            return None

        path = request.path
        regras = (
            {
                "path": settings.LOGIN_URL,
                "limit": settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
                "window": settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
                "scope": "login",
                "message": "Demasiadas tentativas de login. Aguarda alguns minutos e tenta novamente.",
                "reset_on_redirect": True,
            },
            {
                "path": "/password-reset/",
                "limit": settings.PASSWORD_RESET_RATE_LIMIT_MAX_ATTEMPTS,
                "window": settings.PASSWORD_RESET_RATE_LIMIT_WINDOW_SECONDS,
                "scope": "password-reset",
                "message": "Demasiados pedidos de recuperação de password. Aguarda alguns minutos e tenta novamente.",
                "reset_on_redirect": False,
            },
            {
                "path": "/registo/",
                "limit": settings.REGISTO_RATE_LIMIT_MAX_ATTEMPTS,
                "window": settings.REGISTO_RATE_LIMIT_WINDOW_SECONDS,
                "scope": "registo",
                "message": "Demasiadas tentativas de registo. Aguarda algum tempo e tenta novamente.",
                "reset_on_redirect": False,
            },
        )
        for regra in regras:
            if path == regra["path"]:
                return regra
        return None

    def _cache_key(self, request, scope):
        return f"security-rate-limit:{scope}:{_client_ip(request)}"
