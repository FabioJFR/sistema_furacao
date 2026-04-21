from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("plataforma", "0003_alter_perfilplataforma_tipo_acesso"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscricaoempresa",
            name="ciclo_cobranca",
            field=models.CharField(
                choices=[("mensal", "Mensal"), ("anual", "Anual")],
                default="mensal",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="subscricaoempresa",
            name="proxima_renovacao",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="MovimentoFinanceiroPlataforma",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("tipo_movimento", models.CharField(choices=[("cobranca", "Cobrança"), ("pagamento", "Pagamento"), ("ajuste", "Ajuste"), ("reembolso", "Reembolso")], default="cobranca", max_length=20)),
                ("ciclo_cobranca", models.CharField(choices=[("mensal", "Mensal"), ("anual", "Anual"), ("unico", "Único")], default="unico", max_length=20)),
                ("valor", models.DecimalField(decimal_places=2, max_digits=10)),
                ("moeda", models.CharField(default="EUR", max_length=10)),
                ("descricao", models.CharField(blank=True, max_length=255)),
                ("data_competencia", models.DateField(blank=True, null=True)),
                ("data_vencimento", models.DateField(blank=True, null=True)),
                ("data_pagamento", models.DateField(blank=True, null=True)),
                ("estado", models.CharField(choices=[("pendente", "Pendente"), ("pago", "Pago"), ("atrasado", "Atrasado"), ("cancelado", "Cancelado")], default="pendente", max_length=20)),
                ("referencia", models.CharField(blank=True, max_length=100)),
                ("observacoes", models.TextField(blank=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("empresa", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="movimentos_financeiros", to="plataforma.empresa")),
                ("perfil_plataforma", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="movimentos_financeiros", to="plataforma.perfilplataforma")),
                ("plano", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="movimentos_financeiros", to="plataforma.plano")),
                ("subscricao", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="movimentos_financeiros", to="plataforma.subscricaoempresa")),
            ],
            options={
                "verbose_name": "Movimento Financeiro da Plataforma",
                "verbose_name_plural": "Movimentos Financeiros da Plataforma",
                "ordering": ["-criado_em"],
            },
        ),
    ]
