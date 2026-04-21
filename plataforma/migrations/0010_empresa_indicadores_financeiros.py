from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("plataforma", "0009_alter_movimentofinanceiroplataforma_categoria_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="empresa",
            name="custo_por_metro_cliente",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="empresa",
            name="custo_por_metro_empresa",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="empresa",
            name="outros_valores_gastos_associados",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="empresa",
            name="valor_total_cobrado_cliente",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="empresa",
            name="valor_total_gasto_furo",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="empresa",
            name="valor_total_gasto_maquinas",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="empresa",
            name="valor_total_gasto_materias",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="empresa",
            name="valor_total_gasto_projeto",
            field=models.FloatField(default=0.0),
        ),
    ]
