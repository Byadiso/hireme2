import json
from unittest.mock import Mock
from hiremed import ai_provider


def test_groq_first_and_gemini_fallback(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','groq')
    monkeypatch.setenv('AI_FALLBACK_PROVIDER','gemini')
    monkeypatch.setenv('GROQ_API_KEY','test')
    monkeypatch.setenv('GEMINI_API_KEY','test')
    calls=[]
    def fail(*args):
        calls.append('groq')
        raise RuntimeError('quota')
    def success(*args):
        calls.append('gemini')
        return {'roles':['Support']}
    monkeypatch.setattr(ai_provider,'_groq',fail)
    monkeypatch.setattr(ai_provider,'_gemini',success)
    assert ai_provider.llm_json('system','user') == {'roles':['Support']}
    assert calls == ['groq','gemini']


def test_groq_json_response(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY','test')
    monkeypatch.setenv('GROQ_MODEL','openai/gpt-oss-20b')
    resp=Mock()
    resp.json.return_value={'choices':[{'message':{'content':'{"skills":["python"]}'}}]}
    resp.raise_for_status.return_value=None
    monkeypatch.setattr(ai_provider.requests,'post',lambda *a,**kw: resp)
    assert ai_provider._groq('system','user')['skills']==['python']


def test_no_provider(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY',raising=False)
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    monkeypatch.delenv('GOOGLE_API_KEY',raising=False)
    assert ai_provider.llm_json('a','b') is None
