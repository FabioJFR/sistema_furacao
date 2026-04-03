# projetos/ai.py
from PIL import Image
import numpy as np

def classificar_rocha(imagem_path):
    img = Image.open(imagem_path).resize((50, 50))
    arr = np.array(img)

    media = arr.mean(axis=(0,1))  # RGB médio

    r, g, b = media

    if r > 150 and g > 150:
        return "Areia"
    elif r < 100 and g < 100:
        return "Basalto"
    elif b > 120:
        return "Argila"
    else:
        return "Rocha mista"