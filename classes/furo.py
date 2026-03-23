""" import uuid
from datetime import datetime


class Furo:
    # Classe que representa um Furo

    def __init__(self, nome="", localizacao=(0,0), id=None, estado="ativo"):
        self.id = id or str(uuid.uuid4())
        self.nome = nome
        self.localizacao = localizacao
        self.medicoes = []  # histórico de medições
        self.relatorios = []
        self.imagens = []
        self.estado = estado
        self.sondadores = []
        self.ajudantes = []
        self.inclinacao = 0.0
        self.azimute = 0.0
        self.profundidade_alvo = 0.0
        self.profundidade_final = 0.0
        self.profundidade_atual = 0.0
        self.detalhes = ""
        
    # mudar este método para receber um objeto Medicao ao invés de parâmetros separados, e o atributo de mediçao da classe deve receber varias listas de objetos Medicao
    def adicionar_medicao(self, profundidade, inclinacao, azimute):
        # Adiciona uma medição diária com data atual
        self.medicoes.append({
            "id": str(uuid.uuid4()),
            "data": datetime.now().isoformat(),
            "profundidade": float(profundidade),
            "inclinacao": float(inclinacao),
            "azimute": float(azimute)
        })

    def editar(self, nome=None, localizacao=None):
        # Permite editar o nome e a localização
        if nome is not None:
            self.nome = nome
        if localizacao is not None:
            self.localizacao = localizacao

    #def to_dict(self):
    #   return self.__dict__

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "estado": self.estado,
            "medicoes": self.medicoes
        }

    @staticmethod
    def from_dict(d):
        f = Furo(d.get("nome"), d.get("id"), d.get("estado", "ativo"))
        f.medicoes = d.get("medicoes", [])
        return f


    @staticmethod
    def from_dict(d):
        f = Furo(d.get("nome",""), tuple(d.get("localizacao",(0,0))), d.get("id"))
        f.medicoes = d.get("medicoes", [])
        f.relatorios = d.get("relatorios", [])
        f.imagens = d.get("imagens", [])
        f.estado = d.get("estado", False)
        f.sondadores = d.get("sondadores", [])
        f.ajudantes = d.get("ajudantes", [])
        return f """


import uuid
from datetime import datetime

class Furo:
    def __init__(self, nome="", localizacao=(0,0), id=None, estado="ativo"):
        self.id = id or str(uuid.uuid4())
        self.nome = nome
        self.localizacao = localizacao
        self.estado = estado  # "ativo", "parado", "concluido"
        self.medicoes = []
        self.relatorios = []
        self.imagens = []
        self.sondadores = []
        self.ajudantes = []
        self.inclinacao = 0.0
        self.azimute = 0.0
        self.profundidade_alvo = 0.0
        self.profundidade_final = 0.0
        self.profundidade_atual = 0.0
        self.detalhes = ""
        self.metros_furados_diario = []
        self.metros_furados = 0.0

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "localizacao": self.localizacao,
            "estado": self.estado,
            "medicoes": self.medicoes,
            "relatorios": self.relatorios,
            "imagens": self.imagens,
            "sondadores": self.sondadores,
            "ajudantes": self.ajudantes,
            "inclinacao": self.inclinacao,
            "azimute": self.azimute,
            "profundidade_alvo": self.profundidade_alvo,
            "profundidade_final": self.profundidade_final,
            "profundidade_atual": self.profundidade_atual,
            "detalhes": self.detalhes,
            "metros_furados_diario": self.metros_furados_diario,
            "metros_furados": self.metros_furados
        }

    @staticmethod
    def from_dict(d):
        f = Furo(
            nome=d.get("nome",""),
            localizacao=tuple(d.get("localizacao",(0,0))),
            id=d.get("id"),
            estado=str(d.get("estado", "ativo"))  # garante string
        )
        f.medicoes = d.get("medicoes", [])
        f.relatorios = d.get("relatorios", [])
        f.imagens = d.get("imagens", [])
        f.sondadores = d.get("sondadores", [])
        f.ajudantes = d.get("ajudantes", [])
        f.inclinacao = d.get("inclinacao", 0.0)
        f.azimute = d.get("azimute", 0.0)
        f.profundidade_alvo = d.get("profundidade_alvo", 0.0)
        f.profundidade_final = d.get("profundidade_final", 0.0)
        f.profundidade_atual = d.get("profundidade_atual", 0.0)
        f.detalhes = d.get("detalhes", "")
        f.metros_furados_diario = d.get("metros_furados_diario", [])
        f.metros_furados = d.get("metros_furados", 0.0)
        return f