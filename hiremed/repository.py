"""Shared job state for scheduled Actions and dashboard; Postgres preferred."""
import os,json,sqlite3
from datetime import datetime,timezone
from pathlib import Path

def connection():
    if os.getenv('DATABASE_URL'):
        import psycopg
        return psycopg.connect(os.environ['DATABASE_URL']),True
    db=Path(os.getenv('HIREMED_DB','data/hiremed.sqlite3'));db.parent.mkdir(parents=True,exist_ok=True)
    return sqlite3.connect(db),False

def ensure(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS tracked_jobs (id TEXT PRIMARY KEY, title TEXT, company TEXT, url TEXT, description TEXT, source TEXT, score INTEGER, eligible INTEGER, assessment TEXT, policy TEXT, status TEXT, updated_at TEXT)')
    conn.commit()

def save(job,assessment,policy):
    conn,pg=connection()
    try:
        ensure(conn)
        params=(str(job['id']),job.get('title',''),job.get('company',''),job.get('url',''),job.get('description',''),job.get('source',''),int(assessment['score']),int(bool(assessment.get('eligible')) and policy['allowed']),json.dumps(assessment),json.dumps(policy),'discovered',datetime.now(timezone.utc).isoformat())
        sql='INSERT INTO tracked_jobs(id,title,company,url,description,source,score,eligible,assessment,policy,status,updated_at) VALUES ('+(','.join(['%s' if pg else '?']*12))+') ON CONFLICT(id) DO UPDATE SET score=excluded.score,eligible=excluded.eligible,assessment=excluded.assessment,policy=excluded.policy,updated_at=excluded.updated_at'
        conn.execute(sql,params);conn.commit()
    finally:conn.close()

def list_jobs():
    conn,_=connection()
    try:
        ensure(conn)
        cur=conn.execute('SELECT id,title,company,url,source,score,eligible,assessment,policy,status,updated_at FROM tracked_jobs ORDER BY score DESC')
        return [dict(zip(['id','title','company','url','source','score','eligible','assessment','policy','status','updated_at'],row)) for row in cur.fetchall()]
    finally:conn.close()

def get_job(jid):
    conn,pg=connection()
    try:
        ensure(conn)
        cur=conn.execute('SELECT id,title,company,url,description,assessment,policy,status FROM tracked_jobs WHERE id='+('%s' if pg else '?'),(jid,))
        row=cur.fetchone()
        return dict(zip(['id','title','company','url','description','assessment','policy','status'],row)) if row else None
    finally:conn.close()

def set_status(jid,status):
    allowed={'discovered','needs_review','prepared','submitted','submission_uncertain','blocked'}
    if status not in allowed:raise ValueError('Invalid status')
    conn,pg=connection()
    try:
        ensure(conn)
        conn.execute('UPDATE tracked_jobs SET status='+('%s' if pg else '?')+' WHERE id='+('%s' if pg else '?'),(status,jid));conn.commit()
    finally:conn.close()
