"""Bounded, isolated JobSpy collection. Partial outages remain visible."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
import hashlib
import multiprocessing
import re
import threading
import time
from urllib.parse import urlsplit, urlunsplit
from .skills import skills

ROLES = {
 'backend': ('Backend developer', r'backend|back.end|software|python|java|node|full.stack'),
 'frontend': ('Frontend developer', r'front.end|frontend|react|angular|web developer'),
 'fullstack': ('Full stack developer', r'full.stack|fullstack|software|web developer'),
 'data': ('Data analyst', r'data analyst|business analyst|analytics|data science'),
 'ml': ('Machine learning engineer', r'machine learning|\bml\b|data scien|\bai\b'),
 'devops': ('DevOps engineer', r'devops|cloud|platform engineer|site reliability'),
}
CACHE = {}
CACHE_LOCK = threading.Lock()
COLLECTION_LOCK = threading.Lock()
TTL = 1800
# Indeed requires a country per search; use several markets instead of its US default.
SEARCHES = [('indeed', country) for country in ('USA', 'UK', 'Canada', 'Australia', 'Germany', 'Singapore', 'India')] + [('linkedin', 'Worldwide')]


def clean(value):
    return '' if value is None or str(value).lower() in ('nan', 'nat', 'none', '<na>') else str(value)


def scrape_board(board, query, country):
    from jobspy import scrape_jobs
    frame = scrape_jobs(site_name=[board], search_term=f'junior {query}', location=None if country == 'Worldwide' else country,
        country_indeed=country if board == 'indeed' else 'USA', results_wanted=20, hours_old=24*30,
        fetch_description=True, description_format='markdown', verbose=0)
    return frame.to_dict('records'), frame.attrs


def normalize(records, role):
    jobs, seen = [], set()
    excluded = {'duplicate': 0, 'senior_or_unknown_level': 0, 'irrelevant_role': 0, 'missing_description': 0, 'outside_date_window': 0}
    for row in records:
        title, company = clean(row.get('title')), clean(row.get('company'))
        if not re.search(ROLES[role][1], title, re.I):
            excluded['irrelevant_role'] += 1
            continue
        description = clean(row.get('description'))
        experience = clean(row.get('experience_range'))
        level_text = ' '.join((title, clean(row.get('job_level')), experience, description[:3000]))
        ranges = re.findall(r'(\d+)\s*(?:-|–|to)\s*\d+\s*years?', level_text, re.I)
        minimums = re.findall(r'(?:minimum|at least)\s+(\d+)\s*(?:\+\s*)?years?|\b(\d+)\s*\+\s*years?', level_text, re.I)
        explicit_range = re.search(r'(\d+)\s*(?:-|–|to)\s*(\d+)', experience)
        junior_range = bool(explicit_range and int(explicit_range[1]) <= 2)
        high_minimum = bool(explicit_range and int(explicit_range[1]) >= 3) or any(int(x) >= 3 for x in ranges) or any(int(a or b) >= 3 for a,b in minimums)
        if re.search(r'\b(senior|sr\.?|lead|principal|staff|manager|architect)\b', title, re.I) or high_minimum or not (junior_range or re.search(r'junior|entry.level|fresher|graduate|intern|associate|\b[012]\s*(?:-|–|to)\s*[123]\s*years?', level_text, re.I)):
            excluded['senior_or_unknown_level'] += 1
            continue
        if len(description.strip()) < 100:
            excluded['missing_description'] += 1
            continue
        posted = clean(row.get('date_posted'))[:10]
        if posted:
            try:
                if not date.today()-timedelta(days=30) <= date.fromisoformat(posted) <= date.today():
                    excluded['outside_date_window'] += 1
                    continue
            except ValueError:
                posted = ''
        url = clean(row.get('job_url'))
        parsed = urlsplit(url)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            continue
        normalized_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ''))
        identity = re.sub(r'\W+', '', f'{company}|{title}'.lower()) if company and title else normalized_url
        if identity in seen:
            excluded['duplicate'] += 1
            continue
        seen.add(identity)
        text = description + '\n' + clean(row.get('skills'))
        jobs.append({'id': hashlib.sha256(identity.encode()).hexdigest()[:12], 'title': title, 'company': company,
            'url': url, 'site': clean(row.get('site')), 'location': clean(row.get('location')),
            'search_market': clean(row.get('search_market')), 'date_posted': posted or None, 'seniority': 'entry-level signal detected',
            'skills': sorted(skills(text)), 'analysis_text': text})
    return jobs, excluded


def collect_market(role):
    key = (role, 'international-v1')
    with CACHE_LOCK:
        cached = CACHE.get(key)
        if cached and time.monotonic()-cached[0] < TTL:
            return {**cached[1], 'cached': True}
    # Bound concurrent scraping and process count for the local service.
    if not COLLECTION_LOCK.acquire(blocking=False):
        raise ValueError('Another market search is running. Please retry shortly.')
    try:
        with CACHE_LOCK:
            for stale_key in [k for k,v in CACHE.items() if time.monotonic()-v[0] >= TTL]:
                CACHE.pop(stale_key)
        records, statuses, warnings = [], [], []
        ctx = multiprocessing.get_context('spawn')
        pool = ProcessPoolExecutor(max_workers=4, mp_context=ctx)
        futures = {pool.submit(scrape_board, board, ROLES[role][0], country): (board, country) for board, country in SEARCHES}
        completed = set()
        try:
            try:
                for future in as_completed(futures, timeout=70):
                    board, country = futures[future]
                    completed.add(future)
                    label = f'{board} / {country}'
                    try:
                        rows, attrs = future.result()
                        for row in rows:
                            row['search_market'] = country
                        records.extend(rows)
                        errors = attrs.get('errors', {})
                        board_warnings = attrs.get('warnings', {})
                        statuses.append({'source': label, 'country': country, 'status': 'partial/error' if errors else 'returned' if rows else 'empty', 'fetched': len(rows)})
                        if errors or board_warnings or not rows:
                            warnings.append(f'{label}: source reported errors/warnings or returned no results; coverage may be incomplete.')
                    except Exception:
                        statuses.append({'source': label, 'country': country, 'status': 'unavailable', 'fetched': 0})
                        warnings.append(f'{label}: collection failed.')
            except TimeoutError:
                pass
            for future in futures.keys() - completed:
                board, country = futures[future]
                label = f'{board} / {country}'
                statuses.append({'source': label, 'country': country, 'status': 'timed out', 'fetched': 0})
                warnings.append(f'{label}: exceeded the 70-second collection budget.')
        finally:
            # Python 3.14 can kill timed-out workers; older runtimes use process termination.
            if any(not f.done() for f in futures):
                if hasattr(pool, 'terminate_workers'):
                    pool.terminate_workers()
                else:
                    for process in (getattr(pool, '_processes', {}) or {}).values():
                        process.terminate()
                    pool.shutdown(wait=False, cancel_futures=True)
            else:
                pool.shutdown(wait=False, cancel_futures=True)
        jobs, excluded = normalize(records, role)
        result = {'jobs': jobs, 'focus': 'International', 'location_query': 'Across countries', 'searched_markets': [country for _, country in SEARCHES], 'role_query': ROLES[role][0],
            'collected_at': datetime.now(timezone.utc).isoformat(), 'cached': False, 'cache_ttl_seconds': TTL,
            'sources': statuses, 'fetched_count': len(records), 'excluded': excluded, 'date_window_days': 30,
            'warnings': warnings + ['International sample: Indeed searches USA, UK, Canada, Australia, Germany, Singapore and India; LinkedIn has no location filter. This is not exhaustive worldwide coverage. Check work locations and eligibility in linked postings.',
                                    'Missing posting dates are retained and marked unknown. Results are a sample, not a census.']}
        if jobs:
            with CACHE_LOCK:
                if len(CACHE) >= 20:
                    CACHE.pop(next(iter(CACHE)))
                CACHE[key] = (time.monotonic(), result)
        return result
    finally:
        COLLECTION_LOCK.release()
