from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations, models


def migrar_medida_morta_para_configuracao(apps, schema_editor):
    Configuracao = apps.get_model("projetos", "ConfiguracaoPerfuracaoEmpregado")
    Historico = apps.get_model("projetos", "HistoricoConfiguracaoPerfuracao")
    Furo = apps.get_model("projetos", "Furo")

    medidas_por_furo = dict(Furo.objects.values_list("id", "medida_morta"))
    for configuracao in Configuracao.objects.all().only("id", "furo_id"):
        medida = medidas_por_furo.get(configuracao.furo_id, 0.0) or 0.0
        Configuracao.objects.filter(pk=configuracao.pk).update(medida_morta=medida)

    historicos = Historico.objects.filter(furo_id__isnull=False)
    for historico in historicos.only("id", "furo_id"):
        medida = medidas_por_furo.get(historico.furo_id)
        if medida is None:
            continue
        Historico.objects.filter(pk=historico.pk).update(
            medida_morta=Decimal(str(medida)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )


class Migration(migrations.Migration):
    dependencies = [
        ("projetos", "0073_furo_medida_morta"),
    ]

    operations = [
        migrations.AddField(
            model_name="configuracaoperfuracaoempregado",
            name="medida_morta",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="historicoconfiguracaoperfuracao",
            name="medida_morta",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.RunPython(migrar_medida_morta_para_configuracao, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="furo",
            name="medida_morta",
        ),
    ]
