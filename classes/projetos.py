from .furo import Furo
from .empregado import Empregado
from .maquina import Maquina
from .material import Material

class Projeto:
    def __init__(self, nome="", localizacao=(0,0), cliente=""):
        self.nome = nome
        self.localizacao = localizacao  # (lat, lon)
        self.cliente = cliente
        self.furos: list[Furo] = []
        self.empregados: list[Empregado] = []
        self.maquinas: list[Maquina] = []
        self.materiais: list[Material] = []

    def to_dict(self):
        return {
            "nome": self.nome,
            "localizacao": self.localizacao,
            "cliente": self.cliente,
            "furos": [f.to_dict() for f in self.furos],
            "empregados": [e.to_dict() for e in self.empregados],
            "maquinas": [m.to_dict() for m in self.maquinas],
            "materiais": [m.to_dict() for m in self.materiais]
        }

    @staticmethod
    def from_dict(d):
        p = Projeto(d["nome"], tuple(d["localizacao"]), d["cliente"])
        from .furo import Furo
        from .empregado import Empregado
        from .maquina import Maquina
        from .material import Material

        p.furos = [Furo.from_dict(f) for f in d.get("furos", [])]
        p.empregados = [Empregado.from_dict(e) for e in d.get("empregados", [])]
        p.maquinas = [Maquina.from_dict(m) for m in d.get("maquinas", [])]
        p.materiais = [Material.from_dict(m) for m in d.get("materiais", [])]
        return p