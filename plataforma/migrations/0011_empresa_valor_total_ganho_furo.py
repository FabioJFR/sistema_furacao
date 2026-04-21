from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("plataforma", "0010_empresa_indicadores_financeiros"),
    ]

    operations = [
        migrations.AddField(
            model_name="empresa",
            name="valor_total_ganho_furo",
            field=models.FloatField(default=0.0),
        ),
    ]
