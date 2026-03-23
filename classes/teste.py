from .projeto import Projeto
from .furo import Furo

# ================= DADOS DE TESTE =================


p = Projeto("Projeto Teste", (37.9, -8.1), "Cliente X")
f = Furo("Furo 1")
f.adicionar_medicao(20, -36, 10)
f.adicionar_medicao(40, -35.6, 11.3)
f.adicionar_medicao(60, -34.2, 11.2)
p.furos.append(f)

print("Projeto:", p.nome)
print("Furo:", f.nome)
print("Medições:")
for m in f.medicoes:
    print(f"  - Profundidade: {m['profundidade']} m, Inclinação: {m['inclinacao']}°, Azimute: {m['azimute']}°") 