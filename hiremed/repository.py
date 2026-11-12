"""Shared job state for scheduled Actions and dashboard; Postgres preferred."""
import os,json,sqlite3
from datetime import datetime,timezone
from pathlib import Path

def connection():
    from .storage import _connect
    return _connect()

def ensure(conn):
    """Idempotent, non-destructive schema initialization for SQLite and PostgreSQL.

    PostgreSQL aborts a transaction after any SQL error, so never probe for
    existing columns by deliberately issuing failing ALTER TABLE statements.
    """
    conn.execute('CREATE TABLE IF NOT EXISTS tracked_jobs (id TEXT PRIMARY KEY, title TEXT, company TEXT, url TEXT, description TEXT, source TEXT, score INTEGER, eligible INTEGER, assessment TEXT, policy TEXT, status TEXT, updated_at TEXT, posted_at TEXT, original_posted_at TEXT)')
    pg = conn.__class__.__module__.startswith('psycopg')
    if pg:
        rows = conn.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = 'tracked_jobs'").fetchall()
        existing = {row[0] for row in rows}
    else:
        existing = {row[1] for row in conn.execute('PRAGMA table_info(tracked_jobs)').fetchall()}
    # Explicit allowlist; identifiers are never derived from user input.
    columns = {'posted_at': 'TEXT', 'original_posted_at': 'TEXT'}
    for column, kind in columns.items():
        if column not in existing:
            conn.execute(f'ALTER TABLE tracked_jobs ADD COLUMN {column} {kind}')
    conn.commit()

def save(job,assessment,policy):
    conn,pg=connection()
    try:
        ensure(conn)
        params=(str(job['id']),job.get('title',''),job.get('company',''),job.get('url',''),job.get('description',''),job.get('source',''),int(assessment['score']),int(bool(assessment.get('eligible')) and policy['allowed']),json.dumps(assessment),json.dumps(policy),'discovered',datetime.now(timezone.utc).isoformat(),job.get('posted_at'),job.get('original_posted_at'))
        sql='INSERT INTO tracked_jobs(id,title,company,url,description,source,score,eligible,assessment,policy,status,updated_at,posted_at,original_posted_at) VALUES ('+(','.join(['%s' if pg else '?']*14))+') ON CONFLICT(id) DO UPDATE SET score=excluded.score,eligible=excluded.eligible,assessment=excluded.assessment,policy=excluded.policy,updated_at=excluded.updated_at,posted_at=excluded.posted_at,original_posted_at=excluded.original_posted_at'
        conn.execute(sql,params);conn.commit()
    finally:conn.close()

def list_jobs():
    conn,_=connection()
    try:
        ensure(conn)
        cur=conn.execute('SELECT id,title,company,url,source,score,eligible,assessment,policy,status,updated_at,posted_at,original_posted_at FROM tracked_jobs ORDER BY score DESC')
        return [dict(zip(['id','title','company','url','source','score','eligible','assessment','policy','status','updated_at','posted_at','original_posted_at'],row)) for row in cur.fetchall()]
    finally:conn.close()

def get_job(jid):
    conn,pg=connection()
    try:
        ensure(conn)
        cur=conn.execute('SELECT id,title,company,url,description,assessment,policy,status,posted_at,original_posted_at FROM tracked_jobs WHERE id='+('%s' if pg else '?'),(jid,))
        row=cur.fetchone()
        return dict(zip(['id','title','company','url','description','assessment','policy','status','posted_at','original_posted_at'],row)) if row else None
    finally:conn.close()

def set_status(jid,status):
    allowed={'discovered','needs_review','prepared','submitted','submission_uncertain','blocked'}
    if status not in allowed:raise ValueError('Invalid status')
    conn,pg=connection()
    try:
        ensure(conn)
        conn.execute('UPDATE tracked_jobs SET status='+('%s' if pg else '?')+' WHERE id='+('%s' if pg else '?'),(status,jid));conn.commit()
    finally:conn.close()
