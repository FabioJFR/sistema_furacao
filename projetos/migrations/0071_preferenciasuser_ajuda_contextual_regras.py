from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projetos", "0070_preferenciasuser_ajuda_contextual_ativa"),
    ]

    operations = [
        migrations.AddField(
            model_name="preferenciasuser",
            name="ajuda_contextual_apenas_paginas_novas",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="preferenciasuser",
            name="ajuda_contextual_apenas_utilizadores_recentes",
            field=models.BooleanField(default=False),
        ),
    ]
