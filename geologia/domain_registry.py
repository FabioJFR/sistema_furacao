from geologia.models import (
    AnexoLogGeologico,
    ComandoDroneSFOperacao,
    ConfiguracaoDroneSF,
    DroneComandoOperacao,
    DroneOperacaoTempoReal,
    DroneSF,
    LogGeologicoFuro,
    MissaoDroneFuro,
    MissaoProgramadaDroneSF,
    ModuloDroneSF,
    OperacaoDroneSFTempoReal,
    SensorDroneSF,
)


GEOLOGIA_MODEL_MAP = {
    "MissaoDroneFuro": MissaoDroneFuro,
    "DroneOperacaoTempoReal": DroneOperacaoTempoReal,
    "DroneComandoOperacao": DroneComandoOperacao,
    "DroneSF": DroneSF,
    "ModuloDroneSF": ModuloDroneSF,
    "SensorDroneSF": SensorDroneSF,
    "ConfiguracaoDroneSF": ConfiguracaoDroneSF,
    "OperacaoDroneSFTempoReal": OperacaoDroneSFTempoReal,
    "ComandoDroneSFOperacao": ComandoDroneSFOperacao,
    "MissaoProgramadaDroneSF": MissaoProgramadaDroneSF,
    "LogGeologicoFuro": LogGeologicoFuro,
    "AnexoLogGeologico": AnexoLogGeologico,
}

