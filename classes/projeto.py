""" import uuid
from .furo import Furo
from .empregado import Empregado
from .maquina import Maquina
from .material import Material

class Projeto:
    # Classe que representa um projeto

    def __init__(self, nome="", localizacao=(0,0), cliente="", id=None):
        self.id = id or str(uuid.uuid4())
        self.nome = nome
        self.localizacao = localizacao
        self.cliente = cliente
        self.furos = []
        self.empregados = []
        self.maquinas = []
        self.materiais = []

    def editar(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "localizacao": self.localizacao,
            "cliente": self.cliente,
            "furos": [f.to_dict() for f in self.furos],
            "empregados": [e.to_dict() for e in self.empregados],
            "maquinas": [m.to_dict() for m in self.maquinas],
            "materiais": [m.to_dict() for m in self.materiais]
        }

    @staticmethod
    def from_dict(d):
        p = Projeto(d.get("nome",""), tuple(d.get("localizacao",(0,0))), d.get("cliente",""), d.get("id"))
        p.furos = [Furo.from_dict(f) for f in d.get("furos", [])]
        p.empregados = [Empregado.from_dict(e) for e in d.get("empregados", [])]
        p.maquinas = [Maquina.from_dict(m) for m in d.get("maquinas", [])]
        p.materiais = [Material.from_dict(m) for m in d.get("materiais", [])]
        return p """
import uuid
from .furo import Furo
from .empregado import Empregado
from .maquina import Maquina
from .material import Material
from datetime import datetime

class Projeto:
    """Classe que representa um projeto"""

    def __init__(self, nome="", localizacao=(0,0), cliente="", id=None):
        self._id = id or str(uuid.uuid4())
        self._nome = nome
        self._localizacao = localizacao
        self._cliente = cliente

        self._furos = []       # lista de objetos Furo
        self._empregados = []  # lista de objetos Empregado
        self._maquinas = []    # lista de objetos Maquina
        self._materiais = []   # lista de objetos Material

        # Atributos extras para análise de dados
        self._data_inicio = datetime.now().isoformat()
        self._data_fim = None
        self._status = "ativo"  # ativo, pausado, concluído
        self._notas = ""        # observações gerais do projeto

    # ================== Properties ==================
    @property
    def id(self):
        return self._id

    @property
    def nome(self):
        return self._nome
    @nome.setter
    def nome(self, value):
        self._nome = value

    @property
    def localizacao(self):
        return self._localizacao
    @localizacao.setter
    def localizacao(self, value):
        self._localizacao = value

    @property
    def cliente(self):
        return self._cliente
    @cliente.setter
    def cliente(self, value):
        self._cliente = value

    @property
    def furos(self):
        return self._furos
    @furos.setter
    def furos(self, value):
        self._furos = value

    @property
    def empregados(self):
        return self._empregados
    @empregados.setter
    def empregados(self, value):
        self._empregados = value

    @property
    def maquinas(self):
        return self._maquinas
    @maquinas.setter
    def maquinas(self, value):
        self._maquinas = value

    @property
    def materiais(self):
        return self._materiais
    @materiais.setter
    def materiais(self, value):
        self._materiais = value

    @property
    def data_inicio(self):
        return self._data_inicio
    @data_inicio.setter
    def data_inicio(self, value):
        self._data_inicio = value

    @property
    def data_fim(self):
        return self._data_fim
    @data_fim.setter
    def data_fim(self, value):
        self._data_fim = value

    @property
    def status(self):
        return self._status
    @status.setter
    def status(self, value):
        self._status = value

    @property
    def notas(self):
        return self._notas
    @notas.setter
    def notas(self, value):
        self._notas = value

    # ================== Métodos ==================
    def update(self, **kwargs):
        """Atualiza múltiplos atributos de uma vez"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def adicionar_furo(self, furo: Furo):
        self._furos.append(furo)

    def adicionar_empregado(self, empregado: Empregado):
        self._empregados.append(empregado)

    def adicionar_maquina(self, maquina: Maquina):
        self._maquinas.append(maquina)

    def adicionar_material(self, material: Material):
        self._materiais.append(material)

    def to_dict(self):
        """Converte o projeto em dicionário para JSON"""
        return {
            "id": self._id,
            "nome": self._nome,
            "localizacao": self._localizacao,
            "cliente": self._cliente,
            "furos": [f.to_dict() for f in self._furos],
            "empregados": [e.to_dict() for e in self._empregados],
            "maquinas": [m.to_dict() for m in self._maquinas],
            "materiais": [m.to_dict() for m in self._materiais],
            "data_inicio": self._data_inicio,
            "data_fim": self._data_fim,
            "status": self._status,
            "notas": self._notas
        }

    @staticmethod
    def from_dict(d):
        p = Projeto(
            nome=d.get("nome",""),
            localizacao=tuple(d.get("localizacao",(0,0))),
            cliente=d.get("cliente",""),
            id=d.get("id")
        )
        p.furos = [Furo.from_dict(f) for f in d.get("furos", [])]
        p.empregados = [Empregado.from_dict(e) for e in d.get("empregados", [])]
        p.maquinas = [Maquina.from_dict(m) for m in d.get("maquinas", [])]
        p.materiais = [Material.from_dict(m) for m in d.get("materiais", [])]
        p.data_inicio = d.get("data_inicio")
        p.data_fim = d.get("data_fim")
        p.status = d.get("status", "ativo")
        p.notas = d.get("notas", "")
        return p