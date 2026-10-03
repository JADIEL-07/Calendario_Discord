"""Cálculo de próximas fechas de wipe a partir de reglas de calendario.

Todas las reglas se definen en hora LOCAL de un huso IANA (p. ej. Europe/Paris),
así el cambio de horario de verano se aplica solo.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def _parse_time(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def _local(d: date, t: time, tz: ZoneInfo) -> datetime:
    """Fecha+hora local -> datetime con huso (respeta el horario de verano)."""
    return datetime.combine(d, t).replace(tzinfo=tz)


def _weekday(value: str | int) -> int:
    return WEEKDAYS[value.lower()] if isinstance(value, str) else int(value)


def _next_weekly_date(now: datetime, weekday: int, t: time, tz: ZoneInfo) -> date:
    """Primer día con ese weekday cuyo wipe (a esa hora) sea posterior a `now`."""
    local_now = now.astimezone(tz)
    day = local_now.date()
    for _ in range(8):
        if day.weekday() == weekday and _local(day, t, tz) > now:
            return day
        day += timedelta(days=1)
    raise RuntimeError("no se encontró fecha semanal")  # pragma: no cover


def next_occurrences(event: dict, now: datetime) -> list[tuple[str, datetime]]:
    """Devuelve [(etiqueta, instante)] de la próxima ocurrencia de cada evento.

    Un evento puede devolver varias filas (rotación) o ninguna (fecha ya pasada).
    `now` debe tener huso horario.
    """
    if now.tzinfo is None:
        raise ValueError("now debe tener huso horario")
    kind = event["type"]
    tz = ZoneInfo(event["tz"])

    if kind == "once":
        at = datetime.fromisoformat(event["at"]).replace(tzinfo=tz)
        return [(event["label"], at)] if at > now else []

    t = _parse_time(event["time"]) if "time" in event else None

    if kind == "weekly":
        day = _next_weekly_date(now, _weekday(event["weekday"]), t, tz)
        return [(event["label"], _local(day, t, tz))]

    if kind == "monthly":
        dom = int(event["day"])
        local_now = now.astimezone(tz)
        year, month = local_now.year, local_now.month
        for _ in range(14):  # salta meses donde el día no existe (p. ej. 31)
            try:
                candidate = _local(date(year, month, dom), t, tz)
            except ValueError:
                candidate = None
            if candidate is not None and candidate > now:
                return [(event["label"], candidate)]
            month += 1
            if month > 12:
                year, month = year + 1, 1
        raise RuntimeError("no se encontró fecha mensual")  # pragma: no cover

    if kind == "interval":
        anchor = date.fromisoformat(event["anchor"])
        step = int(event["every_days"])
        day = anchor
        if _local(anchor, t, tz) <= now:
            elapsed = (now.astimezone(tz).date() - anchor).days
            day = anchor + timedelta(days=(elapsed // step) * step)
            while _local(day, t, tz) <= now:
                day += timedelta(days=step)
        return [(event["label"], _local(day, t, tz))]

    if kind == "rotation":
        # Un clúster por semana, en orden fijo, empezando por cycle[0] en `anchor`.
        anchor = date.fromisoformat(event["anchor"])
        cycle: list[str] = event["cycle"]
        weekday = _weekday(event["weekday"])
        first = _next_weekly_date(now, weekday, t, tz)
        weeks_from_anchor = (first - anchor).days // 7
        rows = []
        for offset in range(len(cycle)):
            idx = (weeks_from_anchor + offset) % len(cycle)
            day = first + timedelta(weeks=offset)
            rows.append((cycle[idx], _local(day, t, tz)))
        return rows

    raise ValueError(f"tipo de evento desconocido: {kind}")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def seconds_until_next(config: dict, now: datetime) -> float | None:
    """Segundos hasta el wipe mas cercano de cualquier servidor, o None si ningun
    servidor tiene una proxima fecha (todos 'once' ya pasados, o sin eventos)."""
    best: datetime | None = None
    for server in config.get("servers", []):
        for event in server.get("events", []):
            for _, dt in next_occurrences(event, now):
                if best is None or dt < best:
                    best = dt
    return None if best is None else (best - now).total_seconds()


def ramp_interval(remaining: float | None) -> float | None:
    """Cada cuanto volver a editar el mensaje dentro de la misma corrida, segun lo
    cerca que este el proximo wipe. None = no hace falta loop, el siguiente disparo
    del cron (cada hora) ya se encarga.

    Tramos: > 1h -> None (sale) · 30min-1h -> cada 30min · 10-30min -> cada 10min ·
    5-10min -> cada 5min · <= 5min -> cada 1min.
    """
    if remaining is None or remaining > 3600:
        return None
    if remaining > 1800:
        return 1800.0
    if remaining > 600:
        return 600.0
    if remaining > 300:
        return 300.0
    return 60.0
