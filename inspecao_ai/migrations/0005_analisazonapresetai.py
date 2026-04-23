from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("plataforma", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("inspecao_ai", "0004_analiseimagemai_guardada_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="AnaliseZonaPresetAI",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("nome", models.CharField(max_length=120)),
                (
                    "tipo_documento",
                    models.CharField(
                        choices=[
                            ("caixa_cilindrica", "Caixa cilíndrica com testemunho"),
                            ("relatorio_trabalhador", "Relatório manuscrito de trabalhador"),
                        ],
                        default="relatorio_trabalhador",
                        max_length=40,
                    ),
                ),
                ("zona_relatorio", models.JSONField(blank=True, default=dict)),
                ("zonas_texto", models.JSONField(blank=True, default=list)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                (
                    "criado_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="analise_zona_presets_ai_criados",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "empresa",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="analise_zona_presets_ai",
                        to="plataforma.empresa",
                    ),
                ),
            ],
            options={
                "verbose_name": "Preset de zonas AI",
                "verbose_name_plural": "Presets de zonas AI",
                "ordering": ["nome", "-atualizado_em"],
            },
        ),
        migrations.AddConstraint(
            model_name="analisezonapresetai",
            constraint=models.UniqueConstraint(
                fields=("empresa", "tipo_documento", "nome"),
                name="unique_preset_zonas_ai_empresa_tipo_nome",
            ),
        ),
    ]
