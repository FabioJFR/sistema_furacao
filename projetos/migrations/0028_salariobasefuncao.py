from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plataforma", "0014_configuracaopagamentoplataforma"),
        ("projetos", "0027_projeto_outros_valores_gastos_associados"),
    ]

    operations = [
        migrations.CreateModel(
            name="SalarioBaseFuncao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("funcao", models.CharField(max_length=100)),
                ("salario_base", models.FloatField(default=0.0)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                (
                    "empresa",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="salarios_base_funcoes",
                        to="plataforma.empresa",
                    ),
                ),
            ],
            options={
                "verbose_name": "Salário base por função",
                "verbose_name_plural": "Salários base por função",
                "ordering": ["funcao"],
                "unique_together": {("empresa", "funcao")},
            },
        ),
    ]

