from django.core.management.base import BaseCommand

from projetos.models import (
    ConfiguracaoPerfuracaoEmpregado,
    DevolucaoMaterial,
    Despesa,
    EmpregadoFuro,
    EmpregadoProjeto,
    Furo,
    LevantamentoMaterial,
    Maquina,
    Material,
    Medicao,
    RegistoDiarioEmpregado,
)


class Command(BaseCommand):
    help = "Audita incoerências multiempresa nos principais modelos do sistema."

    def handle(self, *args, **options):
        erros = []

        # 1. Furo -> Projeto
        for obj in Furo.objects.select_related("projeto", "empresa"):
            if obj.projeto_id and obj.projeto and obj.projeto.empresa_id != obj.empresa_id:
                erros.append(
                    f"Furo inconsistente: furo={obj.nome} "
                    f"(empresa={obj.empresa_id}) / projeto={obj.projeto.nome} "
                    f"(empresa={obj.projeto.empresa_id})"
                )

        # 2. EmpregadoProjeto
        for obj in EmpregadoProjeto.objects.select_related("empregado", "projeto", "empresa"):
            if obj.empregado_id and obj.projeto_id:
                if obj.empregado.empresa_id != obj.projeto.empresa_id:
                    erros.append(
                        f"EmpregadoProjeto inconsistente: empregado={obj.empregado.nome} "
                        f"(empresa={obj.empregado.empresa_id}) / projeto={obj.projeto.nome} "
                        f"(empresa={obj.projeto.empresa_id})"
                    )

                if obj.empresa_id and (
                    obj.empresa_id != obj.empregado.empresa_id or
                    obj.empresa_id != obj.projeto.empresa_id
                ):
                    erros.append(
                        f"EmpregadoProjeto empresa divergente: empregado={obj.empregado.nome}, "
                        f"projeto={obj.projeto.nome}, empresa_ligacao={obj.empresa_id}"
                    )

        # 3. EmpregadoFuro
        for obj in EmpregadoFuro.objects.select_related("empregado", "furo", "empresa"):
            if obj.empregado_id and obj.furo_id:
                if obj.empregado.empresa_id != obj.furo.empresa_id:
                    erros.append(
                        f"EmpregadoFuro inconsistente: empregado={obj.empregado.nome} "
                        f"(empresa={obj.empregado.empresa_id}) / furo={obj.furo.nome} "
                        f"(empresa={obj.furo.empresa_id})"
                    )

                if obj.empresa_id and (
                    obj.empresa_id != obj.empregado.empresa_id or
                    obj.empresa_id != obj.furo.empresa_id
                ):
                    erros.append(
                        f"EmpregadoFuro empresa divergente: empregado={obj.empregado.nome}, "
                        f"furo={obj.furo.nome}, empresa_ligacao={obj.empresa_id}"
                    )

        # 4. Material
        for obj in Material.objects.select_related("projeto", "furo", "empresa"):
            if obj.projeto_id and obj.projeto and obj.empresa_id != obj.projeto.empresa_id:
                erros.append(
                    f"Material/projeto inconsistente: material={obj.nome}, "
                    f"empresa_material={obj.empresa_id}, projeto={obj.projeto.nome}, "
                    f"empresa_projeto={obj.projeto.empresa_id}"
                )

            if obj.furo_id and obj.furo and obj.empresa_id != obj.furo.empresa_id:
                erros.append(
                    f"Material/furo inconsistente: material={obj.nome}, "
                    f"empresa_material={obj.empresa_id}, furo={obj.furo.nome}, "
                    f"empresa_furo={obj.furo.empresa_id}"
                )

            if obj.projeto_id and obj.furo_id and obj.furo.projeto_id != obj.projeto_id:
                erros.append(
                    f"Material contexto incoerente: material={obj.nome}, "
                    f"projeto={obj.projeto.nome}, furo={obj.furo.nome}, "
                    f"projeto_do_furo={obj.furo.projeto_id}"
                )

        # 5. LevantamentoMaterial
        for obj in LevantamentoMaterial.objects.select_related("empregado", "material", "projeto", "furo", "empresa"):
            if obj.empregado_id and obj.material_id and obj.empregado.empresa_id != obj.material.empresa_id:
                erros.append(
                    f"Levantamento inconsistente: empregado={obj.empregado.nome} "
                    f"(empresa={obj.empregado.empresa_id}) / material={obj.material.nome} "
                    f"(empresa={obj.material.empresa_id})"
                )

            if obj.empresa_id and obj.empregado_id and obj.empresa_id != obj.empregado.empresa_id:
                erros.append(f"Levantamento empresa divergente com empregado: id={obj.pk}")

            if obj.empresa_id and obj.material_id and obj.empresa_id != obj.material.empresa_id:
                erros.append(f"Levantamento empresa divergente com material: id={obj.pk}")

        # 6. DevolucaoMaterial
        for obj in DevolucaoMaterial.objects.select_related("empregado", "material", "projeto", "furo", "empresa"):
            if obj.empregado_id and obj.material_id and obj.empregado.empresa_id != obj.material.empresa_id:
                erros.append(
                    f"Devolução inconsistente: empregado={obj.empregado.nome} "
                    f"(empresa={obj.empregado.empresa_id}) / material={obj.material.nome} "
                    f"(empresa={obj.material.empresa_id})"
                )

            if obj.empresa_id and obj.empregado_id and obj.empresa_id != obj.empregado.empresa_id:
                erros.append(f"Devolução empresa divergente com empregado: id={obj.pk}")

            if obj.empresa_id and obj.material_id and obj.empresa_id != obj.material.empresa_id:
                erros.append(f"Devolução empresa divergente com material: id={obj.pk}")

        # 7. Medicao
        for obj in Medicao.objects.select_related("furo", "empresa"):
            if obj.furo_id and obj.empresa_id != obj.furo.empresa_id:
                erros.append(
                    f"Medição inconsistente: id={obj.pk}, empresa_medicao={obj.empresa_id}, "
                    f"furo={obj.furo.nome}, empresa_furo={obj.furo.empresa_id}"
                )

        # 8. Maquina
        for obj in Maquina.objects.select_related("projeto_atual", "empresa").prefetch_related("projetos", "furos"):
            if obj.projeto_atual_id and obj.projeto_atual.empresa_id != obj.empresa_id:
                erros.append(
                    f"Máquina/projeto_atual inconsistente: maquina={obj.nome}, "
                    f"empresa_maquina={obj.empresa_id}, projeto_atual={obj.projeto_atual.nome}, "
                    f"empresa_projeto={obj.projeto_atual.empresa_id}"
                )

            for projeto in obj.projetos.all():
                if projeto.empresa_id != obj.empresa_id:
                    erros.append(
                        f"Máquina/projetos inconsistente: maquina={obj.nome}, projeto={projeto.nome}"
                    )

            for furo in obj.furos.all():
                if furo.empresa_id != obj.empresa_id:
                    erros.append(
                        f"Máquina/furos inconsistente: maquina={obj.nome}, furo={furo.nome}"
                    )

        # 9. ConfiguracaoPerfuracaoEmpregado
        for obj in ConfiguracaoPerfuracaoEmpregado.objects.select_related("empregado", "furo", "empresa"):
            if obj.empregado_id and obj.furo_id and obj.empregado.empresa_id != obj.furo.empresa_id:
                erros.append(
                    f"Configuração inconsistente: empregado={obj.empregado.nome} / furo={obj.furo.nome}"
                )

            if obj.empresa_id and obj.empregado_id and obj.empresa_id != obj.empregado.empresa_id:
                erros.append(f"Configuração empresa divergente com empregado: id={obj.pk}")

            if obj.empresa_id and obj.furo_id and obj.empresa_id != obj.furo.empresa_id:
                erros.append(f"Configuração empresa divergente com furo: id={obj.pk}")

        # 10. RegistoDiarioEmpregado
        for obj in RegistoDiarioEmpregado.objects.select_related("empregado", "projeto", "furo", "empresa"):
            if obj.empregado_id and obj.empresa_id and obj.empregado.empresa_id != obj.empresa_id:
                erros.append(f"Registo empresa divergente com empregado: id={obj.pk}")

            if obj.projeto_id and obj.empresa_id and obj.projeto.empresa_id != obj.empresa_id:
                erros.append(f"Registo empresa divergente com projeto: id={obj.pk}")

            if obj.furo_id and obj.empresa_id and obj.furo.empresa_id != obj.empresa_id:
                erros.append(f"Registo empresa divergente com furo: id={obj.pk}")

            if obj.furo_id and obj.projeto_id and obj.furo.projeto_id != obj.projeto_id:
                erros.append(f"Registo furo/projeto incoerente: id={obj.pk}")

        # 11. Despesa
        for obj in Despesa.objects.select_related("maquina", "projeto", "furo", "empresa"):
            if obj.maquina_id and obj.empresa_id and obj.maquina.empresa_id != obj.empresa_id:
                erros.append(f"Despesa/máquina inconsistente: id={obj.pk}")

            if obj.projeto_id and obj.empresa_id and obj.projeto.empresa_id != obj.empresa_id:
                erros.append(f"Despesa/projeto inconsistente: id={obj.pk}")

            if obj.furo_id and obj.empresa_id and obj.furo.empresa_id != obj.empresa_id:
                erros.append(f"Despesa/furo inconsistente: id={obj.pk}")

            if obj.furo_id and obj.projeto_id and obj.furo.projeto_id != obj.projeto_id:
                erros.append(f"Despesa furo/projeto incoerente: id={obj.pk}")

        total = len(erros)

        if total == 0:
            self.stdout.write(self.style.SUCCESS("Nenhuma incoerência multiempresa encontrada."))
            return

        self.stdout.write(self.style.WARNING(f"Total de incoerências encontradas: {total}"))
        for erro in erros:
            self.stdout.write(f"- {erro}")