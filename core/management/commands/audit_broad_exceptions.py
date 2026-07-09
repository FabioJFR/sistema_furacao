import ast
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


IGNORED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "htmlcov",
    "migrations",
    "node_modules",
    "staticfiles",
}


class BroadExceptionVisitor(ast.NodeVisitor):
    def __init__(self):
        self.findings = []

    def visit_ExceptHandler(self, node):
        if node.type is None:
            self.findings.append((node.lineno, "bare-except"))
        elif isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"}:
            self.findings.append((node.lineno, node.type.id))
        self.generic_visit(node)


def _iter_python_files(root):
    for path in root.rglob("*.py"):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        yield path


def _audit_file(path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError) as exc:
        return [(path, 0, f"parse-error: {exc}")]

    visitor = BroadExceptionVisitor()
    visitor.visit(tree)
    return [(path, line, kind) for line, kind in visitor.findings]


class Command(BaseCommand):
    help = "Inventaria handlers genéricos except:/except Exception para reduzir silêncios defensivos."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=str(settings.BASE_DIR),
            help="Diretoria ou ficheiro Python a auditar. Por defeito usa BASE_DIR.",
        )
        parser.add_argument(
            "--fail-on-found",
            action="store_true",
            help="Falha quando encontra handlers genéricos.",
        )

    def handle(self, *args, **options):
        root = Path(options["path"]).resolve()
        if not root.exists():
            raise CommandError(f"Caminho não encontrado: {root}")

        if root.is_file():
            files = [root] if root.suffix == ".py" else []
        else:
            files = list(_iter_python_files(root))

        findings = []
        for path in files:
            findings.extend(_audit_file(path))

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Broad exception audit"))
        if findings:
            for path, line, kind in findings:
                rel_path = path.relative_to(root) if root.is_dir() and path.is_relative_to(root) else path
                line_label = f":{line}" if line else ""
                self.stdout.write(self.style.WARNING(f"[AVISO] {rel_path}{line_label}: {kind}"))
        else:
            self.stdout.write(self.style.SUCCESS("[OK] Nenhum handler genérico encontrado."))

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Resumo: {len(files)} ficheiro(s) analisado(s), {len(findings)} ocorrência(s)."
            )
        )

        if findings and options["fail_on_found"]:
            raise CommandError("Foram encontrados handlers genéricos. Revê ou documenta estes fallbacks.")
