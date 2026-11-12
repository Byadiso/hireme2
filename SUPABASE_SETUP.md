# Supabase + GitHub Actions Setup

Use a shared Supabase PostgreSQL database so the local HireMeD dashboard and scheduled GitHub Actions workflow can access the same saved candidate profile and job records.

## 1. Get the database URL

In your [Supabase dashboard](https://supabase.com/dashboard), open your project, select **Connect → Session pooler**, and copy the PostgreSQL connection URI (port `5432`). Replace the password placeholder with your database password. URL-encode special characters in the password.

```env
DATABASE_URL=postgresql://USER:ENCODED_PASSWORD@HOST:5432/postgres
```

Keep the complete URL private. Do not commit it to Git.

## 2. Configure HireMeD locally

Add `DATABASE_URL` and your API credentials to the project's `.env` file:

```env
DATABASE_URL=postgresql://USER:ENCODED_PASSWORD@HOST:5432/postgres
AI_PROVIDER=groq
AI_FALLBACK_PROVIDER=gemini
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_optional_gemini_key
ADZUNA_APP_ID=your_adzuna_id
ADZUNA_APP_KEY=your_adzuna_key
```

Install dependencies and start the local dashboard:

```bash
python -m pip install -r requirements.txt
python -m streamlit run dashboard.py --server.address 127.0.0.1
```

**Upload and analyze your CV again** after configuring `DATABASE_URL`. A new Supabase database does not automatically contain the profile previously saved in local SQLite.

Verify that the profile is available without displaying personal information:

```bash
python -m dotenv run -- python -c "from hiremed.storage import load_profile; print('Profile available:', bool(load_profile()))"
```

Expected result: `Profile available: True`.

## 3. Configure GitHub Actions secrets

In your GitHub repository, go to **Settings → Secrets and variables → Actions** and add:

| Secret | Purpose |
| --- | --- |
| `DATABASE_URL` | The **same** Supabase URI used locally |
| `GROQ_API_KEY` | Primary AI provider |
| `GEMINI_API_KEY` | Optional fallback AI provider |
| `ADZUNA_APP_ID` | Job discovery |
| `ADZUNA_APP_KEY` | Job discovery |

**Repository secrets** work without extra workflow configuration. If you instead use **environment secrets**, set the job's `environment:` to the exact GitHub environment name:

```yaml
jobs:
  discover:
    runs-on: ubuntu-latest
    environment: production  # Replace with your actual environment name
```

Ensure the discovery step passes the secrets:

```yaml
- name: Discover and evaluate (NO SUBMISSION)
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
    GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
    GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
    ADZUNA_APP_ID: ${{ secrets.ADZUNA_APP_ID }}
    ADZUNA_APP_KEY: ${{ secrets.ADZUNA_APP_KEY }}
    AI_PROVIDER: groq
    AI_FALLBACK_PROVIDER: gemini
  run: python job_bot.py
```

## 4. Run and verify

Commit the updated workflow, then open **Actions → HireMeD Scheduled Discovery → Run workflow** to start a **new run** on the latest commit. Re-running an old job may use its original commit and workflow configuration.

If the bot reports that no CV profile is available, first confirm the local verification above returns `True` and that GitHub Actions uses the same `DATABASE_URL`.

## Security and scope

- Never commit `.env`, database passwords, API keys, or CV files.
- Keep the dashboard bound to `127.0.0.1` when local authentication is disabled. Require authentication and HTTPS before public deployment.
- The shared database stores structured profile data, preferences, and job records—not the original uploaded CV document. Resume tailoring that needs the original file requires uploading it in the dashboard session.
- Scheduled discovery does **not** submit job applications.
