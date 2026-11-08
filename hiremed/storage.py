"""Persistent profile storage: local SQLite or PostgreSQL via DATABASE_URL.
Only structured profile is saved. Never store raw CV in this module.
"""
import json,os,sqlite3
from pathlib import Path
from datetime import datetime,timezone

def _connect():
    url=os.getenv('DATABASE_URL','')
    if url:
        import psycopg
        return psycopg.connect(url),True
    path=Path(os.getenv('HIREMED_DB','data/hiremed.sqlite3'))
    path.parent.mkdir(parents=True,exist_ok=True)
    return sqlite3.connect(path),False

def save_profile(profile):
    conn,pg=_connect()
    try:
        cur=conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS candidate_profile (id INTEGER PRIMARY KEY, profile_json TEXT NOT NULL, updated_at TEXT NOT NULL)')
        stamp=datetime.now(timezone.utc).isoformat()
        if pg:
            cur.execute('INSERT INTO candidate_profile(id,profile_json,updated_at) VALUES (1,%s,%s) ON CONFLICT (id) DO UPDATE SET profile_json=EXCLUDED.profile_json, updated_at=EXCLUDED.updated_at',(json.dumps(profile),stamp))
        else:
            cur.execute('INSERT INTO candidate_profile(id,profile_json,updated_at) VALUES (1,?,?) ON CONFLICT(id) DO UPDATE SET profile_json=excluded.profile_json, updated_at=excluded.updated_at',(json.dumps(profile),stamp))
        conn.commit()
    finally:conn.close()

def load_profile():
    conn,_=_connect()
    try:
        cur=conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS candidate_profile (id INTEGER PRIMARY KEY, profile_json TEXT NOT NULL, updated_at TEXT NOT NULL)')
        cur.execute('SELECT profile_json FROM candidate_profile WHERE id=1')
        row=cur.fetchone()
        return json.loads(row[0]) if row else None
    finally:conn.close()

def delete_profile():
    conn,_=_connect()
    try:
        cur=conn.cursor()
        cur.execute('DELETE FROM candidate_profile WHERE id=1')
        conn.commit()
    finally:conn.close()
