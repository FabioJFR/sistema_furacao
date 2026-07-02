from dataclasses import dataclass

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test import Client


@dataclass
class SmokeRoute:
    nome: str
    path: str
    allowed_statuses: tuple[int, ...] = (200,)


PUBLIC_ROUTES = [
    SmokeRoute("homepage", "/"),
    SmokeRoute("planos", "/planos/"),
    SmokeRoute("registo", "/registo/"),
    SmokeRoute("termos", "/termos-condicoes/"),
    SmokeRoute("privacidade", "/politica-privacidade/"),
    SmokeRoute("login", "/login/"),
    SmokeRoute("robots", "/robots.txt"),
]

AUTH_ROUTES = [
    SmokeRoute("redirect-pos-login", "/app/redirect-after-login/", (200, 302)),
    SmokeRoute("dashboard-operacional", "/app/dashboard/", (200, 302)),
]


class Command(BaseCommand):
    help = "Executa smoke tests HTTP internos para validar rotas críticas antes/depois de release."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            "--host",
            default="",
            help="Host HTTP usado pelo Django test client. Por defeito usa o primeiro ALLOWED_HOSTS ou testserver.",
        )
        parser.add_argument("--username", default="", help="Utilizador para smoke autenticado opcional.")
        parser.add_argument("--password", default="", help="Password para smoke autenticado opcional.")
        parser.add_argument(
            "--public-only",
            action="store_true",
            help="Executa apenas rotas públicas, mesmo que sejam fornecidas credenciais.",
        )

    def handle(self, *args, **options):
        host = options["host"] or self._default_host()
        client = Client(HTTP_HOST=host)

        resultados = []
        resultados.extend(self._check_routes(client=client, routes=PUBLIC_ROUTES))

        username = options["username"]
        password = options["password"]
        if not options["public_only"] and (username or password):
            if not (username and password):
                raise CommandError("Define --username e --password para smoke autenticado.")
            if not client.login(username=username, password=password):
                resultados.append(("auth-login", False, "Login falhou com as credenciais fornecidas."))
            else:
                resultados.append(("auth-login", True, "Login autenticado com sucesso."))
                resultados.extend(self._check_routes(client=client, routes=AUTH_ROUTES))

        falhas = [resultado for resultado in resultados if not resultado[1]]

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Release smoke check"))
        for nome, ok, mensagem in resultados:
            style = self.style.SUCCESS if ok else self.style.ERROR
            marker = "OK" if ok else "ERRO"
            self.stdout.write(style(f"[{marker}] {nome}: {mensagem}"))

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Resumo smoke: {len(resultados) - len(falhas)} OK, {len(falhas)} erro(s)."
            )
        )

        if falhas:
            raise CommandError("Smoke check falhou. Corrige as rotas antes de avançar.")

    def _default_host(self):
        hosts = [host for host in getattr(settings, "ALLOWED_HOSTS", []) if host and host != "*"]
        return hosts[0] if hosts else "testserver"

    def _check_routes(self, *, client, routes):
        resultados = []
        for route in routes:
            try:
                response = client.get(route.path)
            except Exception as exc:
                resultados.append((route.nome, False, f"Exceção em {route.path}: {exc}"))
                continue

            ok = response.status_code in route.allowed_statuses
            esperado = "/".join(str(status) for status in route.allowed_statuses)
            mensagem = (
                f"{route.path} respondeu {response.status_code}."
                if ok
                else f"{route.path} respondeu {response.status_code}; esperado {esperado}."
            )
            resultados.append((route.nome, ok, mensagem))
        return resultados
