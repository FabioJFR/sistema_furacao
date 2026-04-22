from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("plataforma", "0011_empresa_valor_total_ganho_furo"),
        ("geologia", "0004_droneoperacaotemporeal_bridge_api_key_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="DroneSF",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("nome", models.CharField(max_length=140)),
                ("codigo", models.CharField(blank=True, max_length=80)),
                ("status", models.CharField(choices=[("planeamento", "Planeamento"), ("montagem", "Montagem"), ("teste", "Teste"), ("operacional", "Operacional"), ("manutencao", "Manutenção"), ("inativo", "Inativo")], default="planeamento", max_length=20)),
                ("frame_modelo", models.CharField(blank=True, max_length=120)),
                ("controlador_voo", models.CharField(blank=True, max_length=120)),
                ("firmware_voo", models.CharField(blank=True, max_length=120)),
                ("protocolo_telemetria", models.CharField(blank=True, default="MAVLink", max_length=80)),
                ("companion_computer", models.CharField(blank=True, max_length=120)),
                ("autonomia_alvo_min", models.PositiveIntegerField(default=0)),
                ("payload_alvo_kg", models.FloatField(default=0.0)),
                ("peso_estimado_kg", models.FloatField(default=0.0)),
                ("tensao_sistema_v", models.FloatField(blank=True, null=True)),
                ("observacoes", models.TextField(blank=True)),
                ("metadados", models.JSONField(blank=True, default=dict)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="drones_sf", to="plataforma.empresa")),
            ],
            options={
                "verbose_name": "Drone S_F",
                "verbose_name_plural": "Drones S_F",
                "ordering": ["nome", "criado_em"],
            },
        ),
        migrations.CreateModel(
            name="ConfiguracaoDroneSF",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("telemetria_ativa", models.BooleanField(default=False)),
                ("video_ativo", models.BooleanField(default=False)),
                ("missao_automatica_ativa", models.BooleanField(default=False)),
                ("sensores_proximidade_ativos", models.BooleanField(default=False)),
                ("sensores_som_ativos", models.BooleanField(default=False)),
                ("software_embarcado_ativo", models.BooleanField(default=False)),
                ("endpoint_bridge", models.URLField(blank=True)),
                ("api_key_bridge", models.CharField(blank=True, max_length=120)),
                ("versao_software_embarcado", models.CharField(blank=True, max_length=120)),
                ("observacoes", models.TextField(blank=True)),
                ("metadados", models.JSONField(blank=True, default=dict)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("drone", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="configuracao", to="geologia.dronesf")),
                ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="configuracoes_drone_sf", to="plataforma.empresa")),
            ],
            options={
                "verbose_name": "Configuração do Drone S_F",
                "verbose_name_plural": "Configurações do Drone S_F",
            },
        ),
        migrations.CreateModel(
            name="ModuloDroneSF",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("nome", models.CharField(max_length=140)),
                ("tipo", models.CharField(choices=[("estrutura", "Estrutura"), ("propulsao", "Propulsão"), ("energia", "Energia"), ("controlo_voo", "Controlo de voo"), ("computacao", "Computação embarcada"), ("camera", "Câmara"), ("comunicacao", "Comunicação"), ("seguranca", "Segurança"), ("outro", "Outro")], default="outro", max_length=20)),
                ("fabricante", models.CharField(blank=True, max_length=120)),
                ("modelo", models.CharField(blank=True, max_length=120)),
                ("numero_serie", models.CharField(blank=True, max_length=120)),
                ("firmware", models.CharField(blank=True, max_length=120)),
                ("peso_kg", models.FloatField(default=0.0)),
                ("consumo_estimado_w", models.FloatField(default=0.0)),
                ("status", models.CharField(choices=[("planeado", "Planeado"), ("instalado", "Instalado"), ("teste", "Em teste"), ("ativo", "Ativo"), ("avariado", "Avariado"), ("substituido", "Substituído")], default="planeado", max_length=20)),
                ("removivel", models.BooleanField(default=True)),
                ("observacoes", models.TextField(blank=True)),
                ("metadados", models.JSONField(blank=True, default=dict)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("drone", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="modulos", to="geologia.dronesf")),
                ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="modulos_drone_sf", to="plataforma.empresa")),
            ],
            options={
                "verbose_name": "Módulo do Drone S_F",
                "verbose_name_plural": "Módulos do Drone S_F",
                "ordering": ["tipo", "nome"],
            },
        ),
        migrations.CreateModel(
            name="SensorDroneSF",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("nome", models.CharField(max_length=140)),
                ("tipo", models.CharField(choices=[("proximidade", "Proximidade"), ("som", "Som"), ("rgb", "RGB"), ("termico", "Térmico"), ("multiespectral", "Multiespectral"), ("lidar", "LiDAR"), ("ambiental", "Ambiental"), ("geologico", "Geológico"), ("outro", "Outro")], default="outro", max_length=20)),
                ("fabricante", models.CharField(blank=True, max_length=120)),
                ("modelo", models.CharField(blank=True, max_length=120)),
                ("interface_ligacao", models.CharField(blank=True, max_length=80)),
                ("alcance_m", models.FloatField(blank=True, null=True)),
                ("taxa_amostragem_hz", models.FloatField(blank=True, null=True)),
                ("status", models.CharField(choices=[("planeado", "Planeado"), ("instalado", "Instalado"), ("calibracao", "Calibração"), ("ativo", "Ativo"), ("avariado", "Avariado"), ("substituido", "Substituído")], default="planeado", max_length=20)),
                ("calibrado", models.BooleanField(default=False)),
                ("observacoes", models.TextField(blank=True)),
                ("metadados", models.JSONField(blank=True, default=dict)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("drone", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sensores", to="geologia.dronesf")),
                ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sensores_drone_sf", to="plataforma.empresa")),
                ("modulo", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sensores", to="geologia.modulodronesf")),
            ],
            options={
                "verbose_name": "Sensor do Drone S_F",
                "verbose_name_plural": "Sensores do Drone S_F",
                "ordering": ["tipo", "nome"],
            },
        ),
        migrations.AddConstraint(
            model_name="dronesf",
            constraint=models.UniqueConstraint(fields=("empresa", "nome"), name="unique_drone_sf_nome_empresa"),
        ),
    ]
