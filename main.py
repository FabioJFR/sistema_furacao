import numpy as np
import matplotlib.pyplot as plt

# Formula base para calcular a trajetória de um poço a partir de MD, INC e AZIM:
# dx = ΔMD * sin(INC) * cos(AZIM)
# dy = ΔMD * sin(INC) * sin(AZIM)
# dz = ΔMD * cos(INC)

# ====================
# 1. Dados simulados
# ====================

def dados_simulados():
    # MD (profundidade medida)
    md = np.array([0, 20, 40, 60, 80, 100])  # em metros
    # Inclinação (em graus)
    inc = np.array([36, 35, 33, 32, 31, 30])  # em graus
    # Azimute (em graus)
    azim = np.array([25, 26, 25, 24, 25, 26])
    return md,inc, azim

# ====================
# 2. Ler CSV
# ====================
def ler_csv(nome_ficheiro):
    dados = np.loadtxt(nome_ficheiro, delimiter=",", skiprows=1)
    md = dados[:, 0]  # Coluna de MD
    inc = dados[:, 1]  # Coluna de INC
    azim = dados[:, 2]  # Coluna de AZIM
    return md, inc, azim


# ====================
# 3. Dados em tempo Real
# ====================
def ler_sensor():
    # simulação de leitura continua
    md = np.array([0, 10, 20,30, 40, 50])  # em metros
    inc = np.array([0, 3, 7, 12, 18, 25])  # em graus
    azim = np.array([0, 20, 40, 60, 80, 100])
    return md, inc, azim

# ====================
# 4. Cálculo da trajetória
# ====================

def calcular_trajetoria(md, inc, azim):
    inc = np.radians(inc)
    azim = np.radians(azim)

    x= [0]
    y = [0]
    z = [0]

    for i in range(1, len(md)):
        dmd = md[i] - md[i-1]

        dx = dmd * np.sin(inc[i]) * np.cos(azim[i])
        dy = dmd * np.sin(inc[i]) * np.sin(azim[i])
        dz = dmd * np.cos(inc[i])

        x.append(x[-1] + dx)
        y.append(y[-1] + dy)
        z.append(z[-1] - dz)  # negativo porque Z aumenta para baixo (profundidade)
    
    return x, y, z

# ====================
# 5. Visualização em 3D
# ====================

def mostrar_3d(x, y, z):
    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    
    ax.plot(x, y, z, marker='o')

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Profundidade")

    plt.show()


# ====================
# 6. Escolher Modo de Entrada
# ====================

modo = input("Escolhe o modo: 1-Simulado | 2-CSV | 3-Tempo Real: ")

if modo == "1":
    md, inc, azim = dados_simulados()

elif modo == "2":
    md, inc, azim = ler_csv("dados.csv")

elif modo == "3":
    md, inc, azim = ler_sensor()

else:
    print("Modo inválido")
    exit()


x, y, z = calcular_trajetoria(md, inc, azim)
mostrar_3d(x, y, z)

# O código acima é um exemplo básico de como calcular e visualizar a trajetória de um poço usando dados de MD, INC e AZIM. Ele inclui três modos de entrada: dados simulados, leitura de um arquivo CSV e simulação de leitura em tempo real. A trajetória é calculada usando as fórmulas de deslocamento e visualizada em um gráfico 3D. Para um uso real, seria necessário adaptar a leitura de dados em tempo real para se conectar a sensores reais e garantir que os dados estejam formatados corretamente.