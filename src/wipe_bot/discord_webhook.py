"""Publicar y editar un mensaje mediante un webhook de Discord.

Un webhook solo puede editar mensajes que él mismo publicó.
La URL del webhook es un secreto: nunca se imprime ni se registra.
"""
from __future__ import annotations

import requests

TIMEOUT = 15


def _payload(content: str) -> dict:
    # allowed_mentions vacío: ningún @ del texto notifica a nadie.
    return {"content": content, "allowed_mentions": {"parse": []}}


def post_message(webhook_url: str, content: str, username: str = "Calendario de Wipes") -> str:
    """Publica un mensaje nuevo y devuelve su id."""
    body = _payload(content) | {"username": username}
    resp = requests.post(webhook_url, params={"wait": "true"}, json=body, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()["id"]


def edit_message(webhook_url: str, message_id: str, content: str) -> None:
    resp = requests.patch(
        f"{webhook_url}/messages/{message_id}", json=_payload(content), timeout=TIMEOUT
    )
    if resp.status_code == 404:
        raise RuntimeError(
            "Mensaje no encontrado: ¿MESSAGE_ID es de un mensaje publicado por este webhook? "
            "Ejecuta con --init para crear uno nuevo."
        )
    resp.raise_for_status()
