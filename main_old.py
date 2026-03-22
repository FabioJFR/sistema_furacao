import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
import pyvista as pv

# =========================
# VARIÁVEIS
# =========================
running = False

md_list = [0]
inc_list = [0]
azim_list = [0]

x = [0]
y = [0]
z = [0]

md_atual = 0

# imagens associadas a profundidade
imagens_por_md = {}

# =========================
# MINIMUM CURVATURE
# =========================
def calcular_min_curve(md, inc, azim):

    inc = np.radians(inc)
    azim = np.radians(azim)

    x = [0]
    y = [0]
    z = [0]

    for i in range(1, len(md)):

        dmd = md[i] - md[i-1]

        dl = np.arccos(
            np.cos(inc[i-1]) * np.cos(inc[i]) +
            np.sin(inc[i-1]) * np.sin(inc[i]) *
            np.cos(azim[i] - azim[i-1])
        )

        rf = (2 / dl) * np.tan(dl / 2) if dl != 0 else 1

        dx = dmd / 2 * (
            np.sin(inc[i-1]) * np.cos(azim[i-1]) +
            np.sin(inc[i]) * np.cos(azim[i])
        ) * rf

        dy = dmd / 2 * (
            np.sin(inc[i-1]) * np.sin(azim[i-1]) +
            np.sin(inc[i]) * np.sin(azim[i])
        ) * rf

        dz = dmd / 2 * (
            np.cos(inc[i-1]) + np.cos(inc[i])
        ) * rf

        x.append(x[-1] + dx)
        y.append(y[-1] + dy)
        z.append(z[-1] - dz)

    return x, y, z


# =========================
# GERAR DADOS (simulação)
# =========================
def gerar_dado():
    global md_atual
    md_atual += 5
    inc = min(md_atual * 0.4, 30)
    azim = md_atual * 2
    return md_atual, inc, azim


# =========================
# ATUALIZAÇÃO
# =========================
def update():

    global running, x, y, z

    if running:
        md, inc, azim = gerar_dado()

        md_list.append(md)
        inc_list.append(inc)
        azim_list.append(azim)

        x, y, z = calcular_min_curve(md_list, inc_list, azim_list)

        atualizar_3d()
        atualizar_imagem(md)

    root.after(1000, update)


# =========================
# 3D (PYVISTA)
# =========================
plotter = pv.Plotter()
plotter.show(interactive_update=True,auto_close=False)

def atualizar_3d():
    plotter.clear()

    pts = np.column_stack((x, y, z))

    if len(pts) > 1:
        plotter.add_lines(pts, width=4)

    plotter.update()


# =========================
# IMAGENS
# =========================
def escolher_imagem():
    caminho = filedialog.askopenfilename()

    if caminho:
        md = float(entry_md.get())

        imagens_por_md[md] = caminho
        print(f"Imagem associada a {md}m")


def atualizar_imagem(md_atual):

    # procurar imagem mais próxima
    md_keys = sorted(imagens_por_md.keys())

    for md in md_keys:
        if md_atual >= md:
            caminho = imagens_por_md[md]

            img = Image.open(caminho)
            img = img.resize((200, 200))

            img_tk = ImageTk.PhotoImage(img)

            label_img.config(image=img_tk)
            label_img.image = img_tk


# =========================
# CONTROLOS
# =========================
def start():
    global running
    running = True

def stop():
    global running
    running = False

def reset():
    global md_list, inc_list, azim_list, x, y, z, md_atual

    md_list = [0]
    inc_list = [0]
    azim_list = [0]

    x = [0]
    y = [0]
    z = [0]

    md_atual = 0

    plotter.clear()


# =========================
# UI
# =========================
root = tk.Tk()
root.title("Drilling System PRO")

frame = ttk.Frame(root)
frame.pack(pady=10)

ttk.Button(frame, text="Start", command=start).grid(row=0, column=0)
ttk.Button(frame, text="Stop", command=stop).grid(row=0, column=1)
ttk.Button(frame, text="Reset", command=reset).grid(row=0, column=2)

# entrada de profundidade para associar imagem
entry_md = ttk.Entry(frame, width=10)
entry_md.grid(row=0, column=3)
entry_md.insert(0, "10")

ttk.Button(frame, text="Associar Imagem", command=escolher_imagem).grid(row=0, column=4)

# área de imagem
label_img = tk.Label(root)
label_img.pack()

# iniciar loop
update()
root.mainloop()