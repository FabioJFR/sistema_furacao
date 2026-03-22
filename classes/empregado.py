class Empregado:
    def __init__(self, nome="", numero="", idade=0, doc_id="", nib="", morada="", nacionalidade="", nif="", categoria="", salario=0):
        self.nome = nome
        self.numero = numero
        self.idade = idade
        self.doc_id = doc_id
        self.nib = nib
        self.morada = morada
        self.nacionalidade = nacionalidade
        self.nif = nif
        self.categoria = categoria
        self.salario = salario

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d):
        return Empregado(**d)