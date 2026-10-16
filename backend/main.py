from pathlib import Path
from typing import Literal
import logging
import threading
import secrets
import time
from collections import OrderedDict
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from .engine import parse_pdf, build_report
from .market import ROLES, collect_market
from .pdf_report import generate_pdf, generate_summary_pdf

app = FastAPI(title='BridgeLabs curriculum analysis')
# Allow local development previews to use the local API; do not enable arbitrary websites.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r'http://(?:localhost|127\.0\.0\.1|\[::1\])(?::\d+)?',
    allow_methods=['GET', 'POST'],
    allow_headers=['Content-Type'],
)
ROOT = Path(__file__).resolve().parent.parent
ACTIVE = threading.BoundedSemaphore(2)
REPORTS = OrderedDict()
REPORT_LOCK = threading.Lock()
REPORT_TTL = 1800

@app.get('/api/health')
def health():
    return {'status': 'ok', 'service': 'bridgelabs', 'ai_required': False, 'market': 'JobSpy / International'}

@app.post('/api/analyze')
async def analyze(file: UploadFile = File(...), role: str = Form('backend')):
    if role not in ROLES:
        raise HTTPException(422, 'Choose a supported role.')
    if not (file.filename or '').lower().endswith('.pdf'):
        raise HTTPException(422, 'Upload a PDF file.')
    if not ACTIVE.acquire(blocking=False):
        raise HTTPException(429, 'Analysis is busy. Please retry shortly.')
    try:
        data = await file.read(10*1024*1024+1)
        if len(data) > 10*1024*1024:
            raise HTTPException(413, 'PDF must be at most 10 MB.')
        curriculum = await run_in_threadpool(parse_pdf, data)
        market = await run_in_threadpool(collect_market, role)
        report = build_report(curriculum, market, ROLES[role][0])
        report['jobs'] = [{k:v for k,v in j.items() if k != 'analysis_text'} for j in market['jobs']]
        report['filename'] = file.filename
        pdf = await run_in_threadpool(generate_pdf, report)
        summary_pdf = await run_in_threadpool(generate_summary_pdf, report)
        report_id = secrets.token_urlsafe(24)
        with REPORT_LOCK:
            for stale in [key for key,(created, _) in REPORTS.items() if time.monotonic()-created >= REPORT_TTL]:
                REPORTS.pop(stale)
            while len(REPORTS) >= 20:
                REPORTS.popitem(last=False)
            REPORTS[report_id] = (time.monotonic(), {'full': pdf, 'summary': summary_pdf})
        report['report_id'] = report_id
        return report
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logging.exception('Analysis failed')
        raise HTTPException(500, 'Analysis could not complete. Check server logs and retry.') from exc
    finally:
        await file.close()
        ACTIVE.release()

@app.get('/api/reports/{report_id}.pdf')
def download_pdf(report_id: str, version: Literal['full', 'summary'] = 'full'):
    with REPORT_LOCK:
        saved = REPORTS.get(report_id)
        if not saved or time.monotonic()-saved[0] >= REPORT_TTL:
            REPORTS.pop(report_id, None)
            raise HTTPException(404, 'Report expired or unavailable. Run the analysis again to download a fresh PDF.')
        pdf = saved[1][version]
    filename = 'bridgelabs-executive-summary.pdf' if version == 'summary' else 'bridgelabs-analysis.pdf'
    return Response(pdf, media_type='application/pdf', headers={
        'Content-Disposition': f'attachment; filename="{filename}"',
        'Cache-Control': 'no-store',
        'X-Content-Type-Options': 'nosniff',
    })

@app.get('/')
def index():
    return FileResponse(ROOT / 'index.html')

@app.get('/{asset}')
def asset(asset: str):
    if asset not in {'app.js', 'styles.css'}:
        raise HTTPException(404)
    return FileResponse(ROOT / asset)
