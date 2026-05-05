from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projetos", "0026_projeto_custo_por_metro_cliente_override"),
    ]

    operations = [
        migrations.AddField(
            model_name="projeto",
            name="outros_valores_gastos_associados",
            field=models.FloatField(
                default=0.0,
                help_text="Outros custos associados especificamente a este projeto.",
            ),
        ),
    ]

