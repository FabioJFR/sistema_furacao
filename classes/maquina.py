import uuid

class Maquina:
    """Classe que representa uma máquina"""

    def __init__(self, nome="", tipo="", modelo="", numero_serie="", km=0, ano=0, data_compra="", valor=0, id=None):
        self.id = id or str(uuid.uuid4())
        self.nome = nome
        self.tipo = tipo
        self.modelo = modelo
        self.numero_serie = numero_serie
        self.km = km
        self.ano = ano
        self.data_compra = data_compra
        self.valor = valor
        self.despesas = []

    def editar(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d):
        return Maquina(**d)