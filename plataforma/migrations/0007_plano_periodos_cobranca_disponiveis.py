from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plataforma", "0006_plano_permite_cobranca_mensal_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="plano",
            name="periodos_cobranca_disponiveis",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
