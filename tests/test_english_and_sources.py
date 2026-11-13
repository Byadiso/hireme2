from datetime import datetime, timezone
from io import BytesIO
from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from pypdf import PdfReader
from hiremed.preferences import Preferences, evaluate
from hiremed.agent import summarize_run
from hiremed.resume_optimizer import make_package, to_docx, to_pdf
from hiremed.core import jobs_from_remotive


def test_explicit_polish_is_rejected():
    job = {'title': 'IT Support', 'description': 'English speaking team. Polish language required.',
           'location': 'Warsaw', 'country': 'PL', 'arrangement': 'remote',
           'salary_monthly_gross_pln': 12000, 'language': 'en'}
    decision = evaluate(job, Preferences())
    assert decision['rejected'] and 'Polish language required' in decision['reasons']
    job['description'] = 'English speaking team supporting Polish customers.'
    assert not evaluate(job, Preferences())['rejected']


def test_rejected_job_not_strong():
    results = [{'outcome':'rejected', 'assessment':{'score':90},
                'job':{'id':'a','title':'Support'}, 'policy':{'reasons':['Polish language required']}}]
    report = summarize_run({'queries':[]}, results)
    assert report['strong_matches'] == 0
    assert report['rejected'] == 1
    assert report['highlights'] == []


def test_contact_links_clickable_in_both_formats():
    original = ('Example Person\nIT Specialist\nPoland | GitHub | LinkedIn\n'
                'https://github.com/exampleperson\nhttps://linkedin.com/in/exampleperson\n'
                'PROFESSIONAL SUMMARY\nIT operations specialist.')
    package = make_package(original, {'title':'IT Specialist','description':'IT operations'}, use_ai=False)
    doc = Document(BytesIO(to_docx(package)))
    links = {r.target_ref for r in doc.part.rels.values() if r.reltype == RT.HYPERLINK}
    assert 'https://github.com/exampleperson' in links
    assert 'https://linkedin.com/in/exampleperson' in links
    reader = PdfReader(BytesIO(to_pdf(package)))
    urls = []
    for page in reader.pages:
        for ref in page.get('/Annots', []):
            urls.append(str(ref.get_object().get('/A', {}).get('/URI', '')))
    assert 'https://github.com/exampleperson' in urls
    assert 'https://linkedin.com/in/exampleperson' in urls


def test_remotive_filters_country(monkeypatch):
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {'jobs': [
                {'id':1,'title':'IT Support','url':'https://remotive.com/remote-jobs/1',
                 'publication_date':datetime.now(timezone.utc).isoformat(),
                 'candidate_required_location':'USA Only', 'description':'IT support'},
                {'id':2,'title':'IT Support','url':'https://remotive.com/remote-jobs/2',
                 'publication_date':datetime.now(timezone.utc).isoformat(),
                 'candidate_required_location':'Europe', 'description':'IT support'}]}
    monkeypatch.setattr('hiremed.core.requests.get', lambda *args, **kwargs: Response())
    jobs = jobs_from_remotive(['IT Support'], country='PL')
    assert len(jobs) == 1 and jobs[0]['id'] == 'remotive:2'
