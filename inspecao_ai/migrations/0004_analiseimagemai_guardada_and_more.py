from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inspecao_ai", "0003_analiseimagemai_campos_extraidos"),
    ]

    operations = [
        migrations.AddField(
            model_name="analiseimagemai",
            name="guardada",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="deteccaoimagemai",
            name="texto_sugerido",
            field=models.TextField(blank=True),
        ),
    ]
