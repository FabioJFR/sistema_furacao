from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("projetos", "0010_importacaofuro3dexterna"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FuroVersao",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("versao_numero", models.PositiveIntegerField()),
                ("origem", models.CharField(choices=[("criado", "Criado"), ("atualizado", "Atualizado"), ("medicao", "Medição"), ("recalculo", "Recalculo"), ("migracao", "Migração")], default="atualizado", max_length=20)),
                ("hash_estado", models.CharField(max_length=64)),
                ("dados_snapshot", models.JSONField(blank=True, default=dict)),
                ("observacoes", models.TextField(blank=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("criado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="furos_versoes_criadas", to=settings.AUTH_USER_MODEL)),
                ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="furos_versoes", to="plataforma.empresa")),
                ("furo", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="versoes", to="projetos.furo")),
                ("projeto", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="versoes_furos", to="projetos.projeto")),
            ],
            options={
                "verbose_name": "Versão de furo",
                "verbose_name_plural": "Versões de furo",
                "ordering": ["-criado_em", "-versao_numero"],
            },
        ),
        migrations.AddConstraint(
            model_name="furoversao",
            constraint=models.UniqueConstraint(fields=("furo", "versao_numero"), name="unique_furo_versao_numero"),
        ),
        migrations.AddIndex(
            model_name="furoversao",
            index=models.Index(fields=["empresa", "furo", "-criado_em"], name="idx_furo_versao_tempo"),
        ),
        migrations.AddIndex(
            model_name="furoversao",
            index=models.Index(fields=["origem"], name="idx_furo_versao_origem"),
        ),
    ]

