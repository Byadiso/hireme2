from hiremed import agent


def test_run_report_empty():
    report = agent.summarize_run({'queries': ['IT Support']}, [])
    assert report['total'] == 0
    assert report['eligible'] == 0
    assert 'No vacancies' in report['headline']


def test_run_report_counts_and_reasons():
    results = [
        {'outcome': 'eligible', 'job': {'id': '1', 'title': 'Support', 'company': 'A', 'url': 'https://example.com'}, 'assessment': {'score': 85}, 'policy': {'reasons': [], 'unknown': []}},
        {'outcome': 'review', 'job': {'id': '2'}, 'assessment': {}, 'policy': {'reasons': [], 'unknown': ['Gross monthly salary unconfirmed']}},
        {'outcome': 'rejected', 'job': {'id': '3'}, 'assessment': {}, 'policy': {'reasons': ['Work arrangement not selected'], 'unknown': []}},
    ]
    report = agent.summarize_run({'queries': ['Support'], 'planner': 'gemini'}, results)
    assert (report['total'], report['eligible'], report['review'], report['rejected']) == (3, 1, 1, 1)
    assert report['highlights'][0]['title'] == 'Support'
    assert len(report['blockers']) == 2


def test_report_persists(tmp_path, monkeypatch):
    monkeypatch.setenv('HIREMED_DB', str(tmp_path / 'agent.sqlite'))
    monkeypatch.delenv('DATABASE_URL', raising=False)
    assert agent.load_run_report() is None
    report = agent.summarize_run({'queries': []}, [])
    agent.save_run_report(report)
    assert agent.load_run_report()['headline'] == report['headline']


def test_high_score_unverified_is_reported_as_strong_match():
    results = [{'outcome': 'review', 'job': {'id': '90', 'title': 'IT Specialist', 'company': 'Egis Group', 'url': 'https://example.com/90'}, 'assessment': {'score': 90, 'eligible': False}, 'policy': {'unknown': ['Salary unconfirmed'], 'reasons': []}}]
    report = agent.summarize_run({'queries': ['IT Specialist']}, results)
    assert report['total'] == 1
    assert report['strong_matches'] == 1
    assert report['eligible'] == 0
    assert report['highlights'][0]['score'] == 90
    assert report['highlights'][0]['outcome'] == 'review'
    assert 'Discovered 1 vacancies' in report['headline']


def test_rejected_high_score_remains_visible_but_not_eligible():
    results = [{'outcome': 'rejected', 'job': {'id': 'x', 'title': 'Specialist'}, 'assessment': {'score': 85}, 'policy': {'reasons': ['On-site only'], 'unknown': []}}]
    report = agent.summarize_run({'queries': []}, results)
    assert report['strong_matches'] == 0
    assert report['eligible'] == 0
    assert report['rejected'] == 1


def test_custom_threshold():
    results = [{'outcome': 'review', 'job': {'id': '1'}, 'assessment': {'score': 75}, 'policy': {}}]
    assert agent.summarize_run({}, results, strong_match_threshold=70)['strong_matches'] == 1
    assert agent.summarize_run({}, results, strong_match_threshold=80)['strong_matches'] == 0
