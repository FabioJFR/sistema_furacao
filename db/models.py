import uuid

class Furo:
    def __init__(self, nome="", localizacao=(0, 0), id=None, estado="ativo", profundidade_alvo=0.0):
        self._id = id or str(uuid.uuid4())
        self._nome = nome
        self._localizacao = localizacao
        self.local_sondagem = ""
        self.tipo = ""  # fundo, superfície
        self._estado = estado  # ativo, parado, concluído
        self._medicoes = []
        self._relatorios = []
        self._imagens = []
        self.planeamento = ""
        self.cliente = ""
        self.ficheiros = []
        self._sondadores = []
        self._ajudantes = []
        self._inclinacao = 0.0
        self._azimute = 0.0
        self._profundidade_alvo = profundidade_alvo
        self._profundidade_final = 0.0
        self._profundidade_atual = 0.0
        self._detalhes = ""
        self._metros_furados_diario = []
        self._metros_furados = 0.0

    @property
    def id(self):
        return self._id

    @property
    def profundidade_atual(self):
        return self._profundidade_atual

    @profundidade_atual.setter
    def profundidade_atual(self, valor):
        self._profundidade_atual = valor

    @property
    def profundidade_alvo(self):
        return self._profundidade_alvo

    @profundidade_alvo.setter
    def profundidade_alvo(self, valor):
        self._profundidade_alvo = valor