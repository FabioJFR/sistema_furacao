class Maquina:
    def __init__(self, nome="", tipo="", modelo="", numero_serie="", km=0, ano=0, data_compra="", valor=0):
        self.nome = nome
        self.tipo = tipo
        self.modelo = modelo
        self.numero_serie = numero_serie
        self.km = km
        self.ano = ano
        self.data_compra = data_compra
        self.valor = valor
        self.despesas = []

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d):
        return Maquina(**d)