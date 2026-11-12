from datetime import datetime, timezone, timedelta
from hiremed.freshness import freshness

NOW = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)

def test_freshness_boundaries():
    assert freshness({'posted_at': (NOW-timedelta(days=7)).isoformat()}, NOW)['allowed']
    assert not freshness({'posted_at': (NOW-timedelta(days=7,seconds=1)).isoformat()}, NOW)['allowed']
    assert not freshness({'posted_at': (NOW+timedelta(seconds=1)).isoformat()}, NOW)['allowed']
    assert not freshness({'posted_at': None}, NOW)['allowed']
    assert not freshness({'posted_at': 'yesterday'}, NOW)['allowed']
    assert not freshness({'posted_at': '2026-11-08'}, NOW)['allowed']

def test_original_date_overrides_repost():
    assert not freshness({'posted_at': NOW.isoformat(), 'original_posted_at': (NOW-timedelta(days=20)).isoformat()}, NOW)['allowed']

def test_offset_timestamp():
    assert freshness({'posted_at': '2026-11-08T13:00:00+01:00'}, NOW)['allowed']
