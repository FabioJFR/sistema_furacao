from django.db import migrations
from django.db.models import Count


def consolidar_configuracoes_por_furo(apps, schema_editor):
    Configuracao = apps.get_model("projetos", "ConfiguracaoPerfuracaoEmpregado")
    Historico = apps.get_model("projetos", "HistoricoConfiguracaoPerfuracao")

    furo_ids_duplicados = (
        Configuracao.objects
        .values("furo_id")
        .annotate(total=Count("id"))
        .filter(total__gt=1)
        .values_list("furo_id", flat=True)
    )

    for furo_id in furo_ids_duplicados:
        configuracoes = list(
            Configuracao.objects
            .filter(furo_id=furo_id)
            .order_by("-atualizado_em", "-id")
        )
        configuracao_mantida = configuracoes[0]
        configuracoes_removidas = configuracoes[1:]

        for configuracao in configuracoes_removidas:
            Historico.objects.filter(configuracao_id=configuracao.id).update(
                configuracao_id=configuracao_mantida.id
            )
            configuracao.delete()


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("projetos", "0071_preferenciasuser_ajuda_contextual_regras"),
    ]

    operations = [
        migrations.RunPython(consolidar_configuracoes_por_furo, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name="configuracaoperfuracaoempregado",
            unique_together={("furo",)},
        ),
        migrations.AlterModelOptions(
            name="configuracaoperfuracaoempregado",
            options={
                "ordering": ["furo__nome"],
                "verbose_name": "Configuração de Perfuração do Furo",
                "verbose_name_plural": "Configurações de Perfuração dos Furos",
            },
        ),
    ]
