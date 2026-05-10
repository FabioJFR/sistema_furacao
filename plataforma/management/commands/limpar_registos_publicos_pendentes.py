from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from plataforma.models import PerfilPlataforma


class Command(BaseCommand):
    help = (
        "Limpa registos públicos pendentes e não confirmados de forma conservadora. "
        "Por omissão executa em modo de simulação."
    )

    ACCESSORES_AUTOMATICOS_PERMITIDOS = {
        "subscricoes",
        "pagamentos",
        "movimentos_financeiros",
        "perfis_acesso",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Idade mínima em dias para considerar o registo elegível para limpeza.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Aplica realmente a limpeza. Sem esta flag, corre em modo dry-run.",
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options["days"])
        candidatos = self._obter_candidatos(cutoff=cutoff)

        self.stdout.write(
            self.style.WARNING(
                f"Foram encontrados {len(candidatos)} registos públicos pendentes elegíveis para limpeza."
            )
        )

        for item in candidatos[:50]:
            self.stdout.write(
                f"- empresa={item['empresa_nome']} | email={item['email']} | criado_em={item['date_joined']}"
            )

        if not options["confirm"]:
            self.stdout.write(
                self.style.WARNING(
                    "Modo dry-run: nada foi apagado. Usa --confirm para aplicar."
                )
            )
            return

        removidos = 0
        for item in candidatos:
            self._apagar_registo(item["user_id"], item["empresa_id"])
            removidos += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Limpeza concluída. Registos removidos: {removidos}."
            )
        )

    def _obter_candidatos(self, *, cutoff):
        perfis = (
            PerfilPlataforma.objects
            .select_related("user", "empresa")
            .filter(
                tipo_acesso="empresa_admin",
                user__is_active=False,
                empresa__isnull=False,
                empresa__status="teste",
                user__date_joined__lt=cutoff,
            )
            .order_by("user__date_joined")
        )

        candidatos = []
        for perfil in perfis:
            empresa = perfil.empresa
            user = perfil.user
            if not empresa or not user:
                continue
            if not self._empresa_elegivel_para_limpeza(empresa):
                continue
            candidatos.append(
                {
                    "empresa_id": empresa.pk,
                    "empresa_nome": empresa.nome,
                    "user_id": user.pk,
                    "email": user.email,
                    "date_joined": user.date_joined,
                }
            )
        return candidatos

    def _empresa_elegivel_para_limpeza(self, empresa):
        if empresa.perfis_acesso.count() != 1:
            return False

        if empresa.perfis_acesso.exclude(user__is_active=False, tipo_acesso="empresa_admin").exists():
            return False

        if not empresa.subscricoes.exists():
            return False

        if empresa.subscricoes.exclude(estado="pendente").exists():
            return False

        for related in empresa._meta.related_objects:
            accessor = related.get_accessor_name()
            if accessor in self.ACCESSORES_AUTOMATICOS_PERMITIDOS:
                continue

            manager = getattr(empresa, accessor, None)
            if manager is None:
                continue

            try:
                if manager.exists():
                    return False
            except Exception:
                return False

        return True

    @transaction.atomic
    def _apagar_registo(self, user_id, empresa_id):
        user = User.objects.filter(pk=user_id, is_active=False).first()
        if user:
            user.delete()

        perfil = PerfilPlataforma.objects.filter(empresa_id=empresa_id).first()
        if perfil:
            return

        empresa_model = PerfilPlataforma._meta.get_field("empresa").remote_field.model
        empresa = empresa_model.objects.filter(pk=empresa_id, status="teste").first()
        if empresa:
            empresa.delete()
