## Version 2.8: Professional resume layout

Replaces excerpt-and-appendix output with structured, ATS-friendly CVs. Preserves original source facts, reflows wrapped PDF text, ranks existing skills and achievement bullets by job relevance, and exports Word/PDF. No automatic application submission. Original CV remains unchanged.

**Limitations:** Tailoring is conservative: it reorganizes and cleans source material, but does not generate unverified new claims or guarantee full semantic rewriting. Review every draft before applying.

# HireMeD 2.5 — Groq-first AI with Gemini backup

Set `AI_PROVIDER=groq`, `GROQ_API_KEY=...`, `AI_FALLBACK_PROVIDER=gemini`, and optionally `GEMINI_API_KEY=...` in `.env` (see `.env.example`). Groq is attempted first. On errors (including quota/rate limits), Gemini is tried if configured. If both fail, job search still uses keyword fallback; CV upload preserves the previously saved profile instead of overwriting it.

**Note:** The free plans have rate limits and may change. This upgrade does not guarantee unlimited free inference. The current code makes up to two AI calls per job; keep the run size small to conserve quota. Gemini fallback may also be exhausted.

**Privacy:** CV text is transmitted to the selected cloud provider. Use only providers you trust. Never commit `.env` or keys.

**Migration:** Copy your `.env` and (for local SQLite) `data/hiremed.sqlite3` from the old version. Start with `python -m streamlit run dashboard.py --server.address 127.0.0.1`. If no profile is saved, upload and analyze the CV before starting the agent.

# HireMeD 2.0 — Gemini & Upload Upgrade

This is an **incremental implementation**, not a fully deployed universal auto-apply service.

## Included and locally tested

- Authenticated Streamlit dashboard for on-demand PDF, DOCX, TXT CV uploads.
- Temporary CV processing (deleted after analysis); Gemini extracts a structured candidate profile.
- Replace or delete stored structured profile. The profile is **persisted** for scheduled searches, and contains personal information.
- Google Gemini via `google-genai` and `GEMINI_API_KEY` (Gemini requests transmit CV/job content to Google).
- Adzuna discovery, CSV demo feed, matching, preference gate, and persistent jobs.
- Poland, English, remote/hybrid, minimum **8,000 PLN gross/month**.
- Unknown salary, language, or work arrangement is **review required**, not assumed eligible.
- AI-generated cover letter and professional-summary DOCX drafts for verified matches.
- GitHub Actions scheduled discovery, reading a shared PostgreSQL database; no CV file in CI.
- Restricted local Playwright form adapter from the previous version, requiring consent, explicit allowlist, applicant details, and a CV at submission time.

## Not yet delivered

- LinkedIn, Indeed, and Pracuj.pl direct integrations; access depends on permitted APIs / terms.
- General company ATS discovery integrations, universal form support, CAPTCHA or login bypass.
- Unattended auto-apply from GitHub Actions. The form adapter is **local only**, and the dashboard does not call it.
- A full tailored CV; the generated professional-summary DOCX is not a complete CV.
- Live end-to-end validation with Gemini, Adzuna, PostgreSQL, or a real employer submission.

## Setup

1. `python -m venv .venv` and activate it.
2. `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env`; configure `GEMINI_API_KEY`, `HIREMED_DASHBOARD_PASSWORD`, `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`.
4. Configure a **private PostgreSQL database** using `DATABASE_URL` for sharing state across your Streamlit host and GitHub Actions. Use a restricted DB user and TLS. Without `DATABASE_URL`, local SQLite works but **GitHub Actions state will not persist between runs**.
5. Start dashboard: `python -m dotenv run -- streamlit run dashboard.py`.
6. Upload a CV in the dashboard, review the extracted profile, then run `python -m dotenv run -- python job_bot.py` or test offline with `python -m dotenv run -- python job_bot.py --jobs-csv examples/jobs.csv`.
7. Run tests: `python -m pytest -q`.
8. Deploy the dashboard on an authenticated private host separately; GitHub Actions is a scheduler, **not** a Streamlit host. Configure GitHub Actions secrets `GEMINI_API_KEY`, `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `DATABASE_URL`.

**Do not commit your CV, API keys, `.env`, database files, or browser cookies.** Original uploaded CVs are deleted after analysis; they are not available later for unattended form uploads. Upload again when you intend to apply, or build a separate consent-based encrypted temporary document store with expiry.

## Safety and review

Missing job data blocks auto-eligibility. Gemini outputs may be wrong; review generated text. No automatic applications are made by the scheduled workflow. Local form automation (`apply_job.py`) requires `HIREMED_AUTO_APPLY=I_CONSENT_TO_AUTOMATED_SUBMISSIONS`, a configured `application_sites.json`, a verified job assessment in the legacy local DB, and an accessible CV file. This legacy adapter is not yet wired to the new PostgreSQL tracking flow.

## Privacy

Uploaded CVs are briefly written to a temporary directory for PDF/DOCX parsing and deleted automatically. Streamlit's upload session may retain the upload in memory until the session ends. Structured profile and job assessments are saved in the database and may contain sensitive personal information. Delete the stored profile through the dashboard when no longer needed.

## HireMeD 2.1: One-dashboard workflow (updated)

This version simplifies the user interface. **Only one command is needed for interactive use**:

```bash
python -m pip install -r requirements.txt
python -m streamlit run dashboard.py --server.address 127.0.0.1
```

`dashboard.py` loads `.env` automatically. Open the local Streamlit URL, upload your CV, click **Analyze CV and update profile**, then click **Search jobs now**. Matching jobs appear in a table **on the same page**. No separate `job_bot.py` command is required for manual searching. `job_bot.py` remains available for scheduled GitHub Actions runs and uses the exact same `hiremed.discovery.discover` pipeline.

### Authentication

For local-only use, `HIREMED_REQUIRE_AUTH=false` disables the password prompt. **Always bind the server to `127.0.0.1` in local mode**; this is not safe on an exposed/public server. When deploying to a public or shared host, set `HIREMED_REQUIRE_AUTH=true`, set a strong `HIREMED_DASHBOARD_PASSWORD` in protected environment secrets, and deploy behind HTTPS. The password is remembered for the current Streamlit session.

### Gemini troubleshooting

Set `GEMINI_MODEL=gemini-3.5-flash` in `.env` (or choose another model verified to work with your API key). Failures are logged with a short error description in the terminal. Your existing saved profile is **not replaced** when a new CV analysis fails. The original uploaded CV is deleted after parsing; the structured profile is retained until you delete it.

### Live search limitations

Live discovery requires `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`. Without them, the dashboard explains what is missing. Adzuna snippets often omit salary, job language, and remote/hybrid arrangement; such jobs are shown for review rather than incorrectly labeled eligible. The dashboard does **not** automatically submit applications. LinkedIn, Indeed, Pracuj.pl, and universal employer-form automation are **not** included. GitHub Actions and a locally running dashboard require a shared `DATABASE_URL` to see the same saved profile and jobs; a local SQLite file is not shared with GitHub-hosted runners.

### Tests

```bash
python -m pytest -q
```

## Career Agent (new in 2.2)

Run **one** local command (after installing requirements and configuring `.env`):

```bash
python -m streamlit run dashboard.py --server.address 127.0.0.1
```

The same page now offers **Run career agent** and an **Agent activity and decisions** history. The agent:

1. Uses Gemini to propose up to five CV-grounded search queries, falling back to the CV's roles if Gemini is unavailable.
2. Searches Adzuna (or a local CSV in programmatic tests), with a hard cap of 30 evaluated jobs per run.
3. Investigates each listing using Gemini and verifies any quoted evidence against the original listing text.
4. Checks your preferences and assesses qualifications; unknown salary, language, arrangement, and requirements remain review items, **never verified**.
5. Saves results, reasons, and an activity log to SQLite locally or PostgreSQL when configured.
6. Optionally creates **cover-letter and CV-summary drafts** for fully verified matches. These are stored in the private database and downloadable on the same dashboard. They are **not** complete tailored CVs or automatic applications.
7. Accepts relevant/irrelevant feedback on jobs and uses that feedback to prioritize similar searches in later runs.

### Scope and safety

This is a bounded, tool-using AI workflow, not a universal autonomous applicant. **No applications are submitted by the agent.** The existing separate employer-form adapter remains opt-in. Adzuna is the only implemented live source; LinkedIn, Indeed, Pracuj.pl and broad company-career crawling are not implemented. Missing information is not guessed. CV text is sent to Google Gemini when you upload and analyze it, and the original uploaded file is discarded; structured profiles and generated drafts remain in the database until deleted. Keep database credentials and dashboard access private. A GitHub Actions runner requires `DATABASE_URL` for shared persistent state.

To run the offline tests:

```bash
python -m pytest -q
```

## Editable job preferences (2.3)

Open the dashboard and edit **Job search preferences** at the top. Country code, job language,
minimum monthly gross salary in PLN, accepted work arrangements, and work authorization are
saved in the configured SQLite/PostgreSQL database. Both **Search jobs now** and **Run the
career agent** read the saved values. The scheduled `job_bot.py` entry point reads the same
values when it connects to the same database. Defaults remain Poland / English / remote or
hybrid / 8,000 PLN gross per month until you save your own preferences.

**Country coverage:** Adzuna searches now use the selected country code, but not every country is supported by
Adzuna. Unsupported countries may produce API errors or zero results. The salary
field currently uses PLN for all countries and is not a currency conversion feature.

**Scheduled runs:** If Streamlit and GitHub Actions do not share `DATABASE_URL`, they will
have separate settings and profile databases. Configure a shared private PostgreSQL instance
for cross-device/scheduled persistence.

## 2.4 — Agent feedback and progress

The **Career agent — what did it find?** section now displays a persisted report for the most recent completed run: total checked, verified matches, jobs needing review, rejections, frequent blockers, top verified matches, and a suggested next step. A progress indicator reports planning, discovery, and per-job evaluation while the agent runs. The detailed event log remains available in an optional expander. The report is stored in the configured database; it reflects **only the most recent completed agent run**, not the full historical jobs table. No applications are submitted automatically.

## 2.7: Automatic job-specific resume packages

Upload your original CV again **in the same dashboard session**, then run Search Jobs or Career Agent. With **Automatically tailor strong matches** enabled (default), HireMeD prepares up to five resume packages for saved jobs scoring **80+**. Each package offers **DOCX and PDF** downloads and requires your review before use. No applications are submitted automatically.

The generated files place **verbatim job-relevant lines from the uploaded CV** first, followed by the **complete extracted original CV text**. The AI may select existing CV line indices, but cannot write new claims. This is a conservative, truthful tailoring workflow, **not** a polished rewrite of each experience bullet or a preservation of the original document's formatting. Inspect the downloads before sending. Original CV text and generated packages are kept only in Streamlit session memory; the existing saved structured profile remains in the database. Reupload after restarting Streamlit. A fresh upload is also needed for scheduled discovery if you later want background tailoring.

The free-tier AI provider is called only for candidate line selection; keyword-based selection works if both Groq and Gemini are unavailable. Adjust the threshold and maximum packages in the dashboard to control usage.

## 2.9 — AI-assisted ATS resume tailoring

After discovery, jobs scoring at least 80 (configurable) are selected for CV preparation.
The dashboard loads the **stored full job description**, identifies matching and unverified
keywords, then makes one Groq-first/Gemini-backup JSON rewrite request per job. AI may
propose concise summary and bullet rewrites; a conservative lexical and numeric gate
rejects unsupported changes. This gate **does not guarantee factual correctness**:
review the original/revised comparison before unlocking DOCX and PDF downloads.
If a listing description is short or both providers are unavailable, the existing
resume wording is preserved and the dashboard explains why. No applications are
submitted automatically. Original CV stays in Streamlit session state, not the ZIP.

**Application workflow:** review changes, check the original employer job listing,
confirm the CV's factual accuracy, download DOCX/PDF, then apply manually through
its official application page. Automated submission is not included: it would require
separate employer-specific integration and explicit opt-in/approval.


## Version 3.0 improvements: job freshness and CV tailoring

- Both dashboard discovery and scheduled agent runs **exclude jobs without a verified timezone-aware publication date**, and jobs older than 7 x 24 hours. Adzuna queries include `max_days_old=7`, with a second local verification gate. CSV imports must include `posted_at` (ISO 8601 with timezone, e.g. `2026-11-08T12:00:00Z`); undated rows are excluded. `original_posted_at`, when supplied, takes precedence over repost dates.
- Existing database rows are migrated to retain `posted_at`. Old, undated jobs are hidden from active discovery and CV tailoring; previously submitted or prepared applications remain visible for tracking.
- AI tailoring now receives the original CV context so it can use skills supported elsewhere in the CV. Proposed rewrites still undergo a deterministic safety check, with accepted/rejected counts shown in the dashboard. No invented skills, metrics or credentials are permitted.
- AI rewrites require a configured LLM provider. Without one, the agent still produces a source-preserving, reordered CV; it cannot guarantee substantive rewriting. The generated documents must be reviewed before use.
- Date filtering verifies feed-provided timestamps; it does not independently verify employer websites or detect every disguised repost.


## Version 3.1: CV links and strict seven-day visibility

- DOCX hyperlink relationship targets and PDF URI annotations are extracted into the CV text, even when the displayed text is only “GitHub” or “LinkedIn”. URLs found in the CV are preserved as **clickable hyperlinks** in both exported DOCX and PDF. The application does not guess or invent missing profile URLs.
- AI is instructed to make only meaningful, evidence-backed edits and cannot rewrite lines containing portfolio links. The change preview and explicit candidate approval remain mandatory.
- Freshness uses the oldest verified date among `original_posted_at` and `posted_at`. Both are persisted in the database; older saved jobs are hidden from the active dashboard even if they were previously submitted. This is a strict visibility rule, not deletion of application history.
- Source caveat: Adzuna's `created` timestamp may describe aggregator publication, not the employer's first posting. The agent cannot guarantee the original employer posting is under seven days unless the source supplies that original date.

## 3.2 PostgreSQL / Supabase reliability update

This release fixes the PostgreSQL `InFailedSqlTransaction` error during tracked-job schema migration, makes schema initialization idempotent, shares the database connector between job storage and profile storage, improves missing-profile and missing-Adzuna-credential diagnostics in the scheduled CLI, and configures Groq primary / Gemini backup in GitHub Actions. See `SUPABASE_SETUP.md` for setup steps. Your existing tables and application statuses are retained.

Offline automated tests do not establish a live connection to your Supabase project or verify third-party APIs. A separate local SQLite store is still used for the optional browser application helper; it is not synchronized with Supabase.


## Optional additional job source: Remotive

Set `JOB_SOURCES=adzuna,remotive` in `.env` or Streamlit Secrets to search both Adzuna and Remotive. The default remains `adzuna`. Remotive is a public remote-job API; listings must link to Remotive and credit it as the source. It may include jobs restricted to certain countries, and some requirements (salary and language) still need manual verification. HireMeD does not guarantee that a job is English-only without explicit evidence.

The **Relevant jobs** view hides listings explicitly rejected by your preferences. Rejected listings can be inspected under **All (including rejected)**. Strong matches exclude rejected jobs; missing salary, work arrangement, or language evidence remains **Needs review**, not automatically eligible.
