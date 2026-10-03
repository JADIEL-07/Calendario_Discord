import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wipe_bot.render import render_message  # noqa: E402
from wipe_bot.schedule import next_occurrences  # noqa: E402

CONFIG = json.loads(
    (Path(__file__).resolve().parents[1] / "config" / "schedule.json").read_text(encoding="utf-8")
)


def utc(*a):
    return datetime(*a, tzinfo=timezone.utc)


def test_weekly_dst_paris_summer():
    ev = {"type": "weekly", "label": "x", "weekday": "fri", "time": "19:00", "tz": "Europe/Paris"}
    (_, dt), = next_occurrences(ev, utc(2026, 10, 3, 12))
    assert dt.astimezone(timezone.utc) == utc(2026, 10, 9, 17)  # CEST = UTC+2


def test_weekly_dst_paris_winter():
    ev = {"type": "weekly", "label": "x", "weekday": "fri", "time": "19:00", "tz": "Europe/Paris"}
    (_, dt), = next_occurrences(ev, utc(2026, 11, 1, 12))
    assert dt.astimezone(timezone.utc) == utc(2026, 11, 6, 18)  # CET = UTC+1


def test_monthly_rolls_to_next_month():
    ev = {"type": "monthly", "label": "x", "day": 11, "time": "10:00", "tz": "America/Bogota"}
    (_, dt), = next_occurrences(ev, utc(2026, 10, 3))
    assert dt.astimezone(timezone.utc) == utc(2026, 10, 11, 15)
    (_, dt), = next_occurrences(ev, utc(2026, 10, 12))
    assert dt.astimezone(timezone.utc) == utc(2026, 11, 11, 15)


def test_once_expires():
    ev = {"type": "once", "label": "x", "at": "2026-10-07T11:00", "tz": "America/Bogota"}
    assert len(next_occurrences(ev, utc(2026, 10, 3))) == 1
    assert next_occurrences(ev, utc(2026, 10, 8)) == []


def test_render_fits_and_all_servers_present():
    text = render_message(CONFIG, utc(2026, 10, 3, 15))
    assert len(text) <= 2000
    for s in CONFIG["servers"]:
        assert s["name"] in text
    assert re.search(r"<t:\d+:R>", text)
