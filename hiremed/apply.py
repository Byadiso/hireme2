"""Explicitly configured employer form automation. Disabled unless all gates pass."""
import os,json,logging
from pathlib import Path
from urllib.parse import urlparse
from .core import event
LOG=logging.getLogger(__name__)

def prepare_application(profile,job,assessment):
    return {'job_id':job['id'],'job_url':job.get('url'),'cv_path':os.getenv('RESUME_PATH',''), 'assessment':assessment,'status':'ready_for_review' if assessment.get('eligible') else 'blocked','cover_letter':'','notes':'Cover letter must be reviewed; do not fabricate credentials.'}

def submit_configured_form(conn,job,assessment,config_path='application_sites.json',dry_run=True):
    """Only allowlisted first-party employer forms with configured selectors. No CAPTCHA or login bypass."""
    jid=str(job['id'])
    if not assessment.get('eligible') or assessment.get('method') not in ('gemini','ai'): return {'status':'blocked','reason':'Eligibility not verified'}
    if os.getenv('HIREMED_AUTO_APPLY')!='I_CONSENT_TO_AUTOMATED_SUBMISSIONS': return {'status':'blocked','reason':'Explicit consent gate disabled'}
    cfg_path=Path(config_path)
    if not cfg_path.exists():return {'status':'blocked','reason':'No authorized employer forms configured'}
    config=json.loads(cfg_path.read_text(encoding='utf-8'))
    hostname=(urlparse(job.get('url','')).hostname or '').lower()
    if not hostname or hostname not in config.get('allowlisted_domains',{}):return {'status':'blocked','reason':'Domain not allowlisted'}
    existing=conn.execute("SELECT status FROM jobs WHERE id=?",(jid,)).fetchone()
    if existing and existing[0] in ('submitted','submission_uncertain'):return {'status':'blocked','reason':'Already submitted or uncertain'}
    limit=int(os.getenv('HIREMED_DAILY_LIMIT','3'))
    today=conn.execute("SELECT COUNT(*) FROM events WHERE event='submitted' AND substr(created_at,1,10)=date('now')").fetchone()[0]
    if today>=limit:return {'status':'blocked','reason':'Daily submission limit reached'}
    if dry_run:return {'status':'dry_run','reason':'Would attempt configured employer form after human review of profile and site selectors'}
    fields=config['allowlisted_domains'][hostname]
    required=['name','email','cv','submit','success_text']
    if not all(fields.get(k) for k in required):return {'status':'blocked','reason':'Incomplete form configuration'}
    name=os.getenv('APPLICANT_NAME');email=os.getenv('APPLICANT_EMAIL');cv=os.getenv('RESUME_PATH')
    if not name or not email or not cv or not Path(cv).is_file():return {'status':'blocked','reason':'Applicant details/CV missing'}
    if os.getenv('HIREMED_STOP_FILE') and Path(os.getenv('HIREMED_STOP_FILE')).exists():return {'status':'blocked','reason':'Emergency stop file exists'}
    from playwright.sync_api import sync_playwright
    # Persistent session is local only; do not upload browser profile or cookies to CI.
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=False)
            page=browser.new_page();page.goto(job['url'],wait_until='domcontentloaded',timeout=30000)
            if (urlparse(page.url).hostname or '').lower()!=hostname:raise RuntimeError('Redirected outside allowlisted employer domain')
            page.locator(fields['name']).fill(name,timeout=10000)
            page.locator(fields['email']).fill(email,timeout=10000)
            page.locator(fields['cv']).set_input_files(str(Path(cv).resolve()),timeout=10000)
            # Other questions, CAPTCHA, and authentication require manual handling.
            if page.locator('iframe[src*="captcha"], [class*="captcha"], [id*="captcha"]').count():raise RuntimeError('CAPTCHA requires manual completion')
            page.locator(fields['submit']).click(timeout=10000)
            page.get_by_text(fields['success_text'],exact=False).wait_for(timeout=15000)
            browser.close()
        conn.execute('UPDATE jobs SET status="submitted" WHERE id=?',(jid,));conn.commit();event(conn,jid,'submitted','Employer confirmation detected')
        return {'status':'submitted'}
    except Exception as e:
        # After clicking, success might be unknown. Never auto-retry without human review.
        LOG.warning('Submission requires review: %s',type(e).__name__)
        conn.execute('UPDATE jobs SET status="submission_uncertain" WHERE id=?',(jid,));conn.commit();event(conn,jid,'submission_uncertain',str(e)[:300])
        return {'status':'submission_uncertain','reason':str(e)[:200]}
