"""User-editable job search preferences, shared by dashboard, agent and scheduler."""
import json
import os
import re
from dataclasses import asdict, dataclass
from .storage import _connect

@dataclass(frozen=True)
class Preferences:
    country: str = 'PL'
    language: str = 'en'
    minimum_monthly_gross_pln: int = 8000
    arrangements: tuple = ('remote', 'hybrid')
    work_authorized: bool = True

DEFAULT = Preferences()


def validate(p):
    if not isinstance(p, Preferences):
        raise ValueError('Invalid preferences')
    country = p.country.strip().upper()
    if not re.fullmatch(r'[A-Z]{2}', country):
        raise ValueError('Country must be a two-letter ISO country code')
    language = p.language.strip().lower()
    if not re.fullmatch(r'[a-z]{2}', language):
        raise ValueError('Language must be a two-letter code')
    if not 0 <= p.minimum_monthly_gross_pln <= 1000000:
        raise ValueError('Monthly gross salary must be between 0 and 1,000,000 PLN')
    arrangements = tuple(dict.fromkeys(p.arrangements))
    if not arrangements or any(a not in ('remote', 'hybrid', 'onsite') for a in arrangements):
        raise ValueError('Select at least one valid work arrangement')
    return Preferences(country, language, int(p.minimum_monthly_gross_pln), arrangements, bool(p.work_authorized))


def save_preferences(preferences):
    p = validate(preferences)
    conn, pg = _connect()
    try:
        conn.execute('CREATE TABLE IF NOT EXISTS search_preferences (id INTEGER PRIMARY KEY, settings_json TEXT NOT NULL)')
        placeholder = '%s' if pg else '?'
        conn.execute(f'INSERT INTO search_preferences(id,settings_json) VALUES (1,{placeholder}) '
                     'ON CONFLICT(id) DO UPDATE SET settings_json=excluded.settings_json',
                     (json.dumps(asdict(p)),))
        conn.commit()
    finally:
        conn.close()
    return p


def load_preferences():
    conn, _ = _connect()
    try:
        conn.execute('CREATE TABLE IF NOT EXISTS search_preferences (id INTEGER PRIMARY KEY, settings_json TEXT NOT NULL)')
        conn.commit()
        row = conn.execute('SELECT settings_json FROM search_preferences WHERE id=1').fetchone()
        if not row:
            return DEFAULT
        data = json.loads(row[0])
        data['arrangements'] = tuple(data.get('arrangements', DEFAULT.arrangements))
        return validate(Preferences(**data))
    finally:
        conn.close()


def evaluate(job, preferences=None):
    """Conservative policy: missing salary/language/location/arrangement requires review."""
    p = preferences if preferences is not None else load_preferences()
    reasons, unknown = [], []
    title = (job.get('title') or '').lower()
    description = (job.get('description') or '').lower()
    content = title + ' ' + description
    location = (job.get('location') or '').lower()
    country = (job.get('country') or '').strip().upper()
    # For Poland, accept common city names; for other countries require explicit country metadata.
    polish_places = ('poland', 'polska', 'pozna', 'warsaw', 'warszawa', 'krak', 'wroc', 'gdansk', 'gdań', 'łódź', 'lodz', 'szczecin', 'katowice', 'lublin', 'rzesz')
    if country:
        if country != p.country:
            reasons.append('Country does not match selected country')
    elif p.country == 'PL':
        if not location:
            unknown.append('Location in Poland not confirmed')
        elif not any(x in location for x in polish_places):
            unknown.append('Location in Poland not confirmed')
    elif p.country.lower() not in location.lower():
        unknown.append('Country not confirmed')

    arrangement = (job.get('arrangement') or '').lower()
    if arrangement in ('on-site', 'office'):
        arrangement = 'onsite'
    if arrangement in ('remote', 'hybrid', 'onsite'):
        if arrangement not in p.arrangements:
            reasons.append('Work arrangement not selected')
    elif re.search(r'\b(onsite only|on-site only|office only|100% onsite)\b', content):
        if 'onsite' not in p.arrangements:
            reasons.append('On-site-only position')
    else:
        unknown.append('Work arrangement unconfirmed')

    salary = job.get('salary_monthly_gross_pln')
    if salary is None:
        unknown.append('Gross monthly salary unconfirmed')
    else:
        try:
            if float(salary) < p.minimum_monthly_gross_pln:
                reasons.append(f'Salary below {p.minimum_monthly_gross_pln:,} PLN gross/month')
        except (TypeError, ValueError):
            unknown.append('Salary format unverified')

    language = (job.get('language') or '').strip().lower()
    aliases = {'en': {'en', 'english'}, 'pl': {'pl', 'polish', 'polski'}}
    if language and language not in aliases.get(p.language, {p.language}):
        reasons.append('Job language does not match selected language')
    elif not language:
        unknown.append('Job language unconfirmed')
    return {'allowed': not reasons and not unknown, 'rejected': bool(reasons), 'reasons': reasons, 'unknown': unknown}
