import csv
from datetime import datetime, timezone
import json
from hiremed import agent
from hiremed.repository import list_jobs


def test_plan_fallback(monkeypatch):
    monkeypatch.setattr(agent, 'llm_json', lambda *_: None)
    plan = agent.plan_search({'roles': ['IT Support', 'Helpdesk'], 'skills': ['Linux']})
    assert plan['queries'] == ['IT Support', 'Helpdesk']
    assert plan['planner'] == 'profile_fallback'


def test_investigation_rejects_invented_evidence(monkeypatch):
    monkeypatch.setattr(agent, 'llm_json', lambda *_: {'evidence': ['Salary 9000 PLN', 'Remote'], 'unknown': [], 'summary': 'ok'})
    result = agent.investigate({}, {'description': 'This role is Remote only.'})
    assert result['evidence'] == ['Remote']


def test_agent_csv_pipeline_and_activity(tmp_path, monkeypatch):
    monkeypatch.setenv('HIREMED_DB', str(tmp_path / 'jobs.sqlite'))
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.setattr(agent, 'llm_json', lambda *_: None)
    monkeypatch.setattr(agent, 'assess', lambda *_: {'score': 80, 'eligible': True, 'mandatory_met': ['Linux'], 'mandatory_missing': [], 'mandatory_unknown': []})
    path = tmp_path / 'jobs.csv'
    with path.open('w', newline='', encoding='utf8') as f:
        writer = csv.DictWriter(f, fieldnames=['id','title','company','url','description','location','salary_monthly_gross_pln','language','arrangement','posted_at'])
        writer.writeheader()
        writer.writerow({'id':'job1','title':'IT Support','company':'Example','url':'https://example.com/1','description':'Linux helpdesk remote','location':'Warsaw, Poland','salary_monthly_gross_pln':'9000','language':'en','arrangement':'remote','posted_at':datetime.now(timezone.utc).isoformat()})
        writer.writerow({'id':'job2','title':'IT Support','company':'Example','url':'https://example.com/2','description':'Office only','location':'Warsaw, Poland','salary_monthly_gross_pln':'7000','language':'en','arrangement':'onsite','posted_at':datetime.now(timezone.utc).isoformat()})
    output = agent.run_agent({'roles':['IT Support'],'skills':['Linux']},csv_path=str(path))
    assert len(output['results']) == 2
    assert output['results'][0]['outcome'] == 'eligible'
    assert output['results'][1]['outcome'] == 'rejected'
    assert len(list_jobs()) == 2
    assert {'plan','discover','evaluate','complete'}.issubset({x['action'] for x in agent.recent_actions()})
    agent.record_feedback('job1','relevant')
    assert agent.feedback_summary()['relevant'] == 1


def test_draft_storage(tmp_path, monkeypatch):
    monkeypatch.setenv('HIREMED_DB', str(tmp_path / 'jobs.sqlite'))
    monkeypatch.delenv('DATABASE_URL', raising=False)
    agent.save_draft('a', {'cover_letter':'Dear employer', 'cv_summary':'Linux support'})
    assert agent.load_draft('a')['cover_letter'] == 'Dear employer'
