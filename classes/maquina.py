import uuid

class Maquina:
    """Classe que representa uma máquina"""

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
        return Maquina(**d)