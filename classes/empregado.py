import uuid

class Empregado:
    """Classe que representa um empregado"""

    def __init__(self, nome="", numero="", idade=0, doc_id="", nib="", morada="", nacionalidade="",
                 nif="", categoria="", salario=0, id=None):
        self.id = id or str(uuid.uuid4())
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

    def editar(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d):
        return Empregado(**d)