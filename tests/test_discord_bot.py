import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wipe_bot import discord_bot  # noqa: E402


def _snowflake(age_days: float) -> str:
    """Construye un id de Discord valido que corresponde a hace `age_days` dias."""
    ms_since_epoch = int((time.time() - age_days * 86400) * 1000) - discord_bot.DISCORD_EPOCH_MS
    return str(ms_since_epoch << 22)


def test_snowflake_timestamp_roundtrip():
    sf = _snowflake(age_days=1)
    ts = discord_bot._snowflake_timestamp(sf)
    assert abs(ts - (time.time() - 86400)) < 2  # un par de segundos de margen


def test_purge_keeps_calendar_message(monkeypatch):
    keep = "keep-1"
    other_recent = _snowflake(age_days=0.1)
    messages = [{"id": keep}, {"id": other_recent}]

    monkeypatch.setattr(discord_bot, "_fetch_messages", lambda *a, **k: messages)

    bulk_calls = []
    monkeypatch.setattr(
        discord_bot, "_bulk_delete", lambda token, ch, ids: bulk_calls.append(ids)
    )
    single_calls = []
    monkeypatch.setattr(
        discord_bot, "_delete_one", lambda token, ch, mid: single_calls.append(mid)
    )

    deleted = discord_bot.purge_other_messages("tok", "chan", keep)

    assert deleted == 1
    assert keep not in bulk_calls and keep not in single_calls
    # con un solo mensaje "ajeno" de sobra, se borra individual (bulk pide >=2)
    assert single_calls == [other_recent]
    assert bulk_calls == []


def test_purge_nothing_to_delete(monkeypatch):
    monkeypatch.setattr(discord_bot, "_fetch_messages", lambda *a, **k: [{"id": "keep-1"}])
    assert discord_bot.purge_other_messages("tok", "chan", "keep-1") == 0


def test_purge_uses_bulk_for_two_or_more_recent(monkeypatch):
    keep = "keep-1"
    recents = [_snowflake(age_days=0.1), _snowflake(age_days=0.2)]
    monkeypatch.setattr(
        discord_bot, "_fetch_messages",
        lambda *a, **k: [{"id": keep}] + [{"id": m} for m in recents],
    )
    bulk_calls = []
    monkeypatch.setattr(discord_bot, "_bulk_delete", lambda token, ch, ids: bulk_calls.append(ids))
    monkeypatch.setattr(discord_bot, "_delete_one", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("no deberia borrar individual cuando hay >=2 recientes")
    ))

    deleted = discord_bot.purge_other_messages("tok", "chan", keep)

    assert deleted == 2
    assert bulk_calls == [recents]


def test_purge_old_messages_go_individually(monkeypatch):
    keep = "keep-1"
    old = _snowflake(age_days=20)  # mas de 14 dias: bulk-delete no lo acepta
    monkeypatch.setattr(
        discord_bot, "_fetch_messages", lambda *a, **k: [{"id": keep}, {"id": old}]
    )
    monkeypatch.setattr(discord_bot, "_bulk_delete", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("un mensaje viejo no deberia ir por bulk-delete")
    ))
    single_calls = []
    monkeypatch.setattr(discord_bot, "_delete_one", lambda token, ch, mid: single_calls.append(mid))

    deleted = discord_bot.purge_other_messages("tok", "chan", keep)

    assert deleted == 1
    assert single_calls == [old]
