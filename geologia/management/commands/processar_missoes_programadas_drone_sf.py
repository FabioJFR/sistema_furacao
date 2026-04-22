from django.core.management.base import BaseCommand, CommandError

from geologia.services import processar_missoes_programadas_drone_sf
from plataforma.models import Empresa


class Command(BaseCommand):
    help = "Processa as missões programadas ativas do Drone S_F e coloca os comandos devidos na fila."

    def add_arguments(self, parser):
        parser.add_argument("--empresa", default="", help="Nome da empresa a processar. Se omitido, processa todas.")

    def handle(self, *args, **options):
        empresa = self._resolver_empresa(options["empresa"].strip())
        resumo = processar_missoes_programadas_drone_sf(empresa=empresa)

        scope = empresa.nome if empresa else "todas as empresas"
        self.stdout.write(self.style.SUCCESS(f"Motor de missões Drone S_F executado para {scope}."))
        self.stdout.write(
            f"Processadas: {resumo['processadas']} | Executadas: {resumo['executadas']} | "
            f"Ignoradas: {resumo['ignoradas']} | Sem operação: {resumo['sem_operacao']} | "
            f"Pontuais desativadas: {resumo['desativadas']}"
        )

    def _resolver_empresa(self, nome_empresa):
        if not nome_empresa:
            return None
        empresa = Empresa.objects.filter(nome=nome_empresa).first()
        if empresa is None:
            raise CommandError(f"Empresa '{nome_empresa}' não encontrada.")
        return empresa
