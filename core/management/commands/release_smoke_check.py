from dataclasses import dataclass

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test import Client


@dataclass
class SmokeRoute:
    nome: str
    path: str
    allowed_statuses: tuple[int, ...] = (200,)
    expected_content_type: str = ""


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

AUTH_OK = (200, 302)

PROFILE_ROUTES = {
    "superuser": [
        SmokeRoute("superuser-plataforma", "/plataforma/dashboard/", AUTH_OK),
        SmokeRoute("superuser-todo", "/plataforma/todo/", AUTH_OK),
        SmokeRoute("superuser-riscos-deploy", "/plataforma/riscos-deploy/", AUTH_OK),
    ],
    "empresa": [
        SmokeRoute("empresa-dashboard", "/app/dashboard/", AUTH_OK),
        SmokeRoute("empresa-projetos", "/app/projetos/", AUTH_OK),
        SmokeRoute("empresa-furos", "/app/furos/", AUTH_OK),
        SmokeRoute("empresa-registos", "/app/registos/admin/", AUTH_OK),
        SmokeRoute("empresa-materiais", "/app/materiais/", AUTH_OK),
        SmokeRoute("empresa-gestao", "/app/gestao/", AUTH_OK),
    ],
    "empregado": [
        SmokeRoute("empregado-minha-area", "/app/minha-area/", AUTH_OK),
        SmokeRoute("empregado-meus-furos", "/app/minha-area/meus-furos/", AUTH_OK),
        SmokeRoute("empregado-registos", "/app/registos/meus/", AUTH_OK),
        SmokeRoute("empregado-materiais", "/app/minha-area/materiais-disponiveis/", AUTH_OK),
        SmokeRoute("empregado-medicoes", "/app/minha-area/medicoes/", AUTH_OK),
    ],
    "individual": [
        SmokeRoute("individual-minha-area", "/app/minha-area/", AUTH_OK),
        SmokeRoute("individual-projetos", "/app/projetos/", AUTH_OK),
        SmokeRoute("individual-furos", "/app/furos/", AUTH_OK),
        SmokeRoute("individual-registos", "/app/registos/meus/", AUTH_OK),
    ],
}


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
            "--profile",
            choices=["base", "superuser", "empresa", "empregado", "individual", "all"],
            default="base",
            help=(
                "Jornada autenticada a validar. Usa 'base' para rotas comuns ou um perfil "
                "específico com credenciais reais desse tipo de conta."
            ),
        )
        parser.add_argument(
            "--public-only",
            action="store_true",
            help="Executa apenas rotas públicas, mesmo que sejam fornecidas credenciais.",
        )
        parser.add_argument("--project-id", default="", help="ID real de projeto para smoke de detalhe opcional.")
        parser.add_argument("--furo-id", default="", help="ID real de furo para smoke de detalhe opcional.")
        parser.add_argument("--registo-id", default="", help="ID real de registo diário para smoke de detalhe opcional.")
        parser.add_argument("--material-id", default="", help="ID real de material para smoke de detalhe opcional.")
        parser.add_argument("--medicao-id", default="", help="ID real de medição para smoke de detalhe opcional.")
        parser.add_argument(
            "--include-report-pdf",
            action="store_true",
            help="Quando usado com --registo-id, valida também o PDF do relatório técnico desse registo.",
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
                resultados.extend(
                    self._check_routes(
                        client=client,
                        routes=self._auth_routes_for_profile(options["profile"], options=options),
                    )
                )

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
        self._write_checklist(options=options, host=host, resultados=resultados, falhas=falhas)

        if falhas:
            raise CommandError("Smoke check falhou. Corrige as rotas antes de avançar.")

    def _default_host(self):
        hosts = [host for host in getattr(settings, "ALLOWED_HOSTS", []) if host and host != "*"]
        return hosts[0] if hosts else "testserver"

    def _write_checklist(self, *, options, host, resultados, falhas):
        modo = "public-only" if options.get("public_only") else "autenticado"
        rotas_ok = [nome for nome, ok, _mensagem in resultados if ok]
        rotas_falha = [nome for nome, ok, _mensagem in resultados if not ok]

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Checklist copiável"))
        self.stdout.write(f"- Comando: {self._build_safe_command(options=options, host=host)}")
        self.stdout.write(f"- Host: {host}")
        self.stdout.write(f"- Modo: {modo}")
        self.stdout.write(f"- Perfil: {options.get('profile') or 'base'}")
        self.stdout.write(f"- Resultado: {len(rotas_ok)} OK, {len(falhas)} erro(s)")
        self.stdout.write(f"- Rotas OK: {', '.join(rotas_ok) if rotas_ok else '-'}")
        self.stdout.write(f"- Rotas com erro: {', '.join(rotas_falha) if rotas_falha else '-'}")
        if options.get("include_report_pdf"):
            self.stdout.write("- PDF técnico: validado")

    def _build_safe_command(self, *, options, host):
        command = ["python manage.py release_smoke_check", "--host", host]
        if options.get("public_only"):
            command.append("--public-only")
        else:
            command.extend(["--profile", options.get("profile") or "base"])
            if options.get("username"):
                command.extend(["--username", options["username"], "--password", "<password>"])

        for option_name, flag in (
            ("project_id", "--project-id"),
            ("furo_id", "--furo-id"),
            ("registo_id", "--registo-id"),
            ("material_id", "--material-id"),
            ("medicao_id", "--medicao-id"),
        ):
            if options.get(option_name):
                command.extend([flag, options[option_name]])

        if options.get("include_report_pdf"):
            command.append("--include-report-pdf")

        return " ".join(command)

    def _auth_routes_for_profile(self, profile, *, options=None):
        if profile == "base":
            routes = list(AUTH_ROUTES)
            routes.extend(self._detail_routes(options=options or {}, profile=profile))
            return routes
        if profile == "all":
            routes = list(AUTH_ROUTES)
            for profile_routes in PROFILE_ROUTES.values():
                routes.extend(profile_routes)
            routes.extend(self._detail_routes(options=options or {}, profile=profile))
            return routes
        routes = AUTH_ROUTES + PROFILE_ROUTES[profile]
        routes.extend(self._detail_routes(options=options or {}, profile=profile))
        return routes

    def _detail_routes(self, *, options, profile):
        routes = []
        employee_scope = profile in {"empregado", "individual"}

        if options.get("project_id"):
            path = (
                f"/app/minha-area/projetos/{options['project_id']}/"
                if employee_scope
                else f"/app/projetos/{options['project_id']}/"
            )
            routes.append(SmokeRoute("detail-projeto", path, AUTH_OK))

        if options.get("furo_id"):
            path = (
                f"/app/minha-area/furos/{options['furo_id']}/"
                if employee_scope
                else f"/app/furos/{options['furo_id']}/"
            )
            routes.append(SmokeRoute("detail-furo", path, AUTH_OK))

        if options.get("registo_id"):
            path = (
                f"/app/registos/meus/{options['registo_id']}/editar/"
                if employee_scope
                else f"/app/registos/admin/{options['registo_id']}/editar/"
            )
            routes.append(SmokeRoute("detail-registo", path, AUTH_OK))
            if options.get("include_report_pdf"):
                pdf_path = (
                    f"/app/registos/meus/relatorios/{options['registo_id']}/pdf/"
                    if employee_scope
                    else f"/app/registos/admin/relatorios/{options['registo_id']}/pdf/"
                )
                routes.append(SmokeRoute("detail-relatorio-pdf", pdf_path, AUTH_OK, "application/pdf"))

        if options.get("material_id"):
            routes.append(SmokeRoute("detail-material", f"/app/materiais/{options['material_id']}/", AUTH_OK))

        if options.get("medicao_id"):
            path = (
                f"/app/minha-area/medicoes/{options['medicao_id']}/"
                if employee_scope
                else f"/app/medicoes/{options['medicao_id']}/editar/"
            )
            routes.append(SmokeRoute("detail-medicao", path, AUTH_OK))

        return routes

    def _check_routes(self, *, client, routes):
        resultados = []
        for route in routes:
            try:
                response = client.get(route.path, secure=True)
            except Exception as exc:
                resultados.append((route.nome, False, f"Exceção em {route.path}: {exc}"))
                continue

            ok = response.status_code in route.allowed_statuses
            esperado = "/".join(str(status) for status in route.allowed_statuses)
            mensagem = f"{route.path} respondeu {response.status_code}."
            if not ok:
                mensagem = f"{route.path} respondeu {response.status_code}; esperado {esperado}."
            elif route.expected_content_type:
                content_type = response.headers.get("Content-Type", "")
                ok = content_type.startswith(route.expected_content_type)
                mensagem = (
                    f"{route.path} respondeu {response.status_code} com {content_type}."
                    if ok
                    else f"{route.path} respondeu Content-Type {content_type}; esperado {route.expected_content_type}."
                )
            resultados.append((route.nome, ok, mensagem))
        return resultados
