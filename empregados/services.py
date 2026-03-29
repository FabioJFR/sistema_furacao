# empregados/services.py

def criar_empregado(nome, cargo):
    """Função de teste para criar empregado"""
    print(f"[TESTE] Empregado criado: {nome} - {cargo}")

def listar_empregados():
    """Retorna lista de empregados de teste"""
    return [
        {"nome": "João Silva", "cargo": "Geólogo"},
        {"nome": "Maria Santos", "cargo": "Técnica"},
        {"nome": "Carlos Pereira", "cargo": "Supervisor"}
    ]