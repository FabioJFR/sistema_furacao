class Material:
    def __init__(self, nome="", valor=0, quantidade=0, diametro=0, tipo="", numero_serie="", data_compra=""):
        self.nome = nome
        self.valor = valor
        self.quantidade = quantidade
        self.diametro = diametro
        self.tipo = tipo
        self.numero_serie = numero_serie
        self.data_compra = data_compra
        self.faturas = []
        self.alteracoes = []

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d):
        m = Material(**d)
        m.faturas = d.get("faturas",[])
        m.alteracoes = d.get("alteracoes",[])
        return m