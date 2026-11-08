"""Single discovery pipeline shared by Streamlit and GitHub Actions."""
from .core import jobs_from_adzuna, jobs_from_csv, assess
from .preferences import evaluate, load_preferences
from .repository import save


def discover(profile, *, limit=10, csv_path=None, roles=None, preferences=None):
    if not profile:
        raise ValueError('Upload and analyze a CV before searching for jobs.')
    role_list=roles or profile.get('roles', [])
    if not role_list:
        raise ValueError('No suitable job titles found in your profile. Update your CV first.')
    p = preferences if preferences is not None else load_preferences()
    jobs=list(jobs_from_csv(csv_path)) if csv_path else jobs_from_adzuna(role_list,limit,country=p.country)
    results=[]
    for job in jobs:
        policy=evaluate(job,p)
        assessment=(assess(profile,job) if not policy['rejected'] else
                    {'score':0,'eligible':False,'method':'policy','rationale':'Rejected by preferences'})
        save(job,assessment,policy)
        results.append({'job':job,'assessment':assessment,'policy':policy})
    # This is a separate run from the career agent: label it accurately and
    # publish its results immediately so the report matches the jobs just found.
    from .agent import summarize_run, save_run_report
    run_results = []
    for item in results:
        policy = item['policy']
        assessment = item['assessment']
        verified = bool(assessment.get('eligible')) and bool(policy.get('allowed'))
        outcome = 'eligible' if verified else 'rejected' if policy.get('rejected') else 'review'
        run_results.append({**item, 'outcome': outcome})
    report = summarize_run({'queries': role_list, 'planner': 'saved CV roles'},
                           run_results, run_type='job discovery')
    save_run_report(report)
    return results
