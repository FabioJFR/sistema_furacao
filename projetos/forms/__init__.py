# projetos/forms/__init__.py

# Core
from .preferencias import EmpresaFinanceiraForm, PreferenciasForm

# Projetos / Furos
from .projeto import ProjetoForm
from .furo import FuroForm, FuroCreateForm

# Empregados
from .empregado import *
from .empregado_area import MeusDadosEmpregadoForm
from .empregado_furo import EmpregadoFuroForm

# Operação
from .registo import *
from .configuracao_perfuracao import *

# Recursos
from .material import *
from .maquina import *
from .medicao import *
from .despesa import *
