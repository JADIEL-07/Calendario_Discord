"""Construye el texto del mensaje a partir de la configuración y la hora actual."""
from __future__ import annotations

from datetime import datetime

from .schedule import next_occurrences

DISCORD_LIMIT = 2000


def _stamp(dt: datetime) -> str:
    unix = int(dt.timestamp())
    # :f -> fecha completa en la zona de quien lo ve; :R -> contador relativo en vivo
    return f"<t:{unix}:f> · <t:{unix}:R>"


def render_message(config: dict, now: datetime) -> str:
    lines = [config["title"], config["intro"], ""]
    for server in config["servers"]:
        rows: list[tuple[str, datetime]] = []
        for event in server["events"]:
            rows.extend(next_occurrences(event, now))
        rows.sort(key=lambda r: r[1])
        lines.append(f'{server["emoji"]} **{server["name"]}** · {server["note"]}')
        if rows:
            lines.extend(f"• {label}: {_stamp(dt)}" for label, dt in rows)
        else:
            lines.append("• sin próxima fecha conocida (actualizar config/schedule.json)")
        lines.append("")
    if config.get("no_data"):
        lines.append("🔴 Sin datos: " + ", ".join(config["no_data"]) + ".")
    lines.append(f"Última actualización: <t:{int(now.timestamp())}:R>")
    text = "\n".join(lines)
    if len(text) > DISCORD_LIMIT:
        raise ValueError(f"mensaje de {len(text)} caracteres supera el límite de {DISCORD_LIMIT}")
    return text
