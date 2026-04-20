import requests
from config import API_URL, API_TOKEN


def enviar_para_api(payload):
    response = requests.post(
        API_URL,
        json=payload,
        headers={
            "Authorization": f"Token {API_TOKEN}"
        },
        timeout=10,
    )
    return response.json()