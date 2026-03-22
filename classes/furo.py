class Furo:
    def __init__(self, nome="", inclinacao=0, azimute=0, profundidade=0, localizacao=(0,0)):
        self.nome = nome
        self.inclinacao = inclinacao
        self.azimute = azimute
        self.profundidade = profundidade
        self.localizacao = localizacao
        self.desvios = []
        self.relatorios = []
        self.imagens = []
        self.sondadores = []
        self.ajudantes = []

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d):
        f = Furo(
            d.get("nome",""),
            d.get("inclinacao",0),
            d.get("azimute",0),
            d.get("profundidade",0),
            tuple(d.get("localizacao",(0,0)))
        )
        f.desvios = d.get("desvios",[])
        f.relatorios = d.get("relatorios",[])
        f.imagens = d.get("imagens",[])
        f.sondadores = d.get("sondadores",[])
        f.ajudantes = d.get("ajudantes",[])
        return f