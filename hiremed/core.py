import os,re,json,sqlite3,hashlib,logging
from pathlib import Path
from datetime import datetime,timezone
import requests
LOG=logging.getLogger(__name__)
DB=os.getenv('HIREMED_DB','data/hiremed.sqlite3')

def cv_text(path):
    """Extract CV text AND link targets (including links with labels such as GitHub)."""
    p=Path(path)
    if not p.exists(): raise FileNotFoundError(f'CV not found: {p}')
    if p.suffix.lower()=='.pdf':
        from pypdf import PdfReader
        pages=PdfReader(str(p)).pages
        lines=[page.extract_text() or '' for page in pages]
        links=[]
        for page in pages:
            for annotation in page.get('/Annots', []):
                try:
                    obj=annotation.get_object()
                    uri=obj.get('/A', {}).get('/URI')
                    if uri and str(uri).startswith(('https://','http://','mailto:')): links.append(str(uri))
                except (AttributeError, KeyError, TypeError): pass
        return '\n'.join(lines + list(dict.fromkeys(links)))
    if p.suffix.lower()=='.docx':
        from docx import Document
        from docx.oxml.ns import qn
        doc=Document(str(p))
        paragraphs=list(doc.paragraphs)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells: paragraphs.extend(cell.paragraphs)
        lines=[para.text for para in paragraphs]
        links=[]
        for para in paragraphs:
            for node in para._p.iter(qn('w:hyperlink')):
                rel_id=node.get(qn('r:id'))
                if rel_id and rel_id in para.part.rels:
                    target=str(para.part.rels[rel_id].target_ref)
                    if target.startswith(('https://','http://','mailto:')): links.append(target)
        return '\n'.join(lines + list(dict.fromkeys(links)))
    if p.suffix.lower()=='.txt': return p.read_text(encoding='utf-8')
    raise ValueError('CV must be PDF, DOCX or TXT')

from .ai_provider import llm_json

SKILLS=['python','sql','linux','active directory','helpdesk','it support','react','javascript','networking','azure','aws','excel','sap','docker','git','power bi','customer service','windows','cybersecurity']
def profile_from_cv(text):
    data=llm_json('Extract a factual candidate profile. Keys: roles (array of plausible job titles based on evidence), skills (array of demonstrated skills), languages (array), evidence (array of brief direct supporting excerpts), unknowns (array). Do not invent qualifications.',text)
    if data and isinstance(data.get('roles'),list) and isinstance(data.get('skills'),list):
        return {'roles':[str(x) for x in data['roles'][:8]],'skills':[str(x) for x in data['skills'][:40]],'languages':data.get('languages',[]),'evidence':data.get('evidence',[]),'unknowns':data.get('unknowns',[]),'source':'ai'}
    found=[s for s in SKILLS if re.search(r'(?<!\w)'+re.escape(s)+r'(?!\w)',text,re.I)]
    roles=['IT Support','IT Specialist'] if any(s in found for s in ['helpdesk','it support','active directory']) else ['Python Developer'] if 'python' in found else []
    return {'roles':roles,'skills':found,'languages':[],'evidence':[],'unknowns':['Profile requires human verification'],'source':'keyword_fallback'}

def assess(profile,job):
    system='Assess candidate evidence against a job description. Return JSON keys mandatory_met (array), mandatory_missing (array), mandatory_unknown (array), preferred_met (array), rationale (string), score (integer 0-100). Missing means confirmed absent; unknown means not proven. Do not infer authorization, language level, certification, or years of experience. A score is relevance only, not hiring probability.'
    result=llm_json(system,json.dumps({'candidate':profile,'job':job},ensure_ascii=False))
    if result and all(k in result for k in ['mandatory_met','mandatory_missing','mandatory_unknown','score']):
        try: result['score']=max(0,min(100,int(result['score'])))
        except (TypeError,ValueError): result['score']=0
        result['eligible']=not result['mandatory_missing'] and not result['mandatory_unknown'] and bool(result['mandatory_met'])
        result['method']='ai';return result
    matched=[s for s in profile.get('skills',[]) if s.lower() in (job.get('description') or '').lower()]
    return {'score':min(100,round(100*len(matched)/max(1,len(profile.get('skills',[]))))),'mandatory_met':[],'mandatory_missing':[],'mandatory_unknown':['Mandatory requirements not verified by fallback matcher'],'preferred_met':matched,'rationale':'Keyword overlap only; no eligibility determination','eligible':False,'method':'fallback'}

def init_db():
    p=Path(DB);p.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(p);conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, title TEXT, company TEXT, url TEXT, description TEXT, source TEXT, score INTEGER, eligible INTEGER, assessment TEXT, status TEXT DEFAULT "discovered", created_at TEXT, updated_at TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT, event TEXT, detail TEXT, created_at TEXT)');conn.commit();return conn

def store_job(conn,job,assessment):
    now=datetime.now(timezone.utc).isoformat();jid=str(job['id'])
    conn.execute('INSERT INTO jobs (id,title,company,url,description,source,score,eligible,assessment,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET score=excluded.score,eligible=excluded.eligible,assessment=excluded.assessment,updated_at=excluded.updated_at', (jid,job.get('title'),job.get('company'),job.get('url'),job.get('description'),job.get('source'),assessment['score'],int(assessment['eligible']),json.dumps(assessment,ensure_ascii=False),now,now));conn.commit()

def event(conn,jid,event_name,detail=''):
    now=datetime.now(timezone.utc).isoformat();conn.execute('INSERT INTO events (job_id,event,detail,created_at) VALUES (?,?,?,?)',(jid,event_name,detail,now));conn.commit()

def jobs_from_adzuna(roles,limit=10,country="PL"):
    aid=os.getenv('ADZUNA_APP_ID');key=os.getenv('ADZUNA_APP_KEY')
    if not aid or not key: LOG.warning('Adzuna credentials missing; no live jobs');return []
    country = country.strip().lower()
    if not re.fullmatch(r'[a-z]{2}', country):
        raise ValueError('Invalid country code')
    results={}
    for role in roles[:8]:
        try:
            r=requests.get(f'https://api.adzuna.com/v1/api/jobs/{country}/search/1',params={'app_id':aid,'app_key':key,'results_per_page':limit,'what':role,'max_days_old':7},timeout=20);r.raise_for_status()
            for j in r.json().get('results',[]):
                url=j.get('redirect_url','');jid='adzuna:'+str(j.get('id') or hashlib.sha256(url.encode()).hexdigest()[:16])
                results[jid]={'id':jid,'title':j.get('title',''),'company':j.get('company',{}).get('display_name',''),'url':url,'description':j.get('description',''),'location':j.get('location',{}).get('display_name',''),'salary_monthly_gross_pln':None,'language':None,'arrangement':None,'source':'adzuna','country':country.upper(),'posted_at':j.get('created'),'original_posted_at':j.get('original_posted_at')}
        except (requests.RequestException,ValueError) as e: LOG.warning('Adzuna query failed for %s: %s',role,type(e).__name__)
    return list(results.values())

def jobs_from_csv(path):
    import csv
    with open(path,encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            url=row.get('url') or row.get('Link') or '';yield {'id':row.get('id') or 'csv:'+hashlib.sha256(url.encode()).hexdigest()[:16], 'title':row.get('title') or row.get('Title') or '', 'company':row.get('company') or row.get('Company') or '', 'url':url, 'description':row.get('description') or row.get('Description') or '', 'location':row.get('location') or '', 'salary_monthly_gross_pln':row.get('salary_monthly_gross_pln') or None,'language':row.get('language') or None,'arrangement':row.get('arrangement') or None, 'source':'csv','posted_at':row.get('posted_at') or row.get('date_posted') or row.get('created') or row.get('published_at'),'original_posted_at':row.get('original_posted_at')}
