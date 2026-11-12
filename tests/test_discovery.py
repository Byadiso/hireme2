from datetime import datetime, timezone
from hiremed import discovery


def test_discovery_shared_pipeline(monkeypatch):
    saved=[]
    monkeypatch.setattr(discovery,'jobs_from_adzuna',lambda roles,limit,country="PL":[{'id':'test:1','title':'Support','company':'Acme','description':'English remote IT support','location':'Poland','salary_monthly_gross_pln':9000,'language':'en','arrangement':'remote','url':'https://example.com','posted_at':datetime.now(timezone.utc).isoformat()}])
    monkeypatch.setattr(discovery,'assess',lambda profile,job:{'score':90,'eligible':True,'mandatory_met':['IT support']})
    monkeypatch.setattr(discovery,'save',lambda job,assessment,policy:saved.append(job['id']))
    results=discovery.discover({'roles':['IT Support'],'skills':['IT support']})
    assert len(results)==1 and results[0]['policy']['allowed']
    assert saved==['test:1']


def test_discovery_requires_profile():
    import pytest
    with pytest.raises(ValueError,match='Upload'):
        discovery.discover(None)


def test_search_updates_report_with_its_own_results(monkeypatch, tmp_path):
    from hiremed import agent
    monkeypatch.setenv('HIREMED_DB', str(tmp_path / 'search.sqlite'))
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.setattr(discovery, 'jobs_from_adzuna', lambda roles, limit, country='PL': [
        {'id': '90', 'title': 'IT Specialist', 'company': 'Egis Group', 'description': 'IT Support', 'url': 'https://example.com/90','posted_at':datetime.now(timezone.utc).isoformat()}])
    monkeypatch.setattr(discovery, 'assess', lambda profile, job: {'score': 90, 'eligible': False})
    monkeypatch.setattr(discovery, 'save', lambda *args: None)
    discovery.discover({'roles': ['IT Specialist']})
    report = agent.load_run_report()
    assert report['run_type'] == 'job discovery'
    assert report['total'] == 1
    assert report['strong_matches'] == 1
    assert report['highlights'][0]['company'] == 'Egis Group'
