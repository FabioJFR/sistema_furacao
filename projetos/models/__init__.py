# ===============================
# CORE (BASE ENTITIES)
# ===============================
from .empresa import Empresa
from .projeto import Projeto
from .furo import Furo

# ===============================
# RECURSOS HUMANOS
# ===============================
from .empregado import (
    Empregados,
    EmpregadoProjeto,
    EmpregadoFicheiro,
)
from .empregado_furo import EmpregadoFuro

# ===============================
# OPERAÇÃO / PRODUÇÃO
# ===============================
from .registo import RegistoDiarioEmpregado
from .registo_foto_amostra import RegistoDiarioFotoAmostra
from .medicao import Medicao

# ===============================
# EQUIPAMENTOS E MATERIAIS
# ===============================
from .maquina import Maquina
from .material import (
    Material,
    LevantamentoMaterial,
    DevolucaoMaterial,
)

# ===============================
# FINANCEIRO
# ===============================
from .despesa import Despesa

# ===============================
# CONFIGURAÇÕES E HISTÓRICO
# ===============================
from .configuracao_perfuracao import ConfiguracaoPerfuracaoEmpregado
from .historico_configuracao import HistoricoConfiguracaoPerfuracao
from .preferencias import PreferenciasUser

# ===============================
# TODO FUTURO:
# - separar por apps (core, operacao, financeiro, rh)
# - adicionar signals centralizados
# - adicionar base model com empresa obrigatória
# ===============================