import uuid
from classes.medicao import Medicao

class Furo:
    """Classe que representa um furo de perfuração"""

    def __init__(self, nome="", localizacao=(0,0), id=None, estado="ativo"):
        self._id = id or str(uuid.uuid4())
        self._nome = nome
        self._localizacao = localizacao
        self.local_sondagem = ""
        self.tipo = ""  # fundo, superficie
        self._estado = estado  # "ativo", "parado", "concluido"
        self._medicoes = []
        self._relatorios = [] # imagem,pdf
        self._imagens = []
        self.planeamento = "" # imagem,pdf
        self.cliente = ""
        self.ficheiros = [] # outros ficheiros
        self._sondadores = []
        self._ajudantes = []
        self._inclinacao = 0.0
        self._azimute = 0.0
        self._profundidade_alvo = 0.0
        self._profundidade_final = 0.0
        self._profundidade_atual = 0.0
        self._detalhes = "" # pdf
        self._metros_furados_diario = [] # varios valores diarios
        self._metros_furados = 0.0

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
    def localizacao(self):
        return self._localizacao
    @localizacao.setter
    def localizacao(self, value):
        self._localizacao = value

    @property
    def estado(self):
        return self._estado
    @estado.setter
    def estado(self, value):
        self._estado = value

    @property
    def medicoes(self):
        return self._medicoes
    @medicoes.setter
    def medicoes(self, value):
        self._medicoes = value

    @property
    def relatorios(self):
        return self._relatorios
    @relatorios.setter
    def relatorios(self, value):
        self._relatorios = value

    @property
    def imagens(self):
        return self._imagens
    @imagens.setter
    def imagens(self, value):
        self._imagens = value

    @property
    def sondadores(self):
        return self._sondadores
    @sondadores.setter
    def sondadores(self, value):
        self._sondadores = value

    @property
    def ajudantes(self):
        return self._ajudantes
    @ajudantes.setter
    def ajudantes(self, value):
        self._ajudantes = value

    @property
    def inclinacao(self):
        return self._inclinacao
    @inclinacao.setter
    def inclinacao(self, value):
        self._inclinacao = value

    @property
    def azimute(self):
        return self._azimute
    @azimute.setter
    def azimute(self, value):
        self._azimute = value

    @property
    def profundidade_alvo(self):
        return self._profundidade_alvo
    @profundidade_alvo.setter
    def profundidade_alvo(self, value):
        self._profundidade_alvo = value

    @property
    def profundidade_final(self):
        return self._profundidade_final
    @profundidade_final.setter
    def profundidade_final(self, value):
        self._profundidade_final = value

    @property
    def profundidade_atual(self):
        return self._profundidade_atual
    @profundidade_atual.setter
    def profundidade_atual(self, value):
        self._profundidade_atual = value

    @property
    def detalhes(self):
        return self._detalhes
    @detalhes.setter
    def detalhes(self, value):
        self._detalhes = value

    @property
    def metros_furados_diario(self):
        return self._metros_furados_diario
    @metros_furados_diario.setter
    def metros_furados_diario(self, value):
        self._metros_furados_diario = value

    @property
    def metros_furados(self):
        return self._metros_furados
    @metros_furados.setter
    def metros_furados(self, value):
        self._metros_furados = value

    # ================== Métodos ==================
    def adicionar_medicao(self, profundidade, inclinacao, azimute, magnetismo=0):
        m = Medicao(profundidade, inclinacao, azimute, magnetismo)
        self._medicoes.append(m)

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
            "localizacao": self._localizacao,
            "estado": self._estado,
            "medicoes": [m.to_dict() for m in self._medicoes],
            "relatorios": self._relatorios,
            "imagens": self._imagens,
            "sondadores": self._sondadores,
            "ajudantes": self._ajudantes,
            "inclinacao": self._inclinacao,
            "azimute": self._azimute,
            "profundidade_alvo": self._profundidade_alvo,
            "profundidade_final": self._profundidade_final,
            "profundidade_atual": self._profundidade_atual,
            "detalhes": self._detalhes,
            "metros_furados_diario": self._metros_furados_diario,
            "metros_furados": self._metros_furados
        }

    @staticmethod
    def from_dict(d):
        f = Furo(
            nome=d.get("nome",""),
            localizacao=tuple(d.get("localizacao",(0,0))),
            id=d.get("id"),
            estado=str(d.get("estado", "ativo"))
        )
        f.medicoes = [Medicao.from_dict(md) for md in d.get("medicoes", [])]
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