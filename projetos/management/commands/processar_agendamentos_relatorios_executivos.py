from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from projetos.models import AgendamentoRelatorioExecutivo
from projetos.views.gestao_empresa import _executar_envio_agendado_empresa
from projetos.services.gestao_relatorios import calcular_proximo_envio_agendado


class Command(BaseCommand):
    help = "Processa envios automáticos pendentes de Relatórios Executivos (Gestão)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--empresa-id",
            dest="empresa_id",
            default="",
            help="Opcional: processa apenas a empresa indicada.",
        )

    def handle(self, *args, **options):
        agora = timezone.now()
        empresa_id = (options.get("empresa_id") or "").strip()

        qs = AgendamentoRelatorioExecutivo.objects.filter(ativo=True).select_related("empresa")
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)

        total = qs.count()
        enviados = 0
        erros = 0

        for agendamento in qs:
            proximo = agendamento.proximo_envio_em
            if not proximo:
                proximo = calcular_proximo_envio_agendado(agendamento=agendamento, referencia=agora - timedelta(minutes=1))
                agendamento.proximo_envio_em = proximo
                agendamento.save(update_fields=["proximo_envio_em", "atualizado_em"])

            if proximo and proximo > agora:
                continue

            try:
                _executar_envio_agendado_empresa(
                    empresa=agendamento.empresa,
                    agendamento=agendamento,
                    referencia=agora,
                )
                agendamento.ultimo_envio_em = agora
                agendamento.proximo_envio_em = calcular_proximo_envio_agendado(agendamento=agendamento, referencia=agora)
                agendamento.save(update_fields=["ultimo_envio_em", "proximo_envio_em", "atualizado_em"])
                enviados += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] Empresa {agendamento.empresa_id}: envio executado."))
            except Exception as exc:
                erros += 1
                self.stdout.write(self.style.ERROR(f"[ERRO] Empresa {agendamento.empresa_id}: {exc}"))

        self.stdout.write(
            self.style.WARNING(
                f"Processamento concluído. Total ativos={total}, enviados={enviados}, erros={erros}."
            )
        )
