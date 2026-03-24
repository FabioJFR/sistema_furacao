""" from datetime import datetime

class Medicao:
    def __init__(self, profundidade=0, inclinacao=0, azimute=0, magnetismo=0, data=None):
        self.profundidade = profundidade
        self.inclinacao = inclinacao
        self.azimute = azimute
        self.magnetismo = magnetismo
        self.latitude = 0.0
        self.longitude = 0.0
        self.altitude = 0.0
        self.data = data or datetime.now().isoformat()

    def to_dict(self):
        return {
            "profundidade": self.profundidade,
            "inclinacao": self.inclinacao,
            "azimute": self.azimute,
            "magnetismo": self.magnetismo,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude": self.altitude,
            "data": self.data
        }

    @staticmethod
    def from_dict(d):
        return Medicao(
            profundidade=d.get("profundidade", 0),
            inclinacao=d.get("inclinacao", 0),
            azimute=d.get("azimute", 0),
            magnetismo=d.get("magnetismo", 0),
            data=d.get("data")
        ) """

from datetime import datetime

class Medicao:
    """Classe que representa uma medição de um furo"""

    def __init__(self, profundidade=0.0, inclinacao=0.0, azimute=0.0, magnetismo=0.0, data=None):
        self._profundidade = profundidade
        self._inclinacao = inclinacao
        self._azimute = azimute
        self._magnetismo = magnetismo
        self._latitude = 0.0
        self._longitude = 0.0
        self._altitude = 0.0
        self._data = data or datetime.now().isoformat()

    # ================== Properties ==================
    @property
    def profundidade(self):
        return self._profundidade
    @profundidade.setter
    def profundidade(self, value):
        self._profundidade = value

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
    def magnetismo(self):
        return self._magnetismo
    @magnetismo.setter
    def magnetismo(self, value):
        self._magnetismo = value

    @property
    def latitude(self):
        return self._latitude
    @latitude.setter
    def latitude(self, value):
        self._latitude = value

    @property
    def longitude(self):
        return self._longitude
    @longitude.setter
    def longitude(self, value):
        self._longitude = value

    @property
    def altitude(self):
        return self._altitude
    @altitude.setter
    def altitude(self, value):
        self._altitude = value

    @property
    def data(self):
        return self._data
    @data.setter
    def data(self, value):
        self._data = value

    # ================== Métodos ==================
    def update(self, **kwargs):
        """Atualiza múltiplos atributos de uma vez"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self):
        """Converte objeto em dicionário"""
        return {
            "profundidade": self._profundidade,
            "inclinacao": self._inclinacao,
            "azimute": self._azimute,
            "magnetismo": self._magnetismo,
            "latitude": self._latitude,
            "longitude": self._longitude,
            "altitude": self._altitude,
            "data": self._data
        }

    @staticmethod
    def from_dict(d):
        m = Medicao(
            profundidade=d.get("profundidade", 0.0),
            inclinacao=d.get("inclinacao", 0.0),
            azimute=d.get("azimute", 0.0),
            magnetismo=d.get("magnetismo", 0.0),
            data=d.get("data")
        )
        m.latitude = d.get("latitude", 0.0)
        m.longitude = d.get("longitude", 0.0)
        m.altitude = d.get("altitude", 0.0)
        return m