import json
import os
from classes.projeto import Projeto

FILE = "dados.json"

# Carrega projetos do JSON
def carregar_projetos():
    if not os.path.exists(FILE):
        return []
    with open(FILE, "r") as f:
        try:
            data = json.load(f)
        except:
            return []
    return [Projeto.from_dict(p) for p in data]

# Salva projetos no JSON
def salvar_projetos(projetos):
    with open(FILE, "w") as f:
        json.dump([p.to_dict() for p in projetos], f, indent=4)



def carregar_maquinas():
    # Mock de máquinas
    class Maquina:
        def __init__(self):
            self.nome = "Máquina Exemplo"
            self.tipo = "Sonda"
            self.modelo = "Modelo X"
            self.numero_serie = "12345"
            self.km = 1000
            self.ano = 2022
            self.estado = "operacional"
    return [Maquina()]

def carregar_materiais():
    # Mock de materiais
    class Material:
        def __init__(self):
            self.nome = "Coroa HQ"
            self.tipo = "coroa"
            self.quantidade = 10
            self.valor = 120
    return [Material()]