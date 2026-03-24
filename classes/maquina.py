""" import uuid

class Maquina:
    # Classe que representa uma máquina

    def __init__(self, nome="", tipo="", modelo="", data_compra="",id=None):
        self.id = id or str(uuid.uuid4())
        self.nome = nome
        self.tipo = tipo
        self.modelo = modelo
        self.numero_serie = ""
        self.data_registo = None
        self.data_revisao = None
        self.estado = "Operacional"
        self.seguro = ""
        self.data_iuc = None
        self.km = 0.0
        self.ano_registo = 0
        self.data_compra = data_compra
        self.valor = 0.0
        self.despesas = []

    def editar(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d):
        return Maquina(**d) """
import uuid
from datetime import datetime

class Maquina:
    """Classe que representa uma máquina"""

    def __init__(self, nome="", tipo="", modelo="", data_compra="", id=None):
        self._id = id or str(uuid.uuid4())
        self._nome = nome
        self._tipo = tipo
        self._modelo = modelo
        self._numero_serie = ""
        self._data_registo = None
        self._data_revisao = None
        self._estado = "Operacional"
        self._seguro = ""
        self._data_iuc = None
        self._km = 0.0
        self._ano_registo = 0
        self._data_compra = data_compra
        self._valor = 0.0
        self._despesas = []

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
    def tipo(self):
        return self._tipo
    @tipo.setter
    def tipo(self, value):
        self._tipo = value

    @property
    def modelo(self):
        return self._modelo
    @modelo.setter
    def modelo(self, value):
        self._modelo = value

    @property
    def numero_serie(self):
        return self._numero_serie
    @numero_serie.setter
    def numero_serie(self, value):
        self._numero_serie = value

    @property
    def data_registo(self):
        return self._data_registo
    @data_registo.setter
    def data_registo(self, value):
        self._data_registo = value

    @property
    def data_revisao(self):
        return self._data_revisao
    @data_revisao.setter
    def data_revisao(self, value):
        self._data_revisao = value

    @property
    def estado(self):
        return self._estado
    @estado.setter
    def estado(self, value):
        self._estado = value

    @property
    def seguro(self):
        return self._seguro
    @seguro.setter
    def seguro(self, value):
        self._seguro = value

    @property
    def data_iuc(self):
        return self._data_iuc
    @data_iuc.setter
    def data_iuc(self, value):
        self._data_iuc = value

    @property
    def km(self):
        return self._km
    @km.setter
    def km(self, value):
        self._km = value

    @property
    def ano_registo(self):
        return self._ano_registo
    @ano_registo.setter
    def ano_registo(self, value):
        self._ano_registo = value

    @property
    def data_compra(self):
        return self._data_compra
    @data_compra.setter
    def data_compra(self, value):
        self._data_compra = value

    @property
    def valor(self):
        return self._valor
    @valor.setter
    def valor(self, value):
        self._valor = value

    @property
    def despesas(self):
        return self._despesas
    @despesas.setter
    def despesas(self, value):
        self._despesas = value

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
            "tipo": self._tipo,
            "modelo": self._modelo,
            "numero_serie": self._numero_serie,
            "data_registo": self._data_registo,
            "data_revisao": self._data_revisao,
            "estado": self._estado,
            "seguro": self._seguro,
            "data_iuc": self._data_iuc,
            "km": self._km,
            "ano_registo": self._ano_registo,
            "data_compra": self._data_compra,
            "valor": self._valor,
            "despesas": self._despesas
        }

    @staticmethod
    def from_dict(d):
        m = Maquina(
            nome=d.get("nome",""),
            tipo=d.get("tipo",""),
            modelo=d.get("modelo",""),
            data_compra=d.get("data_compra",""),
            id=d.get("id")
        )
        m.numero_serie = d.get("numero_serie","")
        m.data_registo = d.get("data_registo")
        m.data_revisao = d.get("data_revisao")
        m.estado = d.get("estado","Operacional")
        m.seguro = d.get("seguro","")
        m.data_iuc = d.get("data_iuc")
        m.km = d.get("km",0.0)
        m.ano_registo = d.get("ano_registo",0)
        m.valor = d.get("valor",0.0)
        m.despesas = d.get("despesas",[])
        return m