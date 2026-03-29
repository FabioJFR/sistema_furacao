# furos/models.py
# Este módulo define a classe Furo, que representa um furo de sondagem, com atributos e métodos para manipulação dos dados relacionados a cada furo.
# furos/models.py
import uuid

class Furo:
    def __init__(
        self, 
        nome="", 
        projeto="", 
        localizacao=(0.0, 0.0), 
        local_sondagem="", 
        inclinacao=0.0, 
        azimute=0.0, 
        profundidade_alvo=0.0, 
        id=None, 
        estado="ativo"
    ):
        self._id = id or str(uuid.uuid4())
        self._nome = nome
        self.projeto = projeto
        self._localizacao = localizacao  # (lat, lon)
        self.local_sondagem = local_sondagem
        self.tipo = ""  # fundo, superfície
        self._estado = estado  # "ativo", "parado", "concluido"
        self._medicoes = []
        self._relatorios = [] # imagens, pdfs
        self._imagens = []
        self.planeamento = "" # imagens, pdfs
        self.cliente = ""
        self.ficheiros = [] # outros ficheiros
        self._sondadores = []
        self._ajudantes = []
        self._inclinacao = inclinacao
        self._azimute = azimute
        self._profundidade_alvo = profundidade_alvo
        self._profundidade_atual = 0.0
        self._detalhes = "" # pdf
        self._metros_furados_diario = [] # vários valores diários
        self._metros_furados = 0.0
    # GETTERS e SETTERS

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

    # Podemos adicionar mais getters/setters conforme necessário