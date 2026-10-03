"""Punto de entrada.

  python -m wipe_bot --dry-run   # solo imprime el mensaje, no toca Discord
  python -m wipe_bot --init      # publica el mensaje y muestra su MESSAGE_ID
  python -m wipe_bot             # edita el mensaje existente (uso normal / cron)

El modo normal no solo edita una vez: si el wipe mas cercano de cualquier
servidor esta a menos de 1 hora, se queda despierto reeditando mas seguido
mientras se acerca (30 -> 10 -> 5 -> 1 min) en vez de esperar a que el cron
horario vuelva a llamarlo. Si nada esta cerca, edita una vez y sale.

Tambien borra, en cada corrida, cualquier otro mensaje del canal que no sea el
del calendario (p. ej. uno publicado a mano) -- para eso hace falta ademas un
bot de Discord con permiso "Gestionar mensajes" (DISCORD_BOT_TOKEN, CHANNEL_ID);
si esas dos variables no estan, simplemente se omite esa limpieza.

Variables de entorno: WEBHOOK_URL (secreto), MESSAGE_ID,
DISCORD_BOT_TOKEN (secreto, opcional), CHANNEL_ID (opcional).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from .discord_bot import DiscordBotError, purge_other_messages
from .discord_webhook import edit_message, post_message
from .render import render_message
from .schedule import ramp_interval, seconds_until_next, utc_now

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "schedule.json"

# Tope de seguridad: nunca se queda corriendo mas que esto en una sola invocacion
# (el workflow tiene timeout-minutes acorde a esto, con margen).
MAX_LOOP_SECONDS = 65 * 60


def _run_update_loop(config_path: Path, webhook_url: str, message_id: str) -> None:
    deadline = time.monotonic() + MAX_LOOP_SECONDS
    while True:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        now = utc_now()
        edit_message(webhook_url, message_id, render_message(config, now))

        remaining = seconds_until_next(config, now)
        step = ramp_interval(remaining)
        time_left = deadline - time.monotonic()
        if step is None or time_left <= 0:
            return
        sleep_for = max(5.0, min(step, remaining, time_left))
        time.sleep(sleep_for)


def main(argv: list[str] | None = None) -> int:
    # En Windows la consola suele ser cp1252 y no sabe imprimir emojis (🔄, 🟢...);
    # forzamos UTF-8 en stdout/stderr para que --dry-run y --init no truenen por eso.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass

    parser = argparse.ArgumentParser(description="Actualiza el calendario de wipes en Discord")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="solo mostrar el mensaje")
    mode.add_argument("--init", action="store_true", help="publicar el mensaje inicial")
    args = parser.parse_args(argv)

    config = json.loads(args.config.read_text(encoding="utf-8"))
    text = render_message(config, utc_now())

    if args.dry_run:
        print(text)
        return 0

    webhook = os.environ.get("WEBHOOK_URL")
    if not webhook:
        print("Falta la variable de entorno WEBHOOK_URL", file=sys.stderr)
        return 2

    if args.init:
        message_id = post_message(webhook, text)
        print(f"Mensaje publicado. Guarda este valor como MESSAGE_ID: {message_id}")
        return 0

    message_id = os.environ.get("MESSAGE_ID")
    if not message_id:
        print("Falta MESSAGE_ID (ejecuta primero con --init)", file=sys.stderr)
        return 2

    bot_token = os.environ.get("DISCORD_BOT_TOKEN")
    channel_id = os.environ.get("CHANNEL_ID")
    if bot_token and channel_id:
        try:
            borrados = purge_other_messages(bot_token, channel_id, message_id)
            if borrados:
                print(f"Limpieza: se borraron {borrados} mensaje(s) ajenos al calendario.")
        except DiscordBotError as exc:
            print(f"Aviso: fallo la limpieza del canal ({exc}); sigo con la edicion normal.", file=sys.stderr)
    else:
        print("Limpieza del canal desactivada (faltan DISCORD_BOT_TOKEN / CHANNEL_ID).")

    _run_update_loop(args.config, webhook, message_id)
    print("Calendario actualizado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
