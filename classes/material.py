""" import uuid

class Material:
    #Classe que representa um material

    def __init__(self, nome="", valor=0, quantidade=0, diametro=0, tipo="", numero_serie="", data_compra="", id=None):
        self.id = id or str(uuid.uuid4())
        self.nome = nome
        self.valor = valor
        self.quantidade = quantidade
        self.diametro = diametro
        self.tipo = tipo
        self.numero_serie = numero_serie
        self.data_compra = data_compra
        self.faturas = []
        self.alteracoes = []
        self.estado = "Em estoque"  # "Em estoque", "Sem Stock", "Recebido" "encomendado" 

    def editar(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d):
        m = Material(**d)
        m.faturas = d.get("faturas", [])
        m.alteracoes = d.get("alteracoes", [])
        return m """

import uuid

class Material:
    """Classe que representa um material"""

    def __init__(self, nome="", valor=0.0, quantidade=0, diametro=0.0, tipo="", numero_serie="", data_compra="", id=None):
        self._id = id or str(uuid.uuid4())
        self._nome = nome
        self._valor = valor
        self._quantidade = quantidade
        self._diametro = diametro
        self._tipo = tipo
        self._numero_serie = numero_serie
        self._data_compra = data_compra
        self._faturas = []
        self._alteracoes = []
        self._estado = "Em estoque"  # "Em estoque", "Sem Stock", "Recebido", "Encomendado"

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
    def valor(self):
        return self._valor
    @valor.setter
    def valor(self, value):
        self._valor = value

    @property
    def quantidade(self):
        return self._quantidade
    @quantidade.setter
    def quantidade(self, value):
        self._quantidade = value

    @property
    def diametro(self):
        return self._diametro
    @diametro.setter
    def diametro(self, value):
        self._diametro = value

    @property
    def tipo(self):
        return self._tipo
    @tipo.setter
    def tipo(self, value):
        self._tipo = value

    @property
    def numero_serie(self):
        return self._numero_serie
    @numero_serie.setter
    def numero_serie(self, value):
        self._numero_serie = value

    @property
    def data_compra(self):
        return self._data_compra
    @data_compra.setter
    def data_compra(self, value):
        self._data_compra = value

    @property
    def faturas(self):
        return self._faturas
    @faturas.setter
    def faturas(self, value):
        self._faturas = value

    @property
    def alteracoes(self):
        return self._alteracoes
    @alteracoes.setter
    def alteracoes(self, value):
        self._alteracoes = value

    @property
    def estado(self):
        return self._estado
    @estado.setter
    def estado(self, value):
        self._estado = value

    # ================== Métodos ==================
    def update(self, **kwargs):
        """Atualiza múltiplos atributos de uma vez"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self):
        """Converte objeto em dicionário"""
        return {
            "id": self._id,
            "nome": self._nome,
            "valor": self._valor,
            "quantidade": self._quantidade,
            "diametro": self._diametro,
            "tipo": self._tipo,
            "numero_serie": self._numero_serie,
            "data_compra": self._data_compra,
            "faturas": self._faturas,
            "alteracoes": self._alteracoes,
            "estado": self._estado
        }

    @staticmethod
    def from_dict(d):
        m = Material(
            nome=d.get("nome",""),
            valor=d.get("valor",0.0),
            quantidade=d.get("quantidade",0),
            diametro=d.get("diametro",0.0),
            tipo=d.get("tipo",""),
            numero_serie=d.get("numero_serie",""),
            data_compra=d.get("data_compra",""),
            id=d.get("id")
        )
        m.faturas = d.get("faturas", [])
        m.alteracoes = d.get("alteracoes", [])
        m.estado = d.get("estado", "Em estoque")
        return m