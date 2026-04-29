# dispositivos/models/__init__.py
# Core
from .dispositivo import Dispositivo
from .sessao_dispositivo import SessaoDispositivo

# Dados
from .leitura_bruta_dispositivo import LeituraBrutaDispositivo
from .leitura_dispositivo import LeituraDispositivo

# Domínio técnico
from .survey_shot import SurveyShot
from .leitura_medicao_link import LeituraDispositivoMedicaoLink
from .importacao_historico import ImportacaoDispositivoHistorico

__all__ = [
    "Dispositivo",
    "SessaoDispositivo",
    "LeituraBrutaDispositivo",
    "LeituraDispositivo",
    "SurveyShot",
    "LeituraDispositivoMedicaoLink",
    "ImportacaoDispositivoHistorico",
]
