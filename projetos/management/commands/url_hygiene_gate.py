import re
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Executa gate de URL hygiene e validacao Django check para pre-release."

    def add_arguments(self, parser):
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Falha com exit code != 0 se encontrar violacoes.",
        )
        parser.add_argument(
            "--skip-check",
            action="store_true",
            help="Nao corre `manage.py check` no fim.",
        )

    def handle(self, *args, **options):
        root = Path.cwd()
        strict = options["strict"]
        skip_check = options["skip_check"]

        findings = []

        template_roots = [
            root / "projetos" / "templates",
            root / "plataforma" / "templates",
            root / "geologia" / "templates",
            root / "inspecao_ai" / "templates",
        ]
        js_roots = [root / "static" / "js"]
        py_roots = [
            root / "projetos",
            root / "plataforma",
            root / "geologia",
            root / "inspecao_ai",
        ]

        template_patterns = [
            re.compile(r'href="/(?:app|plataforma|projetos|admin|logout)'),
            re.compile(r'action="/(?:app|plataforma|projetos)'),
        ]
        js_patterns = [
            re.compile(r'["\']/(?:app|plataforma|projetos)/'),
        ]
        py_patterns = [
            re.compile(r'redirect\(\s*["\']/'),
        ]

        def scan_files(base_paths, glob_pattern, patterns, category):
            for base in base_paths:
                if not base.exists():
                    continue
                for file_path in base.rglob(glob_pattern):
                    if not file_path.is_file():
                        continue
                    try:
                        content = file_path.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        continue
                    for line_no, line in enumerate(content.splitlines(), start=1):
                        if any(pattern.search(line) for pattern in patterns):
                            rel = file_path.relative_to(root)
                            findings.append((category, rel, line_no, line.strip()))

        scan_files(template_roots, "*.html", template_patterns, "template")
        scan_files(js_roots, "*.js", js_patterns, "javascript")
        scan_files(py_roots, "*.py", py_patterns, "python")

        if findings:
            self.stdout.write(self.style.WARNING("Foram encontradas violacoes de URL hygiene:"))
            for category, rel, line_no, line in findings:
                self.stdout.write(f"- [{category}] {rel}:{line_no} -> {line}")
        else:
            self.stdout.write(self.style.SUCCESS("Sem violacoes de URL hygiene nos escopos definidos."))

        if not skip_check:
            self.stdout.write("A correr validacao Django check...")
            call_command("check")

        if findings and strict:
            raise CommandError(
                f"URL hygiene gate falhou com {len(findings)} violacao(oes)."
            )

        if findings:
            self.stdout.write(
                self.style.WARNING(
                    f"Gate concluido com {len(findings)} violacao(oes) (modo nao estrito)."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("URL hygiene gate concluido com sucesso."))
