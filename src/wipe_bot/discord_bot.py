"""Limpieza del canal usando un BOT de Discord (no el webhook).

Un webhook jamas puede borrar un mensaje que no publico el mismo; eso lo
bloquea Discord sin excepcion. Un bot con permiso "Gestionar mensajes" si
puede. Se usa unicamente para esto: borrar en el canal cualquier mensaje que
no sea el del calendario (`keep_message_id`), sin tocar ese.
"""
from __future__ import annotations

import time

import requests

API = "https://discord.com/api/v10"
TIMEOUT = 15
BULK_MAX_AGE_DAYS = 14  # la API de bulk-delete rechaza mensajes mas viejos que esto
DISCORD_EPOCH_MS = 1420070400000  # 2015-01-01, epoca de los ids ("snowflakes") de Discord


class DiscordBotError(RuntimeError):
    """Una llamada a la API de bot de Discord fallo."""


def _headers(bot_token: str) -> dict:
    return {"Authorization": f"Bot {bot_token}"}


def _snowflake_timestamp(snowflake: str) -> float:
    """Instante (segundos unix) codificado en un id de Discord. No hace falta
    pedirlo a la API: viene metido en los primeros bits del propio id."""
    ms = (int(snowflake) >> 22) + DISCORD_EPOCH_MS
    return ms / 1000.0


def _fetch_messages(bot_token: str, channel_id: str, max_pages: int = 5) -> list[dict]:
    messages: list[dict] = []
    before = None
    for _ in range(max_pages):
        params = {"limit": 100}
        if before:
            params["before"] = before
        resp = requests.get(
            f"{API}/channels/{channel_id}/messages",
            headers=_headers(bot_token),
            params=params,
            timeout=TIMEOUT,
        )
        if not resp.ok:
            raise DiscordBotError(f"no se pudo listar mensajes ({resp.status_code}): {resp.text}")
        page = resp.json()
        if not page:
            break
        messages.extend(page)
        before = page[-1]["id"]
        if len(page) < 100:
            break
    return messages


def _delete_one(bot_token: str, channel_id: str, message_id: str) -> None:
    resp = requests.delete(
        f"{API}/channels/{channel_id}/messages/{message_id}",
        headers=_headers(bot_token),
        timeout=TIMEOUT,
    )
    if resp.status_code == 429:
        time.sleep(resp.json().get("retry_after", 1))
        _delete_one(bot_token, channel_id, message_id)
        return
    if resp.status_code not in (204, 404):
        raise DiscordBotError(f"no se pudo borrar {message_id} ({resp.status_code}): {resp.text}")


def _bulk_delete(bot_token: str, channel_id: str, message_ids: list[str]) -> None:
    resp = requests.post(
        f"{API}/channels/{channel_id}/messages/bulk-delete",
        headers=_headers(bot_token),
        json={"messages": message_ids},
        timeout=TIMEOUT,
    )
    if resp.status_code == 429:
        time.sleep(resp.json().get("retry_after", 1))
        _bulk_delete(bot_token, channel_id, message_ids)
        return
    if not resp.ok:
        raise DiscordBotError(f"no se pudo borrar en bloque ({resp.status_code}): {resp.text}")


def purge_other_messages(bot_token: str, channel_id: str, keep_message_id: str) -> int:
    """Borra en el canal todo lo que no sea `keep_message_id`. Devuelve cuantos borro.

    Los mensajes de hasta 14 dias se borran en bloques de hasta 100 (bulk-delete);
    los mas viejos hay que borrarlos uno por uno, porque la API de Discord no
    permite bulk-delete sobre mensajes de mas de 14 dias.
    """
    messages = _fetch_messages(bot_token, channel_id)
    to_delete = [m["id"] for m in messages if m["id"] != keep_message_id]
    if not to_delete:
        return 0

    cutoff = time.time() - BULK_MAX_AGE_DAYS * 86400
    recent = [mid for mid in to_delete if _snowflake_timestamp(mid) >= cutoff]
    old = [mid for mid in to_delete if _snowflake_timestamp(mid) < cutoff]

    for i in range(0, len(recent), 100):
        batch = recent[i : i + 100]
        if len(batch) >= 2:
            _bulk_delete(bot_token, channel_id, batch)
        else:
            for mid in batch:
                _delete_one(bot_token, channel_id, mid)

    for mid in old:
        _delete_one(bot_token, channel_id, mid)

    return len(to_delete)
