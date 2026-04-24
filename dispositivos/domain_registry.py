from dispositivos.models import (
    Dispositivo,
    LeituraBrutaDispositivo,
    LeituraDispositivo,
    LeituraDispositivoMedicaoLink,
    SessaoDispositivo,
    SurveyShot,
)


DISPOSITIVOS_MODEL_MAP = {
    "Dispositivo": Dispositivo,
    "SessaoDispositivo": SessaoDispositivo,
    "LeituraBrutaDispositivo": LeituraBrutaDispositivo,
    "LeituraDispositivo": LeituraDispositivo,
    "SurveyShot": SurveyShot,
    "LeituraDispositivoMedicaoLink": LeituraDispositivoMedicaoLink,
}

