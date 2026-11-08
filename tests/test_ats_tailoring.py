from hiremed.ats_tailoring import ats_analysis, _safe_rewrite, rewrite_package
from hiremed.resume_optimizer import make_package

CV = ('Jane Doe\nIT Support Specialist\nPROFESSIONAL SUMMARY\n'
      'Experienced IT support specialist with Windows troubleshooting and user support.\n'
      'PROFESSIONAL EXPERIENCE\nAcme | IT Specialist | 2021 – Present\n'
      '• Resolved 500 Windows incidents using ServiceNow and Active Directory.\n')
JOB = {'id':'x', 'title':'IT Specialist', 'company':'Example',
       'description':'We require Windows troubleshooting, Active Directory, ServiceNow and user support. '
                     'The position involves incidents, monitoring and ticket triage with documentation.'}

def test_keywords_not_in_cv_are_not_claimed():
    a=ats_analysis(CV, JOB)
    assert 'servicenow' in a['matched_keywords']
    assert 'monitoring' in a['unverified_job_terms']

def test_unsupported_metric_and_tool_rejected():
    original='Resolved 500 Windows incidents using ServiceNow and Active Directory.'
    assert _safe_rewrite(original,'Resolved 1000 Windows incidents using ServiceNow and Active Directory.',CV)==original
    assert _safe_rewrite(original,'Resolved 500 Windows incidents using Kubernetes and Active Directory.',CV)==original

def test_ai_rewrites_and_change_log(monkeypatch):
    monkeypatch.setattr('hiremed.ats_tailoring.llm_json',lambda *a: {'rewrites': {'experience:0:0':'Using ServiceNow and Active Directory, resolved 500 Windows incidents.'}})
    p=make_package(CV,JOB,use_ai=False)
    rewrite_package(p,CV,JOB)
    assert p['ai_rewrite_status']=='rewritten'
    assert p['changes'][0]['before'].startswith('Resolved 500')
    assert p['experience'][0]['bullets'][0].startswith('Using ServiceNow')

def test_no_ai_does_not_invent(monkeypatch):
    monkeypatch.setattr('hiremed.ats_tailoring.llm_json',lambda *a: None)
    p=make_package(CV,JOB,use_ai=False)
    rewrite_package(p,CV,JOB)
    assert p['ai_rewrite_status']=='ai_unavailable_original_preserved'
    assert not p['changes']
