import requests
from urllib.parse import quote
#--------- corversor de latitude e longitude -----------
def obter_coordenadas_por_cidade_pais(cidade, pais):
    if not cidade or not pais:
        return None, None

    query = f"{cidade}, {pais}"
    url = f"https://nominatim.openstreetmap.org/search?q={quote(query)}&format=json&limit=1"

    headers = {
        "User-Agent": "SistemaFuracao/1.0"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            return lat, lon
    except Exception as e:
        print("Erro ao obter coordenadas:", e)

    return None, None
