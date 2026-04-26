from __future__ import annotations

import requests
from django.conf import settings


class PaypalServiceError(Exception):
    pass


def _api_base_url() -> str:
    mode = str(getattr(settings, "PAYPAL_MODE", "sandbox") or "sandbox").strip().lower()
    if mode == "live":
        return "https://api-m.paypal.com"
    return "https://api-m.sandbox.paypal.com"


def _obter_access_token() -> str:
    if not getattr(settings, "PAYPAL_ENABLED", False):
        raise PaypalServiceError("PayPal está desativado na configuração da aplicação.")

    client_id = (getattr(settings, "PAYPAL_CLIENT_ID", "") or "").strip()
    client_secret = (getattr(settings, "PAYPAL_CLIENT_SECRET", "") or "").strip()
    if not client_id or not client_secret:
        raise PaypalServiceError("PAYPAL_CLIENT_ID/PAYPAL_CLIENT_SECRET em falta.")

    response = requests.post(
        f"{_api_base_url()}/v1/oauth2/token",
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        timeout=20,
    )
    if response.status_code >= 400:
        raise PaypalServiceError(f"Falha a obter token PayPal (HTTP {response.status_code}).")

    data = response.json()
    token = data.get("access_token")
    if not token:
        raise PaypalServiceError("Resposta PayPal inválida ao obter token.")
    return token


def criar_ordem_paypal(
    *,
    referencia_local: str,
    valor: str,
    moeda: str,
    descricao: str,
    return_url: str,
    cancel_url: str,
) -> dict:
    token = _obter_access_token()
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": referencia_local,
                "description": descricao[:127],
                "amount": {
                    "currency_code": moeda,
                    "value": valor,
                },
            }
        ],
        "application_context": {
            "return_url": return_url,
            "cancel_url": cancel_url,
            "landing_page": "LOGIN",
            "user_action": "PAY_NOW",
        },
    }

    response = requests.post(
        f"{_api_base_url()}/v2/checkout/orders",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=20,
    )
    if response.status_code >= 400:
        raise PaypalServiceError(f"Falha ao criar ordem PayPal (HTTP {response.status_code}).")

    data = response.json()
    order_id = data.get("id")
    approve_url = None
    for link in data.get("links", []):
        if link.get("rel") == "approve":
            approve_url = link.get("href")
            break

    if not order_id or not approve_url:
        raise PaypalServiceError("Resposta PayPal inválida ao criar ordem.")

    return {
        "order_id": order_id,
        "approve_url": approve_url,
        "status": data.get("status"),
        "raw": data,
    }


def capturar_ordem_paypal(order_id: str) -> dict:
    token = _obter_access_token()
    response = requests.post(
        f"{_api_base_url()}/v2/checkout/orders/{order_id}/capture",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=20,
    )
    if response.status_code >= 400:
        raise PaypalServiceError(f"Falha ao capturar ordem PayPal (HTTP {response.status_code}).")

    data = response.json()
    return {
        "status": data.get("status"),
        "raw": data,
    }
