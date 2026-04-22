from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("plataforma", "0011_empresa_valor_total_ganho_furo"),
        ("geologia", "0005_dronesf_configuracaodronesf_modulodronesf_and_more"),
        migrations.swappable_dependency("auth.User"),
    ]

    operations = [
        migrations.CreateModel(
            name="OperacaoDroneSFTempoReal",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("estado", models.CharField(choices=[("desligado", "Desligado"), ("pronto", "Pronto"), ("em_voo", "Em voo"), ("em_missao", "Em missão"), ("manutencao", "Em manutenção"), ("erro", "Erro")], default="desligado", max_length=20)),
                ("bridge_ativa", models.BooleanField(default=False)),
                ("bridge_nome", models.CharField(blank=True, default="Bridge S_F", max_length=120)),
                ("bridge_base_url", models.URLField(blank=True)),
                ("bridge_api_key", models.CharField(blank=True, max_length=120)),
                ("bridge_ultimo_estado", models.CharField(blank=True, max_length=120)),
                ("bridge_ultimo_erro", models.TextField(blank=True)),
                ("live_view_url", models.URLField(blank=True)),
                ("frame_snapshot_url", models.URLField(blank=True)),
                ("latitude_atual", models.FloatField(blank=True, null=True)),
                ("longitude_atual", models.FloatField(blank=True, null=True)),
                ("altitude_atual_m", models.FloatField(blank=True, null=True)),
                ("velocidade_atual_ms", models.FloatField(blank=True, null=True)),
                ("heading_graus", models.FloatField(blank=True, null=True)),
                ("bateria_percent", models.PositiveIntegerField(blank=True, null=True)),
                ("sinal_percent", models.PositiveIntegerField(blank=True, null=True)),
                ("gravacao_ativa", models.BooleanField(default=False)),
                ("alvo_latitude", models.FloatField(blank=True, null=True)),
                ("alvo_longitude", models.FloatField(blank=True, null=True)),
                ("alvo_altitude_m", models.FloatField(default=35.0)),
                ("ultimo_heartbeat", models.DateTimeField(blank=True, null=True)),
                ("observacoes", models.TextField(blank=True)),
                ("metadados", models.JSONField(blank=True, default=dict)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("drone", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="operacao_tempo_real", to="geologia.dronesf")),
                ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="operacoes_drone_sf_tempo_real", to="plataforma.empresa")),
            ],
            options={
                "verbose_name": "Operação em tempo real do Drone S_F",
                "verbose_name_plural": "Operações em tempo real do Drone S_F",
                "ordering": ["-atualizado_em", "-criado_em"],
            },
        ),
        migrations.CreateModel(
            name="ComandoDroneSFOperacao",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("tipo_comando", models.CharField(choices=[("goto", "Ir para ponto"), ("capturar_foto", "Capturar foto"), ("iniciar_video", "Iniciar vídeo"), ("parar_video", "Parar vídeo"), ("pairar", "Pairar"), ("rth", "Return to home")], max_length=30)),
                ("status", models.CharField(choices=[("pendente", "Pendente"), ("enviado", "Enviado"), ("executado", "Executado"), ("erro", "Erro"), ("cancelado", "Cancelado")], default="pendente", max_length=20)),
                ("latitude_alvo", models.FloatField(blank=True, null=True)),
                ("longitude_alvo", models.FloatField(blank=True, null=True)),
                ("altitude_alvo_m", models.FloatField(blank=True, null=True)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("resposta_execucao", models.TextField(blank=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("criado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="comandos_drone_sf", to="auth.user")),
                ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comandos_drone_sf", to="plataforma.empresa")),
                ("operacao", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comandos", to="geologia.operacaodronesftemporeal")),
            ],
            options={
                "verbose_name": "Comando do Drone S_F",
                "verbose_name_plural": "Comandos do Drone S_F",
                "ordering": ["-criado_em"],
            },
        ),
    ]
