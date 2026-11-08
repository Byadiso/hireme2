from hiremed.core import profile_from_cv,assess
from hiremed.apply import submit_configured_form

def test_keyword_fallback(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    p=profile_from_cv('Python SQL Linux experience')
    assert 'python' in p['skills']
    a=assess(p,{'description':'Python developer'})
    assert a['eligible'] is False
    assert a['mandatory_unknown']

def test_submission_defaults_to_blocked(monkeypatch,tmp_path):
    monkeypatch.delenv('HIREMED_AUTO_APPLY',raising=False)
    class FakeConn: pass
    assert submit_configured_form(FakeConn(),{'id':'1','url':'https://example.com'}, {'eligible':True,'method':'llm'})['status']=='blocked'
