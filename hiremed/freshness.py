"""Strict, timezone-aware job freshness checks. Unknown dates never qualify."""
from datetime import datetime, timezone, timedelta, date

MAX_AGE_DAYS = 7

def parse_posted(value):
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    else:
        raw = str(value).strip()
        try:
            dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return None
    if dt.tzinfo is None:
        return None  # Naive dates cannot be safely interpreted across time zones.
    return dt.astimezone(timezone.utc)

def freshness(job, now=None):
    now = now or datetime.now(timezone.utc)
    # Evaluate every known date: a repost does not reset an older original posting.
    dates = [parse_posted(job.get(field)) for field in ('original_posted_at', 'posted_at')]
    valid = [value for value in dates if value is not None]
    posted = min(valid) if valid else None
    if posted is None:
        return {'allowed': False, 'reason': 'Posting date missing or unverifiable', 'posted_at': None}
    age = now - posted
    if age < timedelta(0):
        return {'allowed': False, 'reason': 'Posting date is in the future', 'posted_at': posted.isoformat()}
    if age > timedelta(days=MAX_AGE_DAYS):
        return {'allowed': False, 'reason': 'Job was posted more than 7 days ago', 'posted_at': posted.isoformat()}
    return {'allowed': True, 'reason': 'Posted within the last 7 days', 'posted_at': posted.isoformat(), 'age_days': round(age.total_seconds()/86400, 1)}
