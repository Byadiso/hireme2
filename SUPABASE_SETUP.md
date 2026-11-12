# Supabase + GitHub Actions setup

1. In Supabase **Connect**, copy the **Session pooler** PostgreSQL URI (port 5432). Replace the password placeholder with your database password; URL-encode special characters. Never commit or share the completed URI.
2. Put the identical `DATABASE_URL` in your local `.env` and in GitHub repository **Settings → Secrets and variables → Actions**. Add `GROQ_API_KEY`, optional `GEMINI_API_KEY`, `ADZUNA_APP_ID`, and `ADZUNA_APP_KEY` as Actions secrets.
3. Run `python -m pip install -r requirements.txt` locally, then `python -m streamlit run dashboard.py --server.address 127.0.0.1`.
4. Upload and analyze your CV **after** setting `DATABASE_URL` locally. A newly created Supabase database does not contain the profile saved previously in local SQLite.
5. Verify with `python -m dotenv run -- python -c "from hiremed.storage import load_profile; print('Profile available:', bool(load_profile()))"` (do not print the profile itself).
6. Push this updated code and run the workflow under **Actions**. The scheduled bot uses the same PostgreSQL database.

The database stores a structured CV profile, preferences, job records and agent reports, **not** the original CV file. Resume tailoring that needs the original CV must be run in the local dashboard with the file uploaded in the current session.

**Security:** Enable `HIREMED_REQUIRE_AUTH=true` and set a strong `HIREMED_DASHBOARD_PASSWORD` before exposing Streamlit to a network. The local password-free dashboard must bind to `127.0.0.1`. Restrict access to Supabase; keep credentials in `.env` / GitHub Secrets only.

**Limitations:** The optional browser-based application helper uses a separate local SQLite database and is not synchronized to Supabase. No universal automatic job submission is provided. A live Supabase connection and external Groq/Adzuna services cannot be verified by offline tests.
