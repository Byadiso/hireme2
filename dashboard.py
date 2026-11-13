"""HireMeD 2.1: one-page local dashboard, one-click discovery, optional cloud auth."""
from dotenv import load_dotenv
load_dotenv()
import os,hmac,json,logging
from pathlib import Path
from tempfile import TemporaryDirectory
import pandas as pd
import streamlit as st
from hiremed.core import cv_text,profile_from_cv
from hiremed.storage import save_profile,load_profile,delete_profile
from hiremed.discovery import discover
from hiremed.freshness import freshness
from hiremed.preferences import Preferences, load_preferences, save_preferences, evaluate
from hiremed.agent import run_agent, recent_actions, record_feedback, load_draft, load_run_report
from hiremed.repository import list_jobs,get_job,set_status
from hiremed.documents import draft_application,draft_docx
from hiremed.resume_optimizer import make_package, to_docx as tailored_docx, to_pdf as tailored_pdf

logging.basicConfig(level=logging.WARNING)
st.set_page_config(page_title='HireMeD Career Agent',layout='wide')
st.title('HireMeD — Career Agent')
st.caption('Your career agent — configure search preferences below, no hardcoded job criteria.')

# Password-free is only safe on a local, loopback-bound Streamlit server.
# Deployment requires setting HIREMED_REQUIRE_AUTH=true and a strong password.
require_auth=os.getenv('HIREMED_REQUIRE_AUTH','false').strip().lower() in ('1','true','yes')
if require_auth:
    password=os.getenv('HIREMED_DASHBOARD_PASSWORD','')
    if not password:
        st.error('Authentication is enabled but HIREMED_DASHBOARD_PASSWORD is missing.')
        st.stop()
    if not st.session_state.get('authenticated'):
        entered=st.text_input('Dashboard password',type='password')
        if st.button('Sign in'):
            if hmac.compare_digest(entered,password):
                st.session_state['authenticated']=True
                st.rerun()
            else:st.error('Incorrect password')
        st.stop()

with st.sidebar:
    st.subheader('Configuration')
    st.write('Primary AI:', os.getenv('AI_PROVIDER','groq').upper())
    st.write('Groq:', 'Configured' if os.getenv('GROQ_API_KEY') else 'Missing key')
    st.write('Gemini backup:', 'Configured' if os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY') else 'Missing key')
    st.write('Adzuna:', 'Configured' if os.getenv('ADZUNA_APP_ID') and os.getenv('ADZUNA_APP_KEY') else 'Missing credentials')
    if not require_auth:
        st.warning('Local mode: no password. Run on 127.0.0.1 only; enable authentication before hosting publicly.')
    st.caption('Job discovery also runs via GitHub Actions using the same service and shared database.')

st.subheader('Job search preferences')
st.caption('Saved settings are shared by Search Jobs, Career Agent and scheduled GitHub Actions runs.')
current_prefs = load_preferences()
with st.form('search_preferences_form'):
    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        country = st.text_input('Country (ISO code)', value=current_prefs.country, max_chars=2,
                                help='Examples: PL, DE, NL. Job source availability varies by country.')
    with pc2:
        language = st.selectbox('Job language', options=['en', 'pl'],
                                index=['en', 'pl'].index(current_prefs.language) if current_prefs.language in ('en', 'pl') else 0,
                                format_func=lambda x: {'en': 'English', 'pl': 'Polish'}[x])
    with pc3:
        minimum_salary = st.number_input('Minimum monthly gross salary (PLN)', min_value=0,
                                         max_value=1000000, step=500, value=current_prefs.minimum_monthly_gross_pln)
    arrangements = st.multiselect('Acceptable work arrangements', ['remote', 'hybrid', 'onsite'],
                                  default=list(current_prefs.arrangements))
    authorized = st.checkbox('Authorized to work in selected country', value=current_prefs.work_authorized)
    submitted_preferences = st.form_submit_button('Save search preferences', type='primary')
    if submitted_preferences:
        try:
            save_preferences(Preferences(country=country, language=language,
                minimum_monthly_gross_pln=int(minimum_salary), arrangements=tuple(arrangements),
                work_authorized=authorized))
            st.success('Search preferences saved. Both search buttons and scheduled runs will use them.')
            st.rerun()
        except Exception as exc:
            st.error(f'Could not save preferences: {exc}')

st.subheader('1. My CV')
st.caption('Upload PDF, DOCX or TXT anytime. Original file is deleted after processing; the structured career profile is saved for scheduled searches. CV content is sent to your configured AI provider (Groq first, Gemini backup).')
uploaded=st.file_uploader('Upload or replace your CV',type=['pdf','docx','txt'])
if uploaded is not None:
    upload_signature=(uploaded.name, uploaded.size, hash(uploaded.getvalue()))
    if st.session_state.get('cv_upload_signature') != upload_signature:
        with TemporaryDirectory() as tmp:
            source=Path(tmp)/('uploaded'+Path(uploaded.name).suffix.lower())
            source.write_bytes(uploaded.getvalue())
            st.session_state['original_cv_text']=cv_text(source)
        st.session_state['cv_upload_signature']=upload_signature
        st.session_state['tailored_packages']={}
        st.info('Original CV loaded for this session. It will not be saved to the database.')
if st.button('Analyze CV and update profile',disabled=uploaded is None,type='primary'):
    with st.spinner('Analyzing your CV with configured AI providers...'):
        try:
            with TemporaryDirectory() as tmp:
                path=Path(tmp)/('uploaded'+Path(uploaded.name).suffix.lower())
                path.write_bytes(uploaded.getvalue())
                raw=cv_text(path)
            st.session_state['original_cv_text']=raw
            if not raw.strip():
                st.error('The CV contains no readable text. Try a text-based PDF or DOCX.')
            else:
                profile=profile_from_cv(raw)
                if profile.get('source') not in ('ai','gemini'):
                    st.error('AI analysis failed on all configured providers. Your previous saved profile is unchanged. Check the terminal for details.')
                else:
                    save_profile(profile)
                    st.success('Profile updated! You can search jobs below.')
                    st.rerun()
        except Exception as exc:
            logging.exception('CV analysis failed')
            st.error(f'CV processing failed ({type(exc).__name__}). See terminal for details.')

profile=load_profile()
if profile:
    st.success('Career profile ready')
    st.write('**Suggested roles:**',', '.join(profile.get('roles',[])) or 'None identified')
    with st.expander('View structured profile'):
        st.json(profile)
    if st.button('Delete stored profile'):
        delete_profile()
        st.success('Profile deleted')
        st.rerun()
else:
    st.info('Upload a CV and analyze it to enable job discovery.')

st.divider()
st.subheader('2. Find jobs')
st.caption('Fresh jobs only: published in the past 7 days. Listings without verifiable posting dates are excluded.')
left,right=st.columns([1,2])
with left:
    limit=st.number_input('Results per suggested role',min_value=1,max_value=50,value=10)
with right:
    st.caption('Uses Adzuna for live vacancies. Unknown salary, language or work arrangement is flagged for review, not treated as verified.')
if st.button('🔎 Search jobs now',disabled=not bool(profile),type='primary'):
    if not (os.getenv('ADZUNA_APP_ID') and os.getenv('ADZUNA_APP_KEY')):
        st.error('Add ADZUNA_APP_ID and ADZUNA_APP_KEY to .env to search live vacancies.')
    else:
        with st.spinner('Searching and matching jobs. This may take a little while...'):
            try:
                results=discover(profile,limit=int(limit),preferences=load_preferences())
                if results:
                    st.session_state.pop('agent_report', None)
                    st.success(f'Search complete: {len(results)} vacancies processed. Results are below.')
                    st.session_state['tailor_after_search']=True
                else:
                    st.warning('Search finished but returned no vacancies. Check Adzuna credentials, search roles and terminal logs.')
            except Exception as exc:
                logging.exception('Job discovery failed')
                st.error(f'Search failed ({type(exc).__name__}). See terminal for details.')

st.divider()
st.subheader('3. Career agent — what did it find?')
st.caption('Run a search, then see a clear outcome and recommended next action. The latest report stays visible after reopening the dashboard.')
agent_limit=st.slider('Maximum jobs per agent run',min_value=1,max_value=30,value=10)
prepare_drafts=st.checkbox('Automatically prepare drafts for fully verified matches',value=False)
if st.button('🧠 Run career agent',disabled=not bool(profile),type='primary'):
    if not (os.getenv('ADZUNA_APP_ID') and os.getenv('ADZUNA_APP_KEY')):
        st.error('Configure ADZUNA_APP_ID and ADZUNA_APP_KEY in .env for live discovery.')
    else:
        status = st.status('Agent working…', expanded=True)
        bar = st.progress(0)
        def show_progress(stage, message, completed, total):
            status.write(message)
            if total:
                bar.progress(min(100, round(completed / total * 100)))
        try:
            output=run_agent(profile,max_jobs=agent_limit,prepare_drafts=prepare_drafts,
                             preferences=load_preferences(),on_progress=show_progress)
            status.update(label='Agent finished',state='complete',expanded=False)
            st.session_state['agent_report']=output['report']
            st.session_state['tailor_after_search']=True
        except Exception as exc:
            logging.exception('Career agent failed')
            status.update(label='Agent run failed',state='error',expanded=True)
            st.error(f'Agent run failed ({type(exc).__name__}); inspect terminal logs. Previous completed report is unchanged.')
report=load_run_report()
if report:
    st.markdown('#### Latest agent report')
    st.caption(f"Completed: {report['finished_at']} · Run: {report.get('run_type', 'career agent')} · Search planner: {report['planner']}")
    st.caption('This saved report reflects the last completed run. Run discovery again to apply updated language filters and refresh its counts.')
    st.info(report['headline'])
    x1,x2,x3,x4,x5=st.columns(5)
    x1.metric('Discovered this run',report['total'])
    x2.metric(f"Strong matches ({report.get('strong_match_threshold', 80)}+)",report.get('strong_matches', 0))
    x3.metric('Verified eligible',report['eligible'])
    x4.metric('Need review',report['review'])
    x5.metric('Rejected',report['rejected'])
    st.write('**What to do next:**',report['next_step'])
    if report['blockers']:
        st.write('**What needs checking before applying:**')
        for blocker in report['blockers']:
            st.write(f"- {blocker['reason']} ({blocker['count']} job(s))")
    if report['highlights']:
        st.write('**Top CV matches from this run (eligibility shown separately):**')
        for job in report['highlights']:
            st.write(f"**{job['title']}** — {job['company']} · match score {job['score']:g} · {job.get('outcome', 'review')}")
            if job['url'].startswith(('https://','http://')):
                st.link_button('Open job listing',job['url'],key='agent_link_'+job['id'])
    with st.expander('Search queries used'):
        st.write(', '.join(report['queries']) or 'None')
        st.write(f"Application drafts created: {report['drafts_created']}. No applications were submitted.")
else:
    st.info('No run report yet. Click Search jobs now or Run career agent to see a summary.')
with st.expander('Detailed agent activity (optional)',expanded=False):
    actions=recent_actions(80)
    if actions:
        st.dataframe(pd.DataFrame(actions),hide_index=True,use_container_width=True)
    else:
        st.info('No agent actions yet.')

st.divider()
st.subheader('4. Automatic resume tailoring')
st.caption('Only jobs with verified posting dates in the past 7 days are eligible for new CV packages. For strong matches, compare the job description with your CV, identify supported ATS terms, and ask Groq (Gemini backup) for conservative rewrites. Review all changes before applying. No automatic submissions.')
auto_tailor = st.checkbox('Automatically tailor strong matches after searching', value=True, key='auto_tailor')
tailor_threshold = st.slider('Minimum score for tailoring', 0, 100, 80, 5, key='tailor_threshold')
tailor_limit = st.number_input('Maximum CV packages per run (protects free AI quota)', 1, 10, 5, key='tailor_limit')
if not st.session_state.get('original_cv_text'):
    st.info('Upload your original CV above in this session to enable resume tailoring. A saved structured profile alone is not enough to reproduce your original CV safely.')

def generate_tailored_packages():
    original=st.session_state.get('original_cv_text')
    if not original:
        return 0
    candidates=[]
    for j in list_jobs():
        if not freshness(j)['allowed'] or float(j.get('score') or 0)<tailor_threshold:
            continue
        full = get_job(j['id']) or {}
        if evaluate({**j, **full}, load_preferences())['rejected']:
            continue
        candidates.append(j)
    candidates.sort(key=lambda j: float(j.get('score') or 0), reverse=True)
    packages=st.session_state.setdefault('tailored_packages', {})
    created=0
    for candidate in candidates[:int(tailor_limit)]:
        jid=str(candidate['id'])
        if jid not in packages:
            packages[jid]=make_package(original, {**candidate, **(get_job(jid) or {})})
            created+=1
    return created

if st.session_state.pop('tailor_after_search', False) and auto_tailor and st.session_state.get('original_cv_text'):
    with st.spinner('Automatically preparing CVs for strong matches...'):
        try:
            n=generate_tailored_packages()
            st.success(f'Automatic resume tailoring: {n} new CV package(s) prepared for review.')
        except Exception:
            logging.exception('Automatic resume tailoring failed')
            st.warning('Automatic tailoring failed; job discovery results remain available.')

if st.button('Prepare tailored CVs for strong matches', disabled=not bool(st.session_state.get('original_cv_text'))):
    with st.spinner('Preparing truthful job-specific CV packages...'):
        try:
            n=generate_tailored_packages()
            st.success(f'{n} new CV package(s) prepared. Review and download below.')
        except Exception as exc:
            logging.exception('Resume tailoring failed')
            st.error(f'Resume tailoring failed ({type(exc).__name__}).')
packages=st.session_state.get('tailored_packages', {})
if packages:
    st.write(f'**{len(packages)} tailored CV package(s) ready for review**')
    for jid, package in packages.items():
        job_record=get_job(jid)
        if not job_record or not freshness(job_record)['allowed']:
            continue
        with st.expander(f"{package['job_title']} — {package['company']}"):
            st.caption(package['note'])
            st.write('**AI rewrite status:**', package.get('ai_rewrite_status', 'unknown'))
            report=package.get('ats_report', {})
            if not report.get('description_available'):
                st.warning('The saved job description is too short for reliable tailoring. Open the employer listing and verify its full requirements.')
            st.write('**ATS terms also found in your CV:**', ', '.join(report.get('matched_keywords', [])) or 'None identified')
            st.write('**Job terms not verified in your CV (do not add without evidence):**', ', '.join(report.get('unverified_job_terms', [])[:18]) or 'None identified')
            st.write('**CV tailoring diagnostics:**', package.get('tailoring_diagnostics', {}))
            st.write('**Preserved clickable CV links:**', package.get('links') or 'No profile URLs detected in extracted CV text')
            st.write('**Proposed changes — compare before approval:**')
            if not package.get('changes'):
                st.info('No safe AI rewrites were accepted; the CV remains based on original wording.')
            for change in package.get('changes', []):
                st.markdown('**Original:** ' + change['before'])
                st.markdown('**Revised:** ' + change['after'])
            approved=st.checkbox('I reviewed this tailored CV and verified its factual accuracy', key='approved_'+jid)
            st.write('**Prioritized source evidence (for your review, not printed in the CV):**')
            for line in package['evidence']:
                st.write('• ' + line)
            st.download_button('Download Word (.docx)', tailored_docx(package), disabled=not approved,
                file_name=f'hiremed_tailored_{jid[:35]}.docx',
                mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document', key='docx_'+jid)
            st.download_button('Download PDF (.pdf)', tailored_pdf(package), disabled=not approved,
                file_name=f'hiremed_tailored_{jid[:35]}.pdf', mime='application/pdf', key='pdf_'+jid)
            st.warning('Downloads unlock only after your review confirmation. HireMeD does not submit applications automatically.')

st.divider()
st.subheader('5. Jobs and applications')
jobs=[j for j in list_jobs() if freshness(j)['allowed']]
if not jobs:
    st.info('No verified jobs posted in the last 7 days. Older and undated saved jobs are hidden; search again for fresh listings.')
else:
    df=pd.DataFrame(jobs)
    a,b,c=st.columns(3)
    a.metric('Jobs found',len(df))
    b.metric('Verified matches',int(df['eligible'].sum()))
    c.metric('Submitted',int((df['status']=='submitted').sum()))
    status_filter=st.selectbox('Show jobs',['Relevant jobs','All (including rejected)','Verified matches','Needs review','Rejected','Submitted'])
    rejected_ids = {j['id'] for j in jobs
                    if evaluate({**j, **(get_job(j['id']) or {})}, current_prefs)['rejected']}
    filtered=df
    if status_filter=='Relevant jobs': filtered=df[~df['id'].isin(rejected_ids)]
    elif status_filter=='Rejected': filtered=df[df['id'].isin(rejected_ids)]
    elif status_filter=='Verified matches':filtered=df[df['eligible']==1]
    elif status_filter=='Needs review':filtered=df[(df['eligible']==0)&(df['status']!='submitted')&(~df['id'].isin(rejected_ids))]
    elif status_filter=='Submitted':filtered=df[df['status']=='submitted']
    st.dataframe(filtered[['title','company','posted_at','score','eligible','status','source','url']],
        column_config={'url':st.column_config.LinkColumn('Job link')},hide_index=True,use_container_width=True)
    if not filtered.empty:
        selected=st.selectbox('Inspect a vacancy',filtered['id'].tolist(),format_func=lambda jid:filtered.loc[filtered.id==jid,'title'].iloc[0])
        job=get_job(selected)
        assessment=json.loads(job['assessment']);policy=json.loads(job['policy'])
        with st.expander('Eligibility and preference details',expanded=True):
            st.write('**Eligibility**');st.json(assessment)
            st.write('**Preferences**');st.json(policy)
            investigation=assessment.get('investigation')
            if investigation:
                st.write('**Agent investigation (only verified listing excerpts are evidence)**')
                st.json(investigation)
        f1,f2=st.columns(2)
        if f1.button('👍 Relevant',key='relevant_'+selected):
            record_feedback(selected,'relevant')
            st.success('Feedback recorded in agent history')
        if f2.button('👎 Not relevant',key='irrelevant_'+selected):
            record_feedback(selected,'irrelevant')
            st.success('Feedback recorded in agent history')
        stored_draft=load_draft(selected)
        if stored_draft:
            st.write('**Agent-prepared application drafts (review before using)**')
            st.download_button('Download prepared cover letter',draft_docx(stored_draft['cover_letter'],'Cover Letter'),file_name='agent_cover_letter.docx')
            st.download_button('Download prepared CV summary',draft_docx(stored_draft['cv_summary'],'Professional Summary'),file_name='agent_cv_summary.docx')
        if assessment.get('eligible') and policy.get('allowed') and profile:
            if st.button('Generate application drafts'):
                try:
                    st.session_state['draft']=draft_application(profile,job,assessment)
                    st.session_state['draft_id']=selected
                except Exception as exc:
                    logging.exception('Draft generation failed')
                    st.error(f'Draft failed ({type(exc).__name__})')
            if st.session_state.get('draft_id')==selected:
                draft=st.session_state['draft']
                st.text_area('Review cover letter',draft['cover_letter'],height=200)
                st.download_button('Download cover letter',draft_docx(draft['cover_letter'],'Cover Letter'),'cover_letter.docx')
                st.download_button('Download CV summary',draft_docx(draft['cv_summary'],'Professional Summary'),'cv_summary.docx')
                if st.button('Mark prepared'):
                    set_status(selected,'prepared');st.rerun()
        else:
            st.caption('Application drafting is blocked until eligibility and preferences are verified.')
st.caption('No automatic submissions are triggered from this dashboard. Supported employer-form submission remains a separate, opt-in workflow.')
