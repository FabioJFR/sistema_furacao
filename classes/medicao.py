class Medicao:
    def __init__(self, profundidade, inclinacao, azimute,magnetismo, data=None):
        self.profundidade = profundidade
        self.inclinacao = inclinacao
        self.azimute = azimute
        self.magnetismo = magnetismo
        self.data = data