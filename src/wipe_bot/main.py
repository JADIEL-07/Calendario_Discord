"""Punto de entrada.

  python -m wipe_bot --dry-run   # solo imprime el mensaje, no toca Discord
  python -m wipe_bot --init      # publica el mensaje y muestra su MESSAGE_ID
  python -m wipe_bot             # edita el mensaje existente (uso normal / cron)

Variables de entorno: WEBHOOK_URL (secreto), MESSAGE_ID.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .discord_webhook import edit_message, post_message
from .render import render_message
from .schedule import utc_now

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "schedule.json"


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
    edit_message(webhook, message_id, text)
    print("Calendario actualizado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
