import requests
from urllib.parse import quote


def obter_coordenadas_por_cidade_pais(cidade, pais):
    if not cidade or not pais:
        return None, None

    query = f"{cidade}, {pais}"
    query_encoded = quote(query)

    url = f"https://nominatim.openstreetmap.org/search?q={query_encoded}&format=json&limit=1"

    headers = {
        "User-Agent": "sistema-furacao/1.0"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        dados = response.json()

        if dados:
            lat = float(dados[0]["lat"])
            lon = float(dados[0]["lon"])
            return lat, lon

    except Exception as e:
        print(f"Erro ao obter coordenadas para {cidade}, {pais}: {e}")

    return None, None