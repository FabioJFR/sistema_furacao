from django.core.management.base import BaseCommand, CommandError

from geologia.models import (
    ComandoDroneSFOperacao,
    ConfiguracaoDroneSF,
    DroneSF,
    ModuloDroneSF,
    OperacaoDroneSFTempoReal,
    SensorDroneSF,
)
from plataforma.models import Empresa


class Command(BaseCommand):
    help = "Cria um Drone S_F demo com módulos, sensores, configuração base e operação em tempo real."

    def add_arguments(self, parser):
        parser.add_argument("--empresa", default="", help="Nome da empresa onde o Drone S_F demo deve ser criado.")
        parser.add_argument("--nome", default="Drone S_F Demo", help="Nome do drone demo.")
        parser.add_argument("--codigo", default="SF-DEMO-001", help="Código técnico do drone demo.")
        parser.add_argument(
            "--bridge-key",
            default="bridge-drone-sf-local-001",
            help="Chave da bridge S_F a configurar na operação demo.",
        )
        parser.add_argument(
            "--bridge-url",
            default="http://127.0.0.1:8890",
            help="URL base da bridge S_F a configurar na operação demo.",
        )

    def handle(self, *args, **options):
        empresa = self._resolver_empresa(options["empresa"].strip())
        nome = options["nome"].strip() or "Drone S_F Demo"
        codigo = options["codigo"].strip() or "SF-DEMO-001"
        bridge_key = options["bridge_key"].strip() or "bridge-drone-sf-local-001"
        bridge_url = options["bridge_url"].strip() or "http://127.0.0.1:8890"

        drone, drone_created = DroneSF.objects.get_or_create(
            empresa=empresa,
            nome=nome,
            defaults={
                "codigo": codigo,
                "status": "teste",
                "frame_modelo": "Quadcopter S_F 650",
                "controlador_voo": "Pixhawk / ArduPilot",
                "firmware_voo": "ArduPilot",
                "protocolo_telemetria": "MAVLink",
                "companion_computer": "Raspberry Pi 5",
                "autonomia_alvo_min": 35,
                "payload_alvo_kg": 1.2,
                "peso_estimado_kg": 4.8,
                "tensao_sistema_v": 22.2,
                "observacoes": "Drone S_F demo criado automaticamente para testes da interface, sensores e bridge própria.",
            },
        )
        if not drone_created:
            drone.codigo = codigo
            drone.status = drone.status or "teste"
            drone.frame_modelo = drone.frame_modelo or "Quadcopter S_F 650"
            drone.controlador_voo = drone.controlador_voo or "Pixhawk / ArduPilot"
            drone.firmware_voo = drone.firmware_voo or "ArduPilot"
            drone.protocolo_telemetria = drone.protocolo_telemetria or "MAVLink"
            drone.companion_computer = drone.companion_computer or "Raspberry Pi 5"
            drone.autonomia_alvo_min = drone.autonomia_alvo_min or 35
            drone.payload_alvo_kg = drone.payload_alvo_kg or 1.2
            drone.peso_estimado_kg = drone.peso_estimado_kg or 4.8
            if drone.tensao_sistema_v in (None, 0):
                drone.tensao_sistema_v = 22.2
            if not drone.observacoes:
                drone.observacoes = "Drone S_F demo criado automaticamente para testes da interface, sensores e bridge própria."
            drone.save()

        modulos = {}
        for payload in [
            {
                "nome": "Frame principal S_F",
                "tipo": "estrutura",
                "fabricante": "S_F Lab",
                "modelo": "SF-Frame-650",
                "firmware": "",
                "peso_kg": 1.35,
                "consumo_estimado_w": 0.0,
                "status": "ativo",
                "removivel": False,
                "observacoes": "Estrutura base do drone próprio.",
            },
            {
                "nome": "Controlador de voo",
                "tipo": "controlo_voo",
                "fabricante": "Pixhawk",
                "modelo": "Pixhawk 6C",
                "firmware": "ArduPilot",
                "peso_kg": 0.12,
                "consumo_estimado_w": 8.0,
                "status": "ativo",
                "removivel": True,
                "observacoes": "Camada de controlo de voo aberta para integração com a plataforma.",
            },
            {
                "nome": "Companion computer",
                "tipo": "computacao",
                "fabricante": "Raspberry Pi",
                "modelo": "Pi 5",
                "firmware": "Ubuntu / Python runtime",
                "peso_kg": 0.09,
                "consumo_estimado_w": 18.0,
                "status": "ativo",
                "removivel": True,
                "observacoes": "Execução de software embarcado, bridge e sensores.",
            },
            {
                "nome": "Módulo de comunicação",
                "tipo": "comunicacao",
                "fabricante": "S_F Link",
                "modelo": "SF-Link-01",
                "firmware": "Bridge runtime",
                "peso_kg": 0.08,
                "consumo_estimado_w": 7.5,
                "status": "ativo",
                "removivel": True,
                "observacoes": "Ligação entre o drone, a bridge S_F e a plataforma.",
            },
            {
                "nome": "Câmara principal",
                "tipo": "camera",
                "fabricante": "S_F Vision",
                "modelo": "RGB-4K-Gimbal",
                "firmware": "Cam stack 1.0",
                "peso_kg": 0.28,
                "consumo_estimado_w": 12.0,
                "status": "ativo",
                "removivel": True,
                "observacoes": "Captura visual para geologia, inspeção e fotogrametria.",
            },
        ]:
            modulo, _ = ModuloDroneSF.objects.get_or_create(
                drone=drone,
                nome=payload["nome"],
                defaults={**payload, "empresa": empresa},
            )
            modulos[payload["nome"]] = modulo

        for payload in [
            {
                "nome": "Sensor frontal de proximidade",
                "tipo": "proximidade",
                "modulo": modulos.get("Módulo de comunicação"),
                "fabricante": "S_F Sense",
                "modelo": "PROX-01",
                "interface_ligacao": "UART/I2C",
                "alcance_m": 25.0,
                "taxa_amostragem_hz": 15.0,
                "status": "ativo",
                "calibrado": True,
                "observacoes": "Evitar colisões e apoiar missões automáticas.",
            },
            {
                "nome": "Matriz de som ambiente",
                "tipo": "som",
                "modulo": modulos.get("Companion computer"),
                "fabricante": "S_F Sense",
                "modelo": "AUD-01",
                "interface_ligacao": "USB",
                "alcance_m": 40.0,
                "taxa_amostragem_hz": 44.1,
                "status": "ativo",
                "calibrado": True,
                "observacoes": "Captação de som e futura análise AI.",
            },
            {
                "nome": "Sensor RGB geológico",
                "tipo": "rgb",
                "modulo": modulos.get("Câmara principal"),
                "fabricante": "S_F Vision",
                "modelo": "RGB-4K-Sensor",
                "interface_ligacao": "CSI",
                "alcance_m": 120.0,
                "taxa_amostragem_hz": 30.0,
                "status": "ativo",
                "calibrado": True,
                "observacoes": "Captura principal para geologia e ortomosaico.",
            },
        ]:
            SensorDroneSF.objects.get_or_create(
                drone=drone,
                nome=payload["nome"],
                defaults={**payload, "empresa": empresa},
            )

        configuracao, _ = ConfiguracaoDroneSF.objects.get_or_create(
            drone=drone,
            defaults={
                "empresa": empresa,
                "telemetria_ativa": True,
                "video_ativo": True,
                "missao_automatica_ativa": True,
                "sensores_proximidade_ativos": True,
                "sensores_som_ativos": True,
                "software_embarcado_ativo": True,
                "endpoint_bridge": bridge_url,
                "api_key_bridge": bridge_key,
                "versao_software_embarcado": "sf-runtime-demo-1.0",
                "observacoes": "Configuração base do Drone S_F demo.",
            },
        )
        configuracao.telemetria_ativa = True
        configuracao.video_ativo = True
        configuracao.missao_automatica_ativa = True
        configuracao.sensores_proximidade_ativos = True
        configuracao.sensores_som_ativos = True
        configuracao.software_embarcado_ativo = True
        configuracao.endpoint_bridge = bridge_url
        configuracao.api_key_bridge = bridge_key
        configuracao.versao_software_embarcado = configuracao.versao_software_embarcado or "sf-runtime-demo-1.0"
        if not configuracao.observacoes:
            configuracao.observacoes = "Configuração base do Drone S_F demo."
        configuracao.save()

        operacao, _ = OperacaoDroneSFTempoReal.objects.get_or_create(
            drone=drone,
            defaults={
                "empresa": empresa,
                "estado": "pronto",
                "bridge_ativa": True,
                "bridge_nome": "Bridge S_F",
                "bridge_base_url": bridge_url,
                "bridge_api_key": bridge_key,
                "bridge_ultimo_estado": "ready",
                "latitude_atual": 40.210500,
                "longitude_atual": -8.430100,
                "altitude_atual_m": 0.0,
                "velocidade_atual_ms": 0.0,
                "heading_graus": 0.0,
                "bateria_percent": 95,
                "sinal_percent": 90,
                "gravacao_ativa": False,
                "alvo_latitude": 40.210500,
                "alvo_longitude": -8.430100,
                "alvo_altitude_m": 35.0,
                "observacoes": "Operação demo preparada para a bridge S_F.",
            },
        )
        operacao.estado = operacao.estado or "pronto"
        operacao.bridge_ativa = True
        operacao.bridge_nome = operacao.bridge_nome or "Bridge S_F"
        operacao.bridge_base_url = bridge_url
        operacao.bridge_api_key = bridge_key
        operacao.bridge_ultimo_estado = operacao.bridge_ultimo_estado or "ready"
        if operacao.latitude_atual is None:
            operacao.latitude_atual = 40.210500
        if operacao.longitude_atual is None:
            operacao.longitude_atual = -8.430100
        if operacao.altitude_atual_m is None:
            operacao.altitude_atual_m = 0.0
        if operacao.velocidade_atual_ms is None:
            operacao.velocidade_atual_ms = 0.0
        if operacao.heading_graus is None:
            operacao.heading_graus = 0.0
        if operacao.bateria_percent is None:
            operacao.bateria_percent = 95
        if operacao.sinal_percent is None:
            operacao.sinal_percent = 90
        if operacao.alvo_latitude is None:
            operacao.alvo_latitude = 40.210500
        if operacao.alvo_longitude is None:
            operacao.alvo_longitude = -8.430100
        operacao.alvo_altitude_m = operacao.alvo_altitude_m or 35.0
        if not operacao.observacoes:
            operacao.observacoes = "Operação demo preparada para a bridge S_F."
        operacao.save()

        ComandoDroneSFOperacao.objects.get_or_create(
            operacao=operacao,
            tipo_comando="goto",
            latitude_alvo=operacao.alvo_latitude,
            longitude_alvo=operacao.alvo_longitude,
            altitude_alvo_m=operacao.alvo_altitude_m,
            defaults={
                "empresa": empresa,
                "status": "pendente",
                "payload": {
                    "origem": "seed_drone_sf_demo",
                    "descricao": "Comando demo inicial para validar a fila do Drone S_F.",
                },
            },
        )

        self.stdout.write(self.style.SUCCESS("Drone S_F demo preparado com sucesso."))
        self.stdout.write(f"Empresa: {empresa}")
        self.stdout.write(f"Drone:   {drone.nome}")
        self.stdout.write(f"Código:  {drone.codigo}")
        self.stdout.write(f"Bridge:  {bridge_url}")
        self.stdout.write(f"Key:     {bridge_key}")

    def _resolver_empresa(self, nome_empresa):
        if nome_empresa:
            empresa = Empresa.objects.filter(nome__iexact=nome_empresa).first()
            if empresa is None:
                raise CommandError(f"Empresa não encontrada: {nome_empresa}")
            return empresa

        empresa = Empresa.objects.order_by("nome").first()
        if empresa is None:
            raise CommandError("Não existe nenhuma empresa para associar ao Drone S_F demo.")
        return empresa
