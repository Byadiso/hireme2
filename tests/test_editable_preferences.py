from hiremed.preferences import Preferences, evaluate, save_preferences, load_preferences


def test_preferences_persist_and_filter(tmp_path, monkeypatch):
    monkeypatch.setenv('HIREMED_DB', str(tmp_path / 'prefs.sqlite3'))
    monkeypatch.delenv('DATABASE_URL', raising=False)
    custom = Preferences(country='PL', language='pl', minimum_monthly_gross_pln=11000,
                         arrangements=('hybrid',), work_authorized=True)
    save_preferences(custom)
    assert load_preferences() == custom
    job = {'country': 'PL', 'location': 'Warsaw', 'language': 'pl',
           'arrangement': 'hybrid', 'salary_monthly_gross_pln': 12000}
    assert evaluate(job)['allowed']
    assert evaluate({**job, 'salary_monthly_gross_pln': 9500})['rejected']
    assert evaluate({**job, 'arrangement': 'remote'})['rejected']


def test_default_preferences_when_not_saved(tmp_path, monkeypatch):
    monkeypatch.setenv('HIREMED_DB', str(tmp_path / 'prefs.sqlite3'))
    monkeypatch.delenv('DATABASE_URL', raising=False)
    assert load_preferences().minimum_monthly_gross_pln == 8000
