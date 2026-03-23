from datetime import date
import uuid

class Empregado:
    """Classe que representa um empregado"""

    def __init__(self, nome="", numero="",categoria="", id=None):
        self.id = id or str(uuid.uuid4())
        self.nome = nome
        self.numero = numero
        self.data_inicio_contrato = date.today().isoformat()
        self.data_fim_contrato = None
        self.idade = 0
        self.doc_id = ""
        self.nib = ""
        self.morada = ""
        self.nacionalidade = ""
        self.nif = ""
        self.categoria = categoria
        self.projetos = []
        self.curriculo = ""
        self.contrato = ""
        self.salario = 0.0
        self.horas_diarias = 0
        self.horas_mensais = 0
        self.horas_extra = 0
        self.projetos_ativos = []       # lista de IDs de projetos em que o empregado está ativo
        self.horas_trabalhadas_mes = 0   # para gráficos mensais
        self.alertas = []                # alertas automáticos (ex: atrasos, excesso de horas)


    def editar(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self):
        return self.__dict__

    from datetime import datetime

@staticmethod
def from_dict(d):
    emp = Empregado(**d)
    if isinstance(d.get("data_inicio_contrato"), str):
        emp.data_inicio_contrato = d["data_inicio_contrato"]
    if isinstance(d.get("data_fim_contrato"), str):
        emp.data_fim_contrato = d["data_fim_contrato"]
    return emp