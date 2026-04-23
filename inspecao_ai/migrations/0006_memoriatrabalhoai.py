from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("plataforma", "0001_initial"),
        ("inspecao_ai", "0005_analisazonapresetai"),
    ]

    operations = [
        migrations.CreateModel(
            name="MemoriaTrabalhoAI",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "area",
                    models.CharField(
                        choices=[
                            ("ocr_relatorios", "OCR relatórios"),
                            ("ocr_caixas", "OCR caixas"),
                            ("chatbox", "Chatbox"),
                            ("memoria_operacional", "Memória operacional"),
                            ("geral", "Geral"),
                        ],
                        default="geral",
                        max_length=40,
                    ),
                ),
                (
                    "estado",
                    models.CharField(
                        choices=[("ativo", "Ativo"), ("standby", "Standby"), ("concluido", "Concluído")],
                        default="ativo",
                        max_length=20,
                    ),
                ),
                ("titulo", models.CharField(max_length=180)),
                ("resumo", models.TextField()),
                ("detalhes", models.JSONField(blank=True, default=dict)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                (
                    "criado_por",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="memorias_trabalho_ai_criadas",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "empresa",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memorias_trabalho_ai",
                        to="plataforma.empresa",
                    ),
                ),
            ],
            options={
                "verbose_name": "Memória de trabalho AI",
                "verbose_name_plural": "Memórias de trabalho AI",
                "ordering": ["-atualizado_em", "-criado_em"],
            },
        ),
    ]
