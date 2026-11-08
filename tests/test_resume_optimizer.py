from io import BytesIO
from docx import Document
from pypdf import PdfReader
from hiremed.resume_optimizer import choose_evidence, make_package, to_docx, to_pdf

CV = 'Jane Doe\nIT Support Specialist\nTroubleshooting Windows and Active Directory incidents for users.\nPython automation and scripting for internal reporting.\nCustomer service and ticket resolution in Jira.\n'
JOB = {'id': 'abc', 'title': 'IT Support Specialist', 'company': 'Example', 'description': 'Windows Active Directory troubleshooting and ticket resolution'}


def test_only_exact_original_lines_are_highlighted(monkeypatch):
    monkeypatch.setattr('hiremed.resume_optimizer.llm_json', lambda *args: {'indices': [999, 2, 2]})
    lines = choose_evidence(CV, JOB)
    assert lines == ['Troubleshooting Windows and Active Directory incidents for users.']


def test_fallback_no_ai(monkeypatch):
    monkeypatch.setattr('hiremed.resume_optimizer.llm_json', lambda *args: None)
    package = make_package(CV, JOB)
    assert package['original'] == CV
    assert all(x in CV.splitlines() for x in package['evidence'])


def test_both_download_formats(monkeypatch):
    monkeypatch.setattr('hiremed.resume_optimizer.llm_json', lambda *args: None)
    package = make_package(CV, JOB)
    docx = to_docx(package)
    pdf = to_pdf(package)
    assert 'Customer service and ticket resolution in Jira.' in [p.text for p in Document(BytesIO(docx)).paragraphs]
    assert len(PdfReader(BytesIO(pdf)).pages) >= 1
    assert pdf.startswith(b'%PDF')


def test_no_original_cv_is_error():
    import pytest
    with pytest.raises(ValueError):
        make_package('', JOB)


def test_professional_cv_has_no_excerpts_appendix():
    p = make_package(CV, JOB, use_ai=False)
    text = '\n'.join(x.text for x in Document(BytesIO(to_docx(p))).paragraphs)
    assert 'Job-tailored resume' not in text
    assert 'Complete original CV' not in text
    assert 'Relevant experience and skills (from original CV)' not in text
    assert text.count('Troubleshooting Windows and Active Directory') == 1


def test_reflow_preserves_skill_categories():
    from hiremed.resume_optimizer import _sections
    cv = ('Jane Doe\nTECHNICAL SKILLS\nMonitoring & operations: Splunk, TIP, ServiceNow, '
          'Windows/Linux server monitoring, database backup\nmonitoring, scheduled jobs\n'
          'IT support & infrastructure: Active Directory, DNS, VPN\n')
    sections = _sections(cv)
    assert len(sections['skills']) == 2
    assert sections['skills'][0].endswith('monitoring, scheduled jobs')
