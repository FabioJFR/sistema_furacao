# materiais/services.py

def criar_material(nome, quantidade):
    """Função de teste para criar material"""
    print(f"[TESTE] Material criado: {nome} - {quantidade} unidades")

def listar_materiais():
    """Retorna lista de materiais de teste"""
    return [
        {"nome": "Broca Diamantada", "quantidade": 5},
        {"nome": "Cimento", "quantidade": 20},
        {"nome": "Tubos PVC", "quantidade": 50}
    ]