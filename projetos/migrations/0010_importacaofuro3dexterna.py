from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("projetos", "0009_remove_individual_nib"),
    ]

    operations = [
        migrations.CreateModel(
            name="ImportacaoFuro3DExterna",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("nome", models.CharField(max_length=200)),
                ("origem_aplicacao", models.CharField(blank=True, max_length=200)),
                ("origem_registo", models.CharField(choices=[("externa", "Carregado de outra aplicação"), ("interna", "Criado internamente")], default="externa", max_length=20)),
                ("formato_arquivo", models.CharField(blank=True, max_length=20)),
                ("payload_json", models.JSONField(blank=True, default=dict)),
                ("observacoes", models.TextField(blank=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="importacoes_furo_3d", to="plataforma.empresa")),
                ("furo", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="importacoes_externas_3d", to="projetos.furo")),
            ],
            options={
                "verbose_name": "Importação 3D Externa",
                "verbose_name_plural": "Importações 3D Externas",
                "ordering": ["-criado_em"],
            },
        ),
    ]
