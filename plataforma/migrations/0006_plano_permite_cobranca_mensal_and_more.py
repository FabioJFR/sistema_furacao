from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plataforma", "0005_subscricaoempresa_renovacao_definida_manualmente"),
    ]

    operations = [
        migrations.AddField(
            model_name="plano",
            name="permite_cobranca_anual",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="plano",
            name="permite_cobranca_mensal",
            field=models.BooleanField(default=True),
        ),
    ]
