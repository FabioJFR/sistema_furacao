import random
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from geologia.models import LogGeologicoFuro
from projetos.models import Empregados, Furo


LITOLOGIAS_BASE = [
    "granito",
    "quartzo",
    "xisto",
    "xisto escuro",
    "xisto claro",
    "argila",
    "pirite",
    "minério",
    "jaspe",
]

CORES_BASE = ["cinzento", "castanho", "amarelo", "avermelhado", "esverdeado", "escuro", "claro"]
GRANULOMETRIAS_BASE = ["fina", "média", "grossa"]
ALTERACOES_BASE = ["fraca", "moderada", "forte"]
ESTRUTURAS_BASE = ["maciça", "foliada", "fraturada"]
DENSIDADES_FRATURAS_BASE = ["baixa", "média", "alta"]
MINERALIZACOES_BASE = ["ausente", "dispersa", "moderada", "elevada"]


class Command(BaseCommand):
    help = "Preenche logs geológicos de furos da empresa associada a um empregado geólogo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default="empregadogeologoteste",
            help="Username do empregado geólogo (default: empregadogeologoteste).",
        )
        parser.add_argument(
            "--por-furo",
            type=int,
            default=3,
            help="Quantidade de logs a criar por furo (default: 3).",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Seed para geração determinística (default: 42).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra o que seria criado sem gravar na base de dados.",
        )
        parser.add_argument(
            "--ignorar-existentes",
            action="store_true",
            help="Se definido, cria mesmo que já existam logs no furo.",
        )

    def handle(self, *args, **options):
        username = options["username"]
        por_furo = options["por_furo"]
        dry_run = options["dry_run"]
        ignorar_existentes = options["ignorar_existentes"]
        random.seed(options["seed"])

        if por_furo < 1:
            raise CommandError("--por-furo deve ser >= 1.")

        empregado = (
            Empregados.objects.select_related("empresa", "user")
            .filter(user__username=username)
            .first()
        )
        if not empregado:
            raise CommandError(f"Empregado com username '{username}' não encontrado.")
        if not empregado.empresa_id:
            raise CommandError(f"Empregado '{username}' não está associado a uma empresa.")
        if (empregado.funcao or "").strip().lower() != "geologo":
            raise CommandError(
                f"Empregado '{username}' existe, mas função atual é '{empregado.funcao}'. Esperado: 'geologo'."
            )

        furos = Furo.objects.filter(empresa_id=empregado.empresa_id).order_by("nome", "pk")
        if not furos.exists():
            raise CommandError("Não existem furos para a empresa deste geólogo.")

        total_previsto = 0
        total_criado = 0
        hoje = timezone.localdate()

        self.stdout.write(
            self.style.NOTICE(
                f"Geólogo: {username} | Empresa: {empregado.empresa.nome} | Furos encontrados: {furos.count()}"
            )
        )

        for furo in furos:
            logs_existentes = LogGeologicoFuro.objects.filter(furo=furo).count()
            if logs_existentes > 0 and not ignorar_existentes:
                self.stdout.write(
                    f"- {furo.nome}: já tem {logs_existentes} logs (usar --ignorar-existentes para acrescentar)."
                )
                continue

            profundidade = float(furo.profundidade_atual or 0.0)
            profundidade = max(profundidade, 30.0)
            passo = max(profundidade / float(por_furo), 1.0)

            for idx in range(por_furo):
                inicio = round(idx * passo, 2)
                fim = round(min((idx + 1) * passo, profundidade), 2)
                if fim <= inicio:
                    fim = round(inicio + 1.0, 2)

                litologia = random.choice(LITOLOGIAS_BASE)
                titulo = f"{furo.nome} · Intervalo {inicio:.2f}m-{fim:.2f}m"

                payload = {
                    "empresa_id": furo.empresa_id,
                    "furo": furo,
                    "titulo": titulo,
                    "data_registo": hoje - timedelta(days=max(0, por_furo - idx - 1)),
                    "intervalo_de": inicio,
                    "intervalo_ate": fim,
                    "recuperacao_testemunho_percent": round(random.uniform(70, 99), 2),
                    "rqd_percent": round(random.uniform(55, 96), 2),
                    "litologia_principal": litologia,
                    "litologia_secundaria": random.choice([l for l in LITOLOGIAS_BASE if l != litologia]),
                    "cor": random.choice(CORES_BASE),
                    "granulometria": random.choice(GRANULOMETRIAS_BASE),
                    "alteracao": random.choice(ALTERACOES_BASE),
                    "mineralizacao": random.choice(MINERALIZACOES_BASE),
                    "estrutura": random.choice(ESTRUTURAS_BASE),
                    "densidade_fraturas": random.choice(DENSIDADES_FRATURAS_BASE),
                    "nivel_agua_m": round(random.uniform(0, max(profundidade * 0.2, 1.0)), 2),
                    "observacoes": "Log gerado automaticamente para testes operacionais de geologia.",
                }

                total_previsto += 1
                if dry_run:
                    self.stdout.write(f"  [dry-run] {furo.nome}: {titulo}")
                    continue

                log = LogGeologicoFuro(**payload)
                log.full_clean()
                log.save()
                total_criado += 1

            if dry_run:
                self.stdout.write(f"- {furo.nome}: seriam criados {por_furo} logs.")
            else:
                self.stdout.write(f"- {furo.nome}: criados {por_furo} logs.")

        if dry_run:
            self.stdout.write(self.style.WARNING(f"Dry-run concluído. Logs previstos: {total_previsto}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Concluído. Logs criados: {total_criado}"))
