from pathlib import Path
import re

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Deteta CSS inline em templates (atributos style e blocos de estilo)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Falha se encontrar CSS inline.",
        )

    def handle(self, *args, **options):
        root = Path.cwd()
        strict = options["strict"]

        template_roots = [
            root / "projetos" / "templates",
            root / "plataforma" / "templates",
            root / "geologia" / "templates",
            root / "inspecao_ai" / "templates",
            root / "website" / "templates",
        ]

        pattern_style_attr = re.compile(r'style="')
        pattern_style_block = re.compile(r"<\s*style\b", re.IGNORECASE)

        findings = []

        for base in template_roots:
            if not base.exists():
                continue
            for file_path in base.rglob("*.html"):
                try:
                    content = file_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                for line_no, line in enumerate(content.splitlines(), start=1):
                    if pattern_style_attr.search(line) or pattern_style_block.search(line):
                        findings.append((file_path.relative_to(root), line_no, line.strip()))

        if findings:
            self.stdout.write(self.style.WARNING("CSS inline encontrado:"))
            for rel, line_no, line in findings:
                self.stdout.write(f"- {rel}:{line_no} -> {line}")
        else:
            self.stdout.write(self.style.SUCCESS("Sem CSS inline nos templates analisados."))

        if findings and strict:
            raise CommandError(f"CSS hygiene gate falhou com {len(findings)} ocorrência(s).")

        if findings:
            self.stdout.write(self.style.WARNING(f"Gate concluído com {len(findings)} ocorrência(s) (modo não estrito)."))
        else:
            self.stdout.write(self.style.SUCCESS("CSS hygiene gate concluído com sucesso."))
