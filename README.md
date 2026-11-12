<div align="center">

# HireMeD

### AI-assisted job discovery, matching & application-ready resume preparation

**Discover relevant vacancies. Understand the match. Tailor your CV. Stay in control.**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Groq](https://img.shields.io/badge/AI-Groq%20(primary)-F55036)](https://groq.com/)
[![Gemini](https://img.shields.io/badge/AI-Gemini%20(fallback)-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%20%2F%20SQLite-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![GitHub Actions](https://img.shields.io/badge/Automation-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)](https://github.com/features/actions)
[![Adzuna](https://img.shields.io/badge/Job%20source-Adzuna-6554C0)](https://developer.adzuna.com/)
[![License](https://img.shields.io/badge/License-See%20repository-lightgrey)](#license)

**[Quick start](#quick-start)** · **[Jobs & matching](#jobs--matching)** · **[Resume tailoring](#ai-assisted-resume-tailoring)** · **[GitHub Actions](#scheduled-discovery-with-github-actions)** · **[Privacy & limitations](#privacy-security--limitations)**

</div>

---

## Overview

**HireMeD** is a Python-based career-assistance project that brings job discovery, CV analysis, vacancy matching, and resume preparation into one Streamlit dashboard. It is designed to reduce repetitive job-search work while keeping application decisions with the candidate.

The project combines the **Adzuna job API** with a **Groq-first AI workflow** (Gemini as an optional fallback). It supports configurable job-search preferences, saved job records, activity reports, and ATS-oriented CV drafts in **DOCX and PDF**.

> **Project status:** Active development. HireMeD is an AI-assisted workflow, **not** a universal autonomous job applicant. Scheduled discovery does **not** submit applications.

## Key features

| Feature | What it does |
| --- | --- |
| **CV analysis** | Extracts a structured candidate profile from an uploaded PDF, DOCX, or TXT resume. |
| **Job discovery** | Finds vacancies through Adzuna and supports CSV-based offline testing. |
| **Configurable preferences** | Filters by country, language, work arrangement, minimum gross monthly salary, and work authorization. |
| **Match scoring** | Ranks vacancies against the candidate profile; a high score is a recommendation to investigate, not proof of eligibility. |
| **Evidence-aware eligibility** | Distinguishes verified matches from listings with missing or conflicting requirements. |
| **Agent feedback** | Summarizes discovered jobs, strong matches, review items, rejections, and suggested next steps. |
| **AI-assisted CV tailoring** | Uses the available job description and original CV to propose relevant ATS-oriented wording. |
| **Resume exports** | Produces Word and PDF drafts with a review step before use. |
| **Scheduled discovery** | Runs headlessly through GitHub Actions against a shared PostgreSQL database. |
| **Provider fallback** | Attempts Groq first, then Gemini if configured; reduced functionality remains available without AI. |

## Jobs & matching

**Job discovery:** `Adzuna` · **Match scoring:** `0–100` · **Strong-match default:** `80+` · **Freshness:** `Last 7 days` · **Status:** `Discovered / Review / Verified / Rejected`

HireMeD separates **finding a vacancy** from **verifying whether it meets your requirements**:

1. **Discover** jobs using your saved search preferences and candidate profile.
2. **Check freshness:** the active discovery view requires a timezone-aware publication date within the last seven days. If an original publication date is available, it takes precedence over a repost date.
3. **Score** job relevance against your CV and identify promising roles.
4. **Investigate** the job description for salary, language, location/work arrangement, and required skills.
5. **Report** strong matches even when some eligibility details are still unverified.
6. **Review** promising vacancies and open the original job listing before applying.

**Important:** A score of **90/100** indicates a strong CV match, **not** that salary, language, or remote/hybrid requirements have been confirmed. Missing information is marked for review rather than assumed to qualify.

### Where to see found jobs

Start the Streamlit dashboard and open **Jobs and applications** to view the saved vacancy table, scores, status, and source links. The **Career agent report** summarizes what the latest run actually discovered.

> **Live job counts are intentionally not embedded in this README.** They depend on your saved profile, configured preferences, database, and the most recent search. The dashboard is the source of truth for current results.

## AI-assisted resume tailoring

For promising jobs (default **80+ match score**), HireMeD can use the available job description to identify ATS keywords and propose improvements to the resume's summary and experience bullets.

- **Groq** is the primary AI provider; **Gemini** is the optional fallback.
- Suggested changes are compared with the original CV, and conservative checks reject some unsupported edits.
- A before-and-after preview helps the candidate review changes.
- **DOCX and PDF** are available after review confirmation.
- The original CV remains unchanged; **no application is submitted by this workflow**.

AI-generated text can still contain errors. Always check job-specific wording, employment dates, qualifications, achievements, and links before using a tailored CV.

## Architecture

```text
                       ┌─────────────────────┐
                       │ Streamlit dashboard │
                       │ CV · jobs · reports │
                       └──────────┬──────────┘
                                  │
                        ┌─────────▼──────────┐
                        │ Candidate profile  │
                        │ & saved preferences│
                        └─────────┬──────────┘
                                  │
            ┌─────────────────────▼─────────────────────┐
            │ Shared discovery and evaluation pipeline  │
            │ Adzuna → freshness → scoring → AI review  │
            └──────────────┬─────────────────┬──────────┘
                           │                 │
                    ┌──────▼──────┐   ┌──────▼─────────┐
                    │ Job reports │   │ CV tailoring   │
                    │ & tracking  │   │ DOCX / PDF     │
                    └─────────────┘   └────────────────┘

GitHub Actions → job_bot.py → shared discovery pipeline
Local SQLite OR shared PostgreSQL (e.g., Supabase)
```

## Tech stack

| Area | Technology |
| --- | --- |
| Language | Python |
| User interface | Streamlit |
| Primary AI | Groq API |
| Optional fallback AI | Google Gemini API |
| Vacancy source | Adzuna API |
| Data persistence | SQLite (local), PostgreSQL / Supabase (shared) |
| Scheduling | GitHub Actions |
| CV processing and exports | PDF/DOCX parsing and Word/PDF generation |
| Browser application helper | Optional, separate local Playwright adapter with explicit consent and site allowlisting |
| Testing | pytest |

## Quick start

### Prerequisites

- Python **3.11+** and Git
- Adzuna application credentials for live discovery
- A Groq API key for AI features (Gemini optional)
- A PostgreSQL connection string **only if** you want the dashboard and GitHub Actions to share state

### 1. Clone and install

```bash
git clone https://github.com/Byadiso/HireMeD.git
cd HireMeD
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux / Git Bash
source .venv/bin/activate
```

Then install dependencies:

```bash
python -m pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and fill in the values you use:

```dotenv
AI_PROVIDER=groq
AI_FALLBACK_PROVIDER=gemini
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_optional_gemini_key
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key

# Optional: required for shared state with GitHub Actions
# DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/postgres

# Local-only dashboard; never expose password-free mode publicly
HIREMED_REQUIRE_AUTH=false
```

**Never commit `.env`, API keys, database credentials, or personal CV files.** If the database password contains URL-reserved characters, encode them in the connection string.

### 3. Launch the dashboard

```bash
python -m streamlit run dashboard.py --server.address 127.0.0.1
```

In the dashboard:

1. Upload and analyze your CV.
2. Review and save the extracted profile.
3. Configure your **job search preferences** (country, language, salary, work arrangement, and authorization).
4. Select **Search jobs now** or **Run career agent**.
5. Review the **agent report** and **Jobs and applications** table.
6. Review tailored CV changes and download DOCX/PDF drafts when appropriate.

The historical default search preference is **Poland / English / remote or hybrid / 8,000 PLN gross per month**, but these values are editable, not fixed in the search logic. Salary handling currently assumes PLN; changing country does not automatically convert currencies.

### 4. Run tests

```bash
python -m pytest -q
```

For an offline discovery test, where supported by the installed version:

```bash
python job_bot.py --jobs-csv examples/jobs.csv
```

## Scheduled discovery with GitHub Actions

The `.github/workflows/` workflow can run `python job_bot.py` on a schedule or via **Actions → Run workflow**. The dashboard and runner must use the **same PostgreSQL `DATABASE_URL`** to access the same saved CV profile, preferences, and job records.

Configure these **GitHub Actions secrets**:

| Secret | Purpose |
| --- | --- |
| `DATABASE_URL` | Shared PostgreSQL / Supabase connection |
| `GROQ_API_KEY` | Primary AI provider |
| `GEMINI_API_KEY` | Optional backup provider |
| `ADZUNA_APP_ID` | Adzuna application ID |
| `ADZUNA_APP_KEY` | Adzuna application key |

If you use **environment secrets** instead of repository secrets, the workflow job must declare the matching `environment:` name. A workflow re-run uses its original commit; use **Run workflow** for the current version.

**First-time setup:** Configure the same `DATABASE_URL` in your local `.env`, launch the dashboard, and upload/analyze your CV. A fresh shared database has no profile until you save one. A GitHub-hosted runner cannot read the SQLite database on your laptop.

Scheduled discovery is **read/evaluate/store only**. It does not submit applications or have access to the original uploaded CV file.

For database setup details, see [`SUPABASE_SETUP.md`](SUPABASE_SETUP.md) if present in your checkout.

## Privacy, security & limitations

- **Personal data:** Uploaded CV text may be sent to Groq or Gemini for analysis. Structured candidate profiles, job records, and generated drafts may be stored in the configured database.
- **Original documents:** Uploaded CV files are not stored in the profile database; the dashboard may retain temporary/session copies while preparing tailored documents.
- **Access control:** Use `127.0.0.1` for password-free local use. A public deployment needs authentication, HTTPS, and appropriate database access controls.
- **Job data:** Adzuna may not supply salary, language, work arrangement, or the employer's original posting date. Missing evidence is not proof of eligibility.
- **Freshness:** The seven-day filter checks available source timestamps; it cannot independently guarantee the employer first posted the role within seven days.
- **AI accuracy:** Keyword matching and AI rewriting cannot guarantee ATS performance or factual correctness. Review every document.
- **Application submission:** There is **no universal or unattended auto-apply** in the scheduled agent. A separate, restricted local Playwright helper may exist, but it is not integrated with the shared PostgreSQL tracking workflow.
- **Sources:** Direct LinkedIn, Indeed, and Pracuj.pl integrations are not included in the documented implementation.
- **Free API usage:** Groq and Gemini free tiers have changing request and rate limits.

## For recruiters

HireMeD demonstrates practical engineering across **Python automation, API integration, AI-assisted document processing, SQL persistence, workflow orchestration, and responsible human-in-the-loop design**.

The project prioritizes **transparent recommendations**: it distinguishes high CV relevance from verified job eligibility, preserves original candidate information, and requires review before using generated application materials.

## Contributing

Issues and pull requests are welcome. Please include reproducible steps for bugs, tests for behavior changes, and **redacted** logs. Never include real CVs, access tokens, or database connection strings in public issues.

## License

See the repository's `LICENSE` file, if provided. If none is present, do not assume the source is licensed for reuse.

---

<div align="center">

**HireMeD — Smarter job discovery, clearer decisions, better-prepared applications.**

</div>
