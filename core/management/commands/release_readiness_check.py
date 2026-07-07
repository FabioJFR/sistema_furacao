from dataclasses import dataclass
import os
import shutil

from django.conf import settings
from django.core import checks
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.migrations.executor import MigrationExecutor

from core.settings import secret_key_looks_unsafe


MIGRACOES_CRITICAS = [
    ("dispositivos", "0006_importacaodispositivohistorico"),
]


@dataclass
class ReadinessItem:
    slug: str
    ok: bool
    nivel: str
    mensagem: str
    detalhe: str = ""


class Command(BaseCommand):
    help = "Executa gate de readiness antes de demo, release ou deploy."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Falha em requisitos fortes de produção e inclui deployment checks do Django.",
        )
        parser.add_argument(
            "--skip-db",
            action="store_true",
            help="Não valida ligação à base de dados/migrações pendentes.",
        )
        parser.add_argument(
            "--skip-system-check",
            action="store_true",
            help="Não executa o framework de checks do Django.",
        )

    def handle(self, *args, **options):
        strict = options["strict"]
        resultados = []
        resultados.extend(self._avaliar_configuracao(strict=strict))

        if not options["skip_system_check"]:
            resultados.extend(self._avaliar_django_checks(strict=strict))

        if not options["skip_db"]:
            resultados.extend(self._avaliar_migracoes(strict=strict))

        falhas = [item for item in resultados if not item.ok and item.nivel == "erro"]
        avisos = [item for item in resultados if not item.ok and item.nivel == "aviso"]

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Release readiness check"))
        for item in resultados:
            marker = "OK" if item.ok else ("ERRO" if item.nivel == "erro" else "AVISO")
            style = self.style.SUCCESS if item.ok else (self.style.ERROR if item.nivel == "erro" else self.style.WARNING)
            self.stdout.write(style(f"[{marker}] {item.slug}: {item.mensagem}"))
            if item.detalhe:
                self.stdout.write(f"      {item.detalhe}")

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Resumo: {len(resultados) - len(falhas) - len(avisos)} OK, {len(avisos)} aviso(s), {len(falhas)} erro(s)."
            )
        )

        if falhas:
            raise CommandError("Release readiness falhou. Corrige os erros antes de avançar.")

    def _avaliar_configuracao(self, *, strict):
        itens = []
        self._add(
            itens,
            slug="debug",
            ok=not settings.DEBUG,
            nivel="erro" if strict else "aviso",
            mensagem="DEBUG está desativado." if not settings.DEBUG else "DEBUG está ativo.",
            detalhe="Para produção/demo externa usa DJANGO_DEBUG=False.",
        )
        self._add(
            itens,
            slug="secret-key",
            ok=bool(settings.SECRET_KEY) and not secret_key_looks_unsafe(settings.SECRET_KEY),
            nivel="erro" if strict else "aviso",
            mensagem="SECRET_KEY parece forte." if not secret_key_looks_unsafe(settings.SECRET_KEY) else "SECRET_KEY insegura.",
            detalhe="Usa uma chave longa, aleatória e fora do repositório.",
        )
        allowed_hosts = list(getattr(settings, "ALLOWED_HOSTS", []) or [])
        hosts_ok = bool(allowed_hosts) and "*" not in allowed_hosts
        self._add(
            itens,
            slug="allowed-hosts",
            ok=hosts_ok,
            nivel="erro" if strict else "aviso",
            mensagem="ALLOWED_HOSTS configurado sem wildcard." if hosts_ok else "ALLOWED_HOSTS vazio ou permissivo.",
            detalhe="Define DJANGO_ALLOWED_HOSTS com domínio/IP reais antes de apresentar fora do local.",
        )
        self._add(
            itens,
            slug="cookies-secure",
            ok=bool(settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE),
            nivel="erro" if strict else "aviso",
            mensagem="Cookies de sessão/CSRF marcados como seguros." if settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE else "Cookies seguros não estão totalmente ativos.",
            detalhe="Em HTTPS real, DJANGO_SESSION_COOKIE_SECURE=True e DJANGO_CSRF_COOKIE_SECURE=True.",
        )
        self._add(
            itens,
            slug="https-hsts",
            ok=bool(settings.SECURE_SSL_REDIRECT and settings.SECURE_HSTS_SECONDS > 0),
            nivel="erro" if strict else "aviso",
            mensagem="HTTPS redirect e HSTS ativos." if settings.SECURE_SSL_REDIRECT and settings.SECURE_HSTS_SECONDS > 0 else "HTTPS redirect/HSTS incompletos.",
            detalhe="Para produção usa DJANGO_SECURE_SSL_REDIRECT=True e HSTS > 0.",
        )
        db_config = settings.DATABASES.get("default", {})
        db_credentials_ok = self._database_credentials_safe(db_config)
        self._add(
            itens,
            slug="database-credentials",
            ok=db_credentials_ok,
            nivel="erro" if strict else "aviso",
            mensagem=(
                "Credenciais da base de dados não usam defaults conhecidos."
                if db_credentials_ok
                else "Credenciais da base de dados parecem defaults/inseguras."
            ),
            detalhe=(
                "Define POSTGRES_DB, POSTGRES_USER e POSTGRES_PASSWORD próprios do ambiente; "
                "evita postgres/postgres/postgres_db em produção."
            ),
        )
        antivirus_enabled = bool(settings.UPLOAD_VIRUS_SCAN_ENABLED and settings.UPLOAD_VIRUS_SCAN_FAIL_CLOSED)
        antivirus_command = getattr(settings, "UPLOAD_VIRUS_SCAN_COMMAND", "clamscan")
        antivirus_command_ok = self._antivirus_command_available(antivirus_command)
        antivirus_ok = antivirus_enabled and antivirus_command_ok
        detalhe_antivirus = (
            f"Comando configurado: {antivirus_command}."
            if antivirus_command_ok
            else (
                "Antes de vender/abrir uploads reais, ativa UPLOAD_VIRUS_SCAN_ENABLED=True, "
                "fail-closed e garante que UPLOAD_VIRUS_SCAN_COMMAND aponta para um executável disponível."
            )
        )
        self._add(
            itens,
            slug="upload-antivirus",
            ok=antivirus_ok,
            nivel="erro" if strict else "aviso",
            mensagem=(
                "Antivírus de upload ativo, fail-closed e executável disponível."
                if antivirus_ok
                else "Antivírus de upload não está operacional em modo produção completo."
            ),
            detalhe=detalhe_antivirus,
        )
        cache_backend = settings.CACHES.get("default", {}).get("BACKEND", "")
        cache_ok = "LocMemCache" not in cache_backend
        self._add(
            itens,
            slug="cache-rate-limit",
            ok=cache_ok,
            nivel="erro" if strict else "aviso",
            mensagem="Cache partilhável configurada para rate-limit." if cache_ok else "Cache local em memória configurada.",
            detalhe="Em produção multi-worker usa Redis/Memcached para rate limits consistentes.",
        )
        mfa_required = bool(getattr(settings, "MFA_REQUIRED", False))
        self._add(
            itens,
            slug="mfa-required",
            ok=mfa_required,
            nivel="erro" if strict else "aviso",
            mensagem="MFA obrigatório sinalizado para produção." if mfa_required else "MFA obrigatório não está sinalizado.",
            detalhe=(
                "Antes de vender ou apresentar com contas reais, ativa MFA_REQUIRED=True e valida o fluxo operacional "
                "de segundo fator para superuser/admins."
            ),
        )
        return itens

    def _database_credentials_safe(self, db_config):
        name = str(db_config.get("NAME") or "").strip().lower()
        user = str(db_config.get("USER") or "").strip().lower()
        password = str(db_config.get("PASSWORD") or "").strip()
        unsafe_names = {"", "postgres", "postgres_db", "sistema_furacao", "test"}
        unsafe_users = {"", "postgres", "admin", "root"}
        unsafe_passwords = {"", "postgres", "password", "admin", "root", "123456", "sistema_furacao"}
        return name not in unsafe_names and user not in unsafe_users and password.lower() not in unsafe_passwords

    def _antivirus_command_available(self, command):
        if not command:
            return False
        command = str(command).strip()
        if os.path.isabs(command):
            return os.path.isfile(command) and os.access(command, os.X_OK)
        return shutil.which(command) is not None

    def _avaliar_django_checks(self, *, strict):
        mensagens = checks.run_checks(include_deployment_checks=strict)
        if not mensagens:
            return [
                ReadinessItem(
                    slug="django-checks",
                    ok=True,
                    nivel="ok",
                    mensagem="Checks do Django sem problemas.",
                )
            ]

        itens = []
        for mensagem in mensagens:
            is_error = mensagem.level >= checks.ERROR
            itens.append(
                ReadinessItem(
                    slug=f"django-check:{mensagem.id}",
                    ok=False,
                    nivel="erro" if is_error else "aviso",
                    mensagem=str(mensagem.msg),
                    detalhe=str(mensagem.hint or ""),
                )
            )
        return itens

    def _avaliar_migracoes(self, *, strict):
        try:
            connection = connections[DEFAULT_DB_ALIAS]
            executor = MigrationExecutor(connection)
            plano = executor.migration_plan(executor.loader.graph.leaf_nodes())
        except Exception as exc:
            return [
                ReadinessItem(
                    slug="database",
                    ok=False,
                    nivel="erro" if strict else "aviso",
                    mensagem="Não foi possível validar base de dados/migrações.",
                    detalhe=str(exc),
                )
            ]

        if plano:
            return [
                ReadinessItem(
                    slug="migrations",
                    ok=False,
                    nivel="erro",
                    mensagem=f"Existem {len(plano)} migração(ões) pendente(s).",
                    detalhe="Executa python manage.py migrate antes de demo/deploy.",
                )
            ]

        itens = [
            ReadinessItem(
                slug="migrations",
                ok=True,
                nivel="ok",
                mensagem="Sem migrações pendentes.",
            )
        ]
        itens.extend(self._avaliar_migracoes_criticas(executor.loader))
        return itens

    def _avaliar_migracoes_criticas(self, loader):
        aplicadas = set(getattr(loader, "applied_migrations", set()) or set())
        itens = []
        for app_label, migration_name in MIGRACOES_CRITICAS:
            slug = f"migration:{app_label}.{migration_name}"
            aplicada = (app_label, migration_name) in aplicadas
            itens.append(
                ReadinessItem(
                    slug=slug,
                    ok=aplicada,
                    nivel="erro",
                    mensagem=(
                        f"Migração crítica {app_label}.{migration_name} aplicada."
                        if aplicada
                        else f"Migração crítica {app_label}.{migration_name} não está aplicada."
                    ),
                    detalhe=(
                        ""
                        if aplicada
                        else "Executa python manage.py migrate e repete o readiness check antes de demo/deploy."
                    ),
                )
            )
        return itens

    def _add(self, itens, *, slug, ok, nivel, mensagem, detalhe=""):
        itens.append(
            ReadinessItem(
                slug=slug,
                ok=ok,
                nivel=nivel,
                mensagem=mensagem,
                detalhe="" if ok else detalhe,
            )
        )
