""" from datetime import date
import uuid

class Empregado:
    # Classe que representa um empregado

    def __init__(self, nome="", numero="",categoria="", id=None):
        self.id = id or str(uuid.uuid4())
        self.nome = nome
        self.numero = numero
        self.data_inicio_contrato = date.today().isoformat()
        self.data_fim_contrato = None
        self.idade = 0
        self.doc_id = ""
        self.nib = ""
        self.morada = ""
        self.nacionalidade = ""
        self.nif = ""
        self.categoria = categoria
        self.projetos = []
        self.curriculo = ""
        self.contrato = ""
        self.salario = 0.0
        self.horas_diarias = 0
        self.horas_mensais = 0
        self.horas_extra = 0
        self.projetos_ativos = []       # lista de IDs de projetos em que o empregado está ativo
        self.horas_trabalhadas_mes = 0   # para gráficos mensais
        self.alertas = []                # alertas automáticos (ex: atrasos, excesso de horas)


    def editar(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self):
        return self.__dict__

    from datetime import datetime

@staticmethod
def from_dict(d):
    emp = Empregado(**d)
    if isinstance(d.get("data_inicio_contrato"), str):
        emp.data_inicio_contrato = d["data_inicio_contrato"]
    if isinstance(d.get("data_fim_contrato"), str):
        emp.data_fim_contrato = d["data_fim_contrato"]
    return emp """

from datetime import date, datetime
import uuid

class Empregado:
    """Classe que representa um empregado"""

    def __init__(self, nome="", numero="", categoria="", id=None):
        self._id = id or str(uuid.uuid4())
        self._nome = nome
        self._numero = numero
        self._data_inicio_contrato = date.today().isoformat()
        self._data_fim_contrato = None
        self._idade = 0
        self._doc_id = ""
        self._nib = ""
        self._morada = ""
        self._nacionalidade = ""
        self._nif = ""
        self._categoria = categoria
        self._projetos = []  # lista de IDs de projetos
        self._curriculo = ""
        self._contrato = ""
        self._salario = 0.0
        self._horas_diarias = 0
        self._horas_mensais = 0
        self._horas_extra = 0
        self._projetos_ativos = []  # IDs de projetos ativos
        self._horas_trabalhadas_mes = 0
        self._alertas = []

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
    def numero(self):
        return self._numero
    @numero.setter
    def numero(self, value):
        self._numero = value

    @property
    def data_inicio_contrato(self):
        return self._data_inicio_contrato
    @data_inicio_contrato.setter
    def data_inicio_contrato(self, value):
        self._data_inicio_contrato = value

    @property
    def data_fim_contrato(self):
        return self._data_fim_contrato
    @data_fim_contrato.setter
    def data_fim_contrato(self, value):
        self._data_fim_contrato = value

    @property
    def idade(self):
        return self._idade
    @idade.setter
    def idade(self, value):
        self._idade = value

    @property
    def doc_id(self):
        return self._doc_id
    @doc_id.setter
    def doc_id(self, value):
        self._doc_id = value

    @property
    def nib(self):
        return self._nib
    @nib.setter
    def nib(self, value):
        self._nib = value

    @property
    def morada(self):
        return self._morada
    @morada.setter
    def morada(self, value):
        self._morada = value

    @property
    def nacionalidade(self):
        return self._nacionalidade
    @nacionalidade.setter
    def nacionalidade(self, value):
        self._nacionalidade = value

    @property
    def nif(self):
        return self._nif
    @nif.setter
    def nif(self, value):
        self._nif = value

    @property
    def categoria(self):
        return self._categoria
    @categoria.setter
    def categoria(self, value):
        self._categoria = value

    @property
    def projetos(self):
        return self._projetos
    @projetos.setter
    def projetos(self, value):
        self._projetos = value

    @property
    def curriculo(self):
        return self._curriculo
    @curriculo.setter
    def curriculo(self, value):
        self._curriculo = value

    @property
    def contrato(self):
        return self._contrato
    @contrato.setter
    def contrato(self, value):
        self._contrato = value

    @property
    def salario(self):
        return self._salario
    @salario.setter
    def salario(self, value):
        self._salario = value

    @property
    def horas_diarias(self):
        return self._horas_diarias
    @horas_diarias.setter
    def horas_diarias(self, value):
        self._horas_diarias = value

    @property
    def horas_mensais(self):
        return self._horas_mensais
    @horas_mensais.setter
    def horas_mensais(self, value):
        self._horas_mensais = value

    @property
    def horas_extra(self):
        return self._horas_extra
    @horas_extra.setter
    def horas_extra(self, value):
        self._horas_extra = value

    @property
    def projetos_ativos(self):
        return self._projetos_ativos
    @projetos_ativos.setter
    def projetos_ativos(self, value):
        self._projetos_ativos = value

    @property
    def horas_trabalhadas_mes(self):
        return self._horas_trabalhadas_mes
    @horas_trabalhadas_mes.setter
    def horas_trabalhadas_mes(self, value):
        self._horas_trabalhadas_mes = value

    @property
    def alertas(self):
        return self._alertas
    @alertas.setter
    def alertas(self, value):
        self._alertas = value

    # ================== Métodos ==================
    def update(self, **kwargs):
        """Atualiza múltiplos atributos de uma só vez"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self):
        """Converte objeto em dicionário"""
        return {
            "id": self._id,
            "nome": self._nome,
            "numero": self._numero,
            "data_inicio_contrato": self._data_inicio_contrato,
            "data_fim_contrato": self._data_fim_contrato,
            "idade": self._idade,
            "doc_id": self._doc_id,
            "nib": self._nib,
            "morada": self._morada,
            "nacionalidade": self._nacionalidade,
            "nif": self._nif,
            "categoria": self._categoria,
            "projetos": self._projetos,
            "curriculo": self._curriculo,
            "contrato": self._contrato,
            "salario": self._salario,
            "horas_diarias": self._horas_diarias,
            "horas_mensais": self._horas_mensais,
            "horas_extra": self._horas_extra,
            "projetos_ativos": self._projetos_ativos,
            "horas_trabalhadas_mes": self._horas_trabalhadas_mes,
            "alertas": self._alertas
        }

    @staticmethod
    def from_dict(d):
        emp = Empregado(
            id=d.get("id"),
            nome=d.get("nome", ""),
            numero=d.get("numero", ""),
            categoria=d.get("categoria", "")
        )
        emp.data_inicio_contrato = d.get("data_inicio_contrato", date.today().isoformat())
        emp.data_fim_contrato = d.get("data_fim_contrato")
        emp.idade = d.get("idade", 0)
        emp.doc_id = d.get("doc_id", "")
        emp.nib = d.get("nib", "")
        emp.morada = d.get("morada", "")
        emp.nacionalidade = d.get("nacionalidade", "")
        emp.nif = d.get("nif", "")
        emp.projetos = d.get("projetos", [])
        emp.curriculo = d.get("curriculo", "")
        emp.contrato = d.get("contrato", "")
        emp.salario = d.get("salario", 0.0)
        emp.horas_diarias = d.get("horas_diarias", 0)
        emp.horas_mensais = d.get("horas_mensais", 0)
        emp.horas_extra = d.get("horas_extra", 0)
        emp.projetos_ativos = d.get("projetos_ativos", [])
        emp.horas_trabalhadas_mes = d.get("horas_trabalhadas_mes", 0)
        emp.alertas = d.get("alertas", [])
        return emp