from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("projetos", "0072_configuracao_perfuracao_por_furo"),
    ]

    operations = [
        migrations.AddField(
            model_name="furo",
            name="medida_morta",
            field=models.FloatField(default=0.0),
        ),
    ]
