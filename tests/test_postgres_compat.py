"""Cross-database regression tests for Supabase migration bug."""
import sqlite3
from hiremed.repository import ensure
from hiremed.storage import save_profile, load_profile
from hiremed.preferences import load_preferences


def test_schema_migration_is_repeatable(tmp_path):
    conn = sqlite3.connect(tmp_path / 'jobs.sqlite3')
    conn.execute('CREATE TABLE tracked_jobs (id TEXT PRIMARY KEY, title TEXT, status TEXT)')
    conn.execute("INSERT INTO tracked_jobs(id,title,status) VALUES ('1','Test','prepared')")
    ensure(conn)
    ensure(conn)
    columns = {row[1] for row in conn.execute('PRAGMA table_info(tracked_jobs)')}
    assert {'posted_at','original_posted_at'} <= columns
    assert conn.execute("SELECT status FROM tracked_jobs WHERE id='1'").fetchone()[0] == 'prepared'
    conn.close()


def test_profile_round_trip(tmp_path, monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.setenv('HIREMED_DB', str(tmp_path / 'profile.sqlite3'))
    assert load_profile() is None
    save_profile({'roles': ['IT Specialist']})
    assert load_profile()['roles'] == ['IT Specialist']
    assert load_preferences().country == 'PL'

class FakePostgres:
    """Exercise PostgreSQL schema inspection branch without external credentials."""
    __module__ = 'psycopg.testing'

    def __init__(self):
        self.db = sqlite3.connect(':memory:')
        self.db.execute('CREATE TABLE tracked_jobs (id TEXT PRIMARY KEY, posted_at TEXT)')
        self.commits = 0

    def execute(self, sql, params=()):
        if 'information_schema.columns' in sql:
            class Rows:
                def fetchall(self_inner):
                    return [(row[1],) for row in self.db.execute('PRAGMA table_info(tracked_jobs)')]
            return Rows()
        return self.db.execute(sql, params)

    def commit(self):
        self.commits += 1
        self.db.commit()


def test_postgres_schema_path_avoids_duplicate_column_errors():
    db = FakePostgres()
    ensure(db)
    ensure(db)
    assert db.commits == 2
    assert {row[1] for row in db.db.execute('PRAGMA table_info(tracked_jobs)')} >= {'posted_at', 'original_posted_at'}
