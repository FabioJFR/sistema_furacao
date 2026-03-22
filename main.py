import numpy as np
import matplotlib.pyplot as plt

# Formula base para calcular a trajetória de um poço a partir de MD, INC e AZIM:
# dx = ΔMD * sin(INC) * cos(AZIM)
# dy = ΔMD * sin(INC) * sin(AZIM)
# dz = ΔMD * cos(INC)

# Dados simulados
# MD (profundidade medida)
md = np.array([0, 20, 40, 60, 80, 100])  # em metros

# Inclinação (em graus)
inc = np.array([36.8, 35.4, 33.5, 32.7, 31.6, 30.5])  # em graus

# Azimute (em graus)
azim = np.array([25.3, 26.2, 25.8, 24, 25, 26])

# Convertendo graus para radianos
inc_rad = np.radians(inc)
azim_rad = np.radians(azim)

# Inicializar arrays para as coordenadas X, Y, Z
x = [0]
y = [0]
z = [0]

# Calcular trajetória
for i in range(1, len(md)):
    dmd= md[i] - md[i-1]  # Incremento de profundidade

    dx = dmd * np.sin(inc_rad[i]) * np.cos(azim_rad[i])  # Incremento em X
    dy = dmd * np.sin(inc_rad[i]) * np.sin(azim_rad[i])  # Incremento em Y
    dz = dmd * np.cos(inc_rad[i])  # Incremento em Z

    x.append(x[-1] + dx)
    y.append(y[-1] + dy)
    z.append(z[-1] - dz) # negativo porque Z aumenta para baixo = profundidade

    # Plot 3D
    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')

    ax.plot(x ,y, z, marker='o')

    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Profundidade)")

    plt.show()
    