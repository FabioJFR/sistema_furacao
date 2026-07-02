from django.core.management.base import BaseCommand
from django.db import transaction

from plataforma.models import PerfilPlataforma
from projetos.models import Empregados, Modelo3DBlock, Modelo3DImplicit, Modelo3DWireframe, Projeto


MODELOS_3D = {
    "wireframe": Modelo3DWireframe,
    "implicit": Modelo3DImplicit,
    "block": Modelo3DBlock,
}


class Command(BaseCommand):
    help = (
        "Propoe ou aplica backfill de empresa/projeto em modelos 3D legados, "
        "mantendo dry-run por defeito."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplica as alteracoes propostas. Sem esta flag, apenas mostra o dry-run.",
        )
        parser.add_argument(
            "--modelo",
            choices=["all", *MODELOS_3D.keys()],
            default="all",
            help="Tipo de modelo 3D a processar.",
        )
        parser.add_argument(
            "--assign-single-project",
            action="store_true",
            help="Associa automaticamente o unico projeto da empresa quando existir exatamente um.",
        )

    def handle(self, *args, **options):
        aplicar = options["apply"]
        assign_single_project = options["assign_single_project"]
        modelos = self._modelos_a_processar(options["modelo"])

        total_analisados = 0
        total_propostos = 0
        total_atualizados = 0
        total_sem_candidato = 0

        if not aplicar:
            self.stdout.write(self.style.WARNING("DRY-RUN: nenhuma alteracao sera gravada. Usa --apply para aplicar."))

        for chave, model_cls in modelos:
            analisados, propostos, atualizados, sem_candidato = self._processar_modelo(
                chave=chave,
                model_cls=model_cls,
                aplicar=aplicar,
                assign_single_project=assign_single_project,
            )
            total_analisados += analisados
            total_propostos += propostos
            total_atualizados += atualizados
            total_sem_candidato += sem_candidato

        self.stdout.write(
            self.style.SUCCESS(
                "Resumo backfill 3D: "
                f"{total_analisados} analisado(s), "
                f"{total_propostos} proposta(s), "
                f"{total_atualizados} atualizado(s), "
                f"{total_sem_candidato} sem candidato."
            )
        )

    def _modelos_a_processar(self, modelo):
        if modelo == "all":
            return list(MODELOS_3D.items())
        return [(modelo, MODELOS_3D[modelo])]

    def _processar_modelo(self, *, chave, model_cls, aplicar, assign_single_project):
        qs = (
            model_cls.objects
            .filter(empresa__isnull=True)
            .select_related("criado_por", "empresa", "projeto")
            .order_by("criado_em")
        )
        analisados = qs.count()
        propostos = 0
        atualizados = 0
        sem_candidato = 0

        for item in qs:
            empresa = self._resolver_empresa(item)
            if not empresa:
                sem_candidato += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"[{chave}] sem candidato: {item.pk} · {item.nome}"
                    )
                )
                continue

            projeto = self._resolver_projeto(item=item, empresa=empresa, assign_single_project=assign_single_project)
            propostos += 1
            self.stdout.write(
                f"[{chave}] {item.pk} · {item.nome} -> empresa={empresa.nome}"
                + (f", projeto={projeto.nome}" if projeto else "")
            )

            if aplicar:
                with transaction.atomic():
                    item.empresa = empresa
                    update_fields = ["empresa", "atualizado_em"]
                    if projeto and not item.projeto_id:
                        item.projeto = projeto
                        update_fields.append("projeto")
                    item.save(update_fields=update_fields)
                    atualizados += 1

        return analisados, propostos, atualizados, sem_candidato

    def _resolver_empresa(self, item):
        if item.empresa_id:
            return item.empresa

        if item.projeto_id and item.projeto and item.projeto.empresa_id:
            return item.projeto.empresa

        user = item.criado_por
        if not user:
            return None

        perfil = (
            PerfilPlataforma.objects
            .filter(user=user, ativo=True, empresa__isnull=False)
            .select_related("empresa")
            .first()
        )
        if perfil:
            return perfil.empresa

        empregado = (
            Empregados.objects
            .filter(user=user, aprovado=True, empresa__isnull=False)
            .select_related("empresa")
            .first()
        )
        if empregado:
            return empregado.empresa

        return None

    def _resolver_projeto(self, *, item, empresa, assign_single_project):
        if item.projeto_id:
            return item.projeto

        if not assign_single_project:
            return None

        projetos = list(Projeto.objects.filter(empresa=empresa).order_by("nome")[:2])
        if len(projetos) == 1:
            return projetos[0]
        return None
