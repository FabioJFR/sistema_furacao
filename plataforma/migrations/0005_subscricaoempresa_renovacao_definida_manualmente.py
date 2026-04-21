from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plataforma", "0004_movimentofinanceiroplataforma_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscricaoempresa",
            name="renovacao_definida_manualmente",
            field=models.BooleanField(default=False),
        ),
    ]
