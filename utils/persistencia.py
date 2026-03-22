import json
from classes.projeto import Projeto

def salvar_projetos(projetos, filename="data/projetos.json"):
    with open(filename,"w") as f:
        json.dump([p.to_dict() for p in projetos], f, indent=4)


def carregar_projetos(filename="data/projetos.json"):
    try:
        with open(filename,"r") as f:
            content = f.read().strip()
            if not content:  # se estiver vazio
                return []
            data = json.loads(content)
            return [Projeto.from_dict(d) for d in data]
    except FileNotFoundError:
        # cria arquivo vazio automaticamente
        with open(filename, "w") as f:
            f.write("[]")
        return []