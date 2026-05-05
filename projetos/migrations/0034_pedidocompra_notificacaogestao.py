import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plataforma", "0017_empresa_geologia_score_config"),
        ("projetos", "0033_assiduidaderegisto"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificacaoGestao",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("titulo", models.CharField(max_length=220)),
                ("tipo", models.CharField(blank=True, max_length=80)),
                ("prioridade", models.CharField(choices=[("baixa", "Baixa"), ("media", "Média"), ("alta", "Alta")], default="media", max_length=10)),
                ("estado", models.CharField(choices=[("aberta", "Aberta"), ("em_andamento", "Em andamento"), ("resolvida", "Resolvida")], default="aberta", max_length=20)),
                ("prazo", models.DateTimeField(blank=True, null=True)),
                ("origem_url", models.CharField(blank=True, max_length=255)),
                ("detalhes", models.TextField(blank=True)),
                ("criado_em", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notificacoes_gestao", to="plataforma.empresa")),
                ("responsavel", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="notificacoes_gestao", to="projetos.empregados")),
            ],
            options={
                "verbose_name": "Notificação de gestão",
                "verbose_name_plural": "Notificações de gestão",
                "ordering": ["estado", "-criado_em"],
            },
        ),
        migrations.CreateModel(
            name="PedidoCompra",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("descricao", models.CharField(max_length=220)),
                ("categoria", models.CharField(blank=True, max_length=80)),
                ("fornecedor_sugerido", models.CharField(blank=True, max_length=160)),
                ("valor_estimado", models.FloatField(default=0.0)),
                ("prioridade", models.CharField(choices=[("baixa", "Baixa"), ("media", "Média"), ("alta", "Alta")], default="media", max_length=10)),
                ("estado", models.CharField(choices=[("pendente", "Pendente"), ("aprovado", "Aprovado"), ("rejeitado", "Rejeitado")], default="pendente", max_length=12)),
                ("data_necessidade", models.DateField(blank=True, null=True)),
                ("observacoes", models.TextField(blank=True)),
                ("aprovado_em", models.DateTimeField(blank=True, null=True)),
                ("criado_em", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pedidos_compra", to="plataforma.empresa")),
                ("projeto", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pedidos_compra", to="projetos.projeto")),
                ("solicitado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pedidos_compra_solicitados", to="projetos.empregados")),
            ],
            options={
                "verbose_name": "Pedido de compra",
                "verbose_name_plural": "Pedidos de compra",
                "ordering": ["-criado_em"],
            },
        ),
    ]
