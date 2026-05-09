from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plataforma", "0017_empresa_geologia_score_config"),
    ]

    operations = [
        migrations.AddField(
            model_name="empresa",
            name="compliance_score_config",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
