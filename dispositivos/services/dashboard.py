"""
Camada de compatibilidade para serviços de dashboard de dispositivos.

Este módulo mantém os imports antigos estáveis enquanto a implementação
foi dividida por responsabilidade:
- registry: registo/normalização de dispositivos detectados
- capture: criação de sessões e teste de leitura USB
- discovery: escuta/inspeção de dispositivos USB/Bluetooth
"""

from dispositivos.services.dashboard_capture import (
    criar_sessao_dispositivo,
    processar_criacao_sessao_captura,
    processar_teste_leitura_usb,
)
from dispositivos.services.dashboard_discovery import (
    processar_procura_dispositivos_bluetooth,
    processar_escuta_dispositivo_detectado,
    processar_inspecao_bluetooth_detectado,
)
from dispositivos.services.dashboard_registry import (
    guardar_dispositivo_detectado,
    processar_registo_dispositivo_detectado,
    validar_parametros_dispositivo_detectado,
)

__all__ = [
    "criar_sessao_dispositivo",
    "guardar_dispositivo_detectado",
    "processar_criacao_sessao_captura",
    "processar_escuta_dispositivo_detectado",
    "processar_inspecao_bluetooth_detectado",
    "processar_procura_dispositivos_bluetooth",
    "processar_registo_dispositivo_detectado",
    "processar_teste_leitura_usb",
    "validar_parametros_dispositivo_detectado",
]
