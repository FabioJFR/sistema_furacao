import uuid
from .furo import Furo
from .empregado import Empregado
from .maquina import Maquina
from .material import Material

class Projeto:
    """Classe que representa um projeto"""

    def __init__(self, nome="", localizacao=(0,0), cliente="", id=None):
        self.id = id or str(uuid.uuid4())
        self.nome = nome
        self.localizacao = localizacao
        self.cliente = cliente
        self.furos = []
        self.empregados = []
        self.maquinas = []
        self.materiais = []

    def editar(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self):
        return {
            "id": self.id,
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
        p = Projeto(d.get("nome",""), tuple(d.get("localizacao",(0,0))), d.get("cliente",""), d.get("id"))
        p.furos = [Furo.from_dict(f) for f in d.get("furos", [])]
        p.empregados = [Empregado.from_dict(e) for e in d.get("empregados", [])]
        p.maquinas = [Maquina.from_dict(m) for m in d.get("maquinas", [])]
        p.materiais = [Material.from_dict(m) for m in d.get("materiais", [])]
        return p