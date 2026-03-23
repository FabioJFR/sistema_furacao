import uuid
from datetime import datetime


class Furo:
    """Classe que representa um Furo"""

    def __init__(self, nome="", localizacao=(0,0), id=None):
        self.id = id or str(uuid.uuid4())
        self.nome = nome
        self.localizacao = localizacao
        self.medicoes = []  # histórico de medições
        self.relatorios = []
        self.imagens = []
        self.estado = False
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
        """Adiciona uma medição diária com data atual"""
        self.medicoes.append({
            "id": str(uuid.uuid4()),
            "data": datetime.now().isoformat(),
            "profundidade": float(profundidade),
            "inclinacao": float(inclinacao),
            "azimute": float(azimute)
        })

    def editar(self, nome=None, localizacao=None):
        """Permite editar o nome e a localização"""
        if nome is not None:
            self.nome = nome
        if localizacao is not None:
            self.localizacao = localizacao

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d):
        f = Furo(d.get("nome",""), tuple(d.get("localizacao",(0,0))), d.get("id"))
        f.medicoes = d.get("medicoes", [])
        f.relatorios = d.get("relatorios", [])
        f.imagens = d.get("imagens", [])
        f.estado = d.get("estado", False)
        f.sondadores = d.get("sondadores", [])
        f.ajudantes = d.get("ajudantes", [])
        return f