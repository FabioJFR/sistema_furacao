# ===============================
# CORE (BASE ENTITIES)
# ===============================
from .empresa import Empresa
from .projeto import Projeto
from .furo import Furo
from .furo_versao import FuroVersao

# ===============================
# RECURSOS HUMANOS
# ===============================
from .empregado import (
    Empregados,
    EmpregadoProjeto,
    EmpregadoFicheiro,
)
from .individual import Individual
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
from .maquina_historico import MaquinaAvaria, MaquinaEventoOperacional
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
from .evento_analytics import EventoAnalytics
from .importacao_furo_3d import ImportacaoFuro3DExterna
from .modelo_3d_wireframe import Modelo3DWireframe
from .modelo_3d_block import Modelo3DBlock
from .block_model_cell import BlockModelCell
from .modelo_3d_implicit import Modelo3DImplicit
from .sugestao import SugestaoPlataforma
from .salario_base_funcao import SalarioBaseFuncao
from .cliente_contrato import ClienteContrato
from .planeamento_turno import PlaneamentoTurno
from .assiduidade_registo import AssiduidadeRegisto
from .gestao import (
    PedidoCompra,
    NotificacaoGestao,
    ChecklistHSE,
    IncidenteSeguranca,
    AgendamentoRelatorioExecutivo,
)

# ===============================
# TODO FUTURO:
# - separar por apps (core, operacao, financeiro, rh)
# - adicionar signals centralizados
# - adicionar base model com empresa obrigatória
# ===============================
