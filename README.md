# BridgeLabs

Curriculum-to-career workspace with a FastAPI backend and the existing vanilla HTML/CSS/JavaScript interface. Upload a searchable syllabus PDF to compare its skill mentions with an international entry-level job sample collected using JobSpy.

## Run locally

Python 3.10+ is required (tested with Python 3.14).

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. A local preview such as `http://127.0.0.1:5500/index.html` can also connect to the backend at port 8000: the frontend checks availability before uploading. The Python backend must still be running. Opening `index.html` as a `file://` URL requires switching to the HTTP address above. Local HTTP preview origins are allowed; remote websites are not. No AI key, database, Node build, or account is required.

Select a PDF (10 MB / 100 pages maximum), and target role. Click **Analyze curriculum**. Live collection has a 70-second budget plus PDF processing; the browser allows 120 seconds. First use imports scraping dependencies and can be slower. Source outages are shown in the report; retry later if all boards are unavailable. Successful market samples are cached in server memory for 30 minutes (up to 20 searches). The PDF and report are not stored on disk by the application; generated PDF exports are held in a bounded in-memory cache. Multipart uploads can use framework-managed temporary files during request handling.

## Implemented analysis

- Layout-preserving `pdfplumber` text extraction with page references, explicit CO-numbered outcome lines, foundational concepts, catalog skills, and conservative legacy-version mentions.
- International searches through pinned `python-jobspy==1.2.0`: Indeed across USA, UK, Canada, Australia, Germany, Singapore and India, plus LinkedIn without a location filter. Up to 20 postings per search, up to four workers (`JOBSPY_WORKERS`, default 4; Render configuration uses 2), junior role queries, and a 30-day date window where dates are available. This bounded sample is not exhaustive worldwide coverage.
- Per-source failure reporting, isolated scrape processes with a time budget, bounded concurrent collection, in-memory caching, title relevance checks, seniority heuristics, missing-description exclusion, and employer/title deduplication.
- Six selectable role profiles: backend, frontend, full stack, data analyst, ML, and DevOps. Each report evaluates one selected role, making its denominator explicit.
- Alias-normalized skill demand, demand-weighted **syllabus mention coverage**, four gap categories, and evidence links/excerpts. Demand counts each skill at most once per posting. Missing PDF mentions are possible gaps, never proof a skill is not taught.
- Up to six optional 40-minute lab outlines anchored to a detected syllabus foundation, with possible original CO links, prerequisites, tasks, suggested rubrics, and verification checklists. Advanced tools are excluded from automatic lab patches. Outcomes are quoted without rewriting; mappings require faculty review.
- Source diagnostics, filtering counts, limitations, live/cached collection timestamps, safe text rendering, and two PDF downloads at the top of results: a full report (evidence, gaps, labs, job links, and methodology) and a two-page Executive Summary (key metrics, top five skill gaps, up to three lab next steps, and evidence-quality context).

## Method and limits

`backend/skills.py` is a small, auditable alias catalog, **not** an ESCO/O*NET integration or an embedding model. Coverage is the sum of posting counts for skills mentioned in the syllabus divided by the sum of posting counts for all detected skills. It is null when no skills are detected in the job sample. It does not measure student competence, syllabus depth, or the whole global market. Low-sample warnings appear below 15 eligible postings. Optional, negated, historical, and textbook mentions can produce false positives.

Job-board search results may be biased, incomplete, blocked, or include remote roles and unknown posting dates. Unknown seniority is excluded; retained postings have textual entry-level signals rather than verified experience requirements. Unknown posting dates are retained and labeled. Employer/title deduplication may merge distinct vacancies. Countries are sampled automatically with no location input; individual work locations and eligibility still need verification. The pooled demand percentages reflect returned postings, not equal country weights. Job descriptions can contain senior or unrelated requirements; the rule catalog does not distinguish required versus preferred skills.

Complex tables, scanned PDFs, wrapped CO statements, metadata, units, and individual lab boundaries do not receive full semantic reconstruction. Image-only PDFs need external OCR first. Legacy tools are flagged as mentions to inspect, without unsupported EOL dates or declaring foundational theory obsolete. Lab patches are reviewed outlines, not generated solution manuals, executable test suites, starter repositories, or proven 40-minute tasks. GitHub verification, accounts, automatic grading, OCR, and semantic outcome mapping are future work.

## Is GPT-4o-mini needed?

**No for the implemented pipeline.** PDF extraction, job ingestion, counts, evidence, and templated lab recommendations run without AI. For deeper semantic syllabus interpretation or custom faculty manuals, GPT-4o-mini could be an optional server-side enrichment layer later. It should receive retrieved evidence and preserve original outcomes; it should never invent jobs or change deterministic counts. Do not put API keys in `app.js` or commit them. This version makes no OpenAI requests.

## API

- `GET /api/health` — availability and AI requirement.
- `POST /api/analyze` — multipart `file`, `role` (default `backend`). Returns curriculum evidence, market diagnostics, summary, demands, gaps, lab outlines, job provenance, and a `report_id`. Empty market evidence returns a valid report with null coverage and no fabricated recommendations.

- `GET /api/reports/{report_id}.pdf` - download the full PDF snapshot generated with the analysis. Add `?version=summary` for the two-page Executive Summary; `?version=full` is the default. Up to 20 exports are held in server memory for 30 minutes, protected by unguessable report IDs; restarting the server clears them. Expired exports return 404 and require rerunning analysis. No rescrape occurs on download.

## Verify

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
node --test tests/test_connection.cjs
```

Tests use generated searchable PDFs and controlled job fixtures; they do not depend on changing external boards. Use an actual PDF in the UI to exercise live collection. This is a local prototype: before public deployment add authentication, request-body limits at a reverse proxy, rate limits, and retention controls. Only static assets are exposed; project files and dependencies are not served.

JobSpy documentation: https://github.com/speedyapply/JobSpy


## Deploy with a public URL (Render)

The repository includes `render.yaml` and `.python-version`. The configuration runs the Python backend and website together, so uploads and both PDF downloads work on one HTTPS address. Deploy this as a **Web Service**, not a Static Site. No frontend build or separate Firebase project is needed.

1. Commit the current project, including `backend/`, `requirements.txt`, `render.yaml`, and `.python-version`, and push it to your GitHub repository. Keep `.venv/`, `.env`, and uploaded PDFs out of Git.
2. Sign in at https://dashboard.render.com and select **New > Blueprint**.
3. Connect the BridgeLabs repository and select the branch containing these changes. If BridgeLabs is inside a larger repository, put the Blueprint at that repository's root and set the service's `rootDir` to the BridgeLabs subdirectory first. The supplied configuration assumes BridgeLabs is the repository root.
4. Review the configuration and deploy. The supplied plan is **Free**; check the displayed plan before confirming. Render will install Python dependencies and start the service.
5. Open the actual `https://<assigned-service-name>.onrender.com` URL shown by Render. The assigned name may differ from `bridgelabs`. This is your shareable URL; localhost addresses are only for your computer.
6. Check `/api/health` on that URL, upload a small searchable PDF, run an analysis, and test both the full-report and Executive Summary downloads. A successful health check proves the service is running, not that every job board is reachable.

If you create a Web Service manually instead of using a Blueprint, use:

| Setting | Value |
| --- | --- |
| Runtime | Python 3 |
| Build command | `python -m pip install -r requirements.txt` |
| Start command | `python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT --workers 1` |
| Health check | `/api/health` |
| Environment variable | `JOBSPY_WORKERS=2` |
| Instances | 1 |

Render reads Python `3.14.6` from `.python-version`, matching the local test environment. Keep **one API worker and one instance**: PDFs and market results currently live in process memory. More instances or API workers require shared report storage/cache first. Do not use `--reload` in the hosted start command.

The frontend uses the hosting site's own `/api` endpoints automatically. No hardcoded public API URL or broad CORS rule is required. Local preview fallback remains available only when the page is served from localhost.

### Hosting limits to consider

- Free Render services sleep after 15 minutes without inbound traffic and take time to wake up. Open the site before demonstrating it. Restarting, sleeping, or redeploying clears cached reports; users must rerun analysis before downloading again.
- The free instance has limited memory and CPU. Two scrape workers reduce peak memory compared with four, but this is not a guarantee that large PDFs or every search will fit. If logs show memory exhaustion or repeated timeouts, use a larger instance, reduce `JOBSPY_WORKERS` to 1, or move collection to a background job. Lower concurrency can mean fewer sources finish within the existing 70-second collection budget.
- Job boards can block cloud/datacenter IPs or throttle requests. A working public URL does not guarantee JobSpy coverage. Inspect the report's source diagnostics on the hosted service; if the chosen host is blocked, address the data provider/access method rather than hiding the failure or inventing sample results.
- This configuration is for a small demonstration of the current prototype. The existing concurrency limits do not provide user authentication or per-user rate limiting. For broader public use, add those controls and shared durable report storage before scaling.

### Why not Firebase Hosting alone?

Firebase Hosting serves static files; this app also needs a Python backend. Hosting rewrites to Cloud Run/Functions have a 60-second request timeout, shorter than the current 70-second job collection budget plus parsing and PDF generation. A direct Cloud Run service is a viable Google Cloud alternative, but the current in-memory reports require one instance/worker or shared storage. Render avoids splitting the frontend and backend for this first deployment.

References: [Render FastAPI deployment](https://render.com/docs/deploy-fastapi), [Python version selection](https://render.com/docs/python-version), [Render free-service limits](https://render.com/docs/free), [Firebase dynamic-content limits](https://firebase.google.com/docs/hosting/serverless-overview).
