# maquinas/services.py

def criar_maquina(nome, tipo):
    """Função de teste para criar máquina"""
    print(f"[TESTE] Máquina criada: {nome} - {tipo}")

def listar_maquinas():
    """Retorna lista de máquinas de teste"""
    return [
        {"nome": "Perfuratriz X1", "tipo": "Superfície"},
        {"nome": "Perfuratriz Y2", "tipo": "Subterrânea"},
        {"nome": "Bomba Água", "tipo": "Auxiliar"}
    ]