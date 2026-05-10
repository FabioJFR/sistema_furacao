from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projetos", "0069_alter_registodiarioempregado_bit_novo"),
    ]

    operations = [
        migrations.AddField(
            model_name="preferenciasuser",
            name="ajuda_contextual_ativa",
            field=models.BooleanField(default=True),
        ),
    ]
