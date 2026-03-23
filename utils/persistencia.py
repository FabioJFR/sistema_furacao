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