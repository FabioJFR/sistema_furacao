import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plataforma", "0017_empresa_geologia_score_config"),
        ("projetos", "0032_planeamentoturno"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssiduidadeRegisto",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("tipo", models.CharField(choices=[("presenca", "Presença"), ("falta", "Falta"), ("ferias", "Férias"), ("baixa", "Baixa"), ("hora_extra", "Hora Extra")], default="presenca", max_length=20)),
                ("estado", models.CharField(choices=[("pendente", "Pendente"), ("aprovado", "Aprovado"), ("rejeitado", "Rejeitado")], default="pendente", max_length=20)),
                ("data_inicio", models.DateField()),
                ("data_fim", models.DateField(blank=True, null=True)),
                ("horas", models.FloatField(default=0.0)),
                ("motivo", models.CharField(blank=True, max_length=220)),
                ("notas", models.TextField(blank=True)),
                ("criado_em", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("empregado", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assiduidades", to="projetos.empregados")),
                ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assiduidades", to="plataforma.empresa")),
                ("projeto", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assiduidades", to="projetos.projeto")),
            ],
            options={
                "verbose_name": "Registo de Assiduidade",
                "verbose_name_plural": "Registos de Assiduidade",
                "ordering": ["-data_inicio", "-atualizado_em"],
            },
        ),
    ]
