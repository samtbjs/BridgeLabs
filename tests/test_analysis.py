from datetime import date, timedelta
from io import BytesIO
import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from backend.engine import parse_pdf, build_report
from backend.market import normalize
from backend.skills import skills
from backend.main import app


def pdf_bytes():
    output = BytesIO()
    c = canvas.Canvas(output)
    for y, text in enumerate(['Database Management Systems CS304',
          'CO1: Apply database normalization and relational algebra.',
          'Unit 1: SQL, database transactions, indexing and ACID properties.',
          'Lab: Execute transactions using Oracle 9i. Preserve database theory.']):
        c.drawString(40, 780-y*30, text)
    c.save()
    return output.getvalue()


def row(**overrides):
    return {'title': 'Junior Backend Developer', 'company': 'Example', 'job_url': 'https://example.org/jobs/1',
       'site': 'indeed', 'date_posted': date.today().isoformat(), 'location': 'Bengaluru, India',
       'description': 'Junior developer with 0-2 years experience. Build PostgreSQL database applications with SQL, Git and Docker. Write unit tests for backend services.', **overrides}


def market(rows):
    jobs, excluded = normalize(rows, 'backend')
    return {'jobs': jobs, 'warnings': [], 'excluded': excluded}


def test_pdf_evidence_and_outcomes():
    parsed = parse_pdf(pdf_bytes())
    assert parsed['page_count'] == 1
    assert parsed['course_outcomes'][0]['id'] == 'CO1'
    assert parsed['legacy_mentions'][0]['tool'] == 'Oracle 9i'
    assert {s['skill'] for s in parsed['skills']} == {'SQL'}


def test_alias_boundaries():
    assert 'Java' not in skills('JavaScript for web pages')
    assert 'Git' not in skills('digital acquisition')
    assert 'SQL' not in skills('PostgreSQL')
    assert {'C++', 'CI/CD', 'Git', 'Node.js'} <= skills('C++, CI/CD, GitHub and Node.js')


def test_exclusions_dedup_and_demand():
    rows = [row(), row(site='linkedin'), row(title='Senior Backend Developer'),
            row(title='Junior Sales Associate'), row(company='Old', date_posted=(date.today()-timedelta(days=90)).isoformat()),
            row(company='No text', description=''), row(company='Senior disguised', description='Junior developer with minimum 5 years experience. '+ 'PostgreSQL '*20)]
    m = market(rows)
    assert len(m['jobs']) == 1
    assert m['excluded']['duplicate'] == 1
    assert m['excluded']['senior_or_unknown_level'] == 2
    report = build_report(parse_pdf(pdf_bytes()), m, 'Backend developer')
    assert report['summary']['mention_alignment_percent'] == 20
    assert next(d for d in report['skill_demand'] if d['skill'] == 'Git')['job_count'] == 1
    lab = next(l for l in report['lab_patches'] if l['skill'] == 'PostgreSQL')
    assert lab['course_outcome']['id'] == 'CO1'
    assert lab['duration_minutes'] == 40
    assert sum(lab['rubric'].values()) == 100


def test_empty_market_is_not_fake_score():
    report = build_report(parse_pdf(pdf_bytes()), market([]), 'Backend developer')
    assert report['summary']['mention_alignment_percent'] is None
    assert report['gaps'] == report['lab_patches'] == []


def test_invalid_and_scanned_pdfs():
    with pytest.raises(ValueError):
        parse_pdf(b'not a pdf')
    output = BytesIO(); c = canvas.Canvas(output); c.showPage(); c.save()
    with pytest.raises(ValueError, match='OCR'):
        parse_pdf(output.getvalue())


def test_api_real_pdf_and_mock_market(monkeypatch):
    monkeypatch.setattr('backend.main.collect_market', lambda role: market([row()]))
    client = TestClient(app)
    response = client.post('/api/analyze', files={'file': ('course.pdf', pdf_bytes(), 'application/pdf')}, data={'role':'backend'})
    assert response.status_code == 200
    assert response.json()['summary']['analyzed_jobs'] == 1
    assert 'analysis_text' not in response.json()['jobs'][0]
    assert client.post('/api/analyze', files={'file': ('x.pdf', b'bad')}).status_code == 422
    assert client.post('/api/analyze', files={'file': ('x.pdf', pdf_bytes())}, data={'role':'bad'}).status_code == 422
    assert client.get('/.env').status_code == 404
    assert client.get('/').status_code == 200


def test_missing_skill_is_not_claimed_as_missing_theory():
    report = build_report(parse_pdf(pdf_bytes()), market([row()]), 'Backend developer')
    gap = next(g for g in report['gaps'] if g['skill'] == 'PostgreSQL')
    assert gap['foundation'] == 'database'
    assert gap['syllabus_anchor']['page'] == 1
    assert gap['evidence'][0]['url'].startswith('https://')


def test_naukri_experience_range_filters_senior_and_keeps_junior():
    m = market([row(company='Junior', title='Backend Developer', experience_range='0 - 2', description='Develop PostgreSQL applications. '+ 'Database services and reliable delivery. '*5),
                row(company='Senior', experience_range='5 - 8')])
    assert len(m['jobs']) == 1
    assert m['jobs'][0]['company'] == 'Junior'
    assert m['excluded']['senior_or_unknown_level'] == 1


def test_collection_partial_failure_and_cache(monkeypatch):
    import backend.market as module
    module.CACHE.clear()
    calls = []
    class Pool:
        def __init__(self, **kwargs): pass
        def submit(self, fn, board, query, country):
            from concurrent.futures import Future
            future = Future()
            calls.append((board, country))
            if board == 'linkedin': future.set_exception(RuntimeError('blocked'))
            else: future.set_result(([row(company=country, location=country)] if country == 'USA' else [], {}))
            return future
        def shutdown(self, **kwargs): pass
    monkeypatch.setattr(module, 'ProcessPoolExecutor', Pool)
    first = module.collect_market('backend')
    assert len(first['jobs']) == 1
    assert next(s for s in first['sources'] if s['source'] == 'linkedin / Worldwide')['status'] == 'unavailable'
    second = module.collect_market('backend')
    assert second['cached'] is True
    assert calls == module.SEARCHES
    assert first['focus'] == 'International'
    assert {'USA', 'UK', 'India', 'Worldwide'} <= set(first['searched_markets'])
    module.CACHE.clear()


def test_local_preview_cors_and_remote_origin_rejection():
    client = TestClient(app)
    for origin in ('http://127.0.0.1:5500', 'http://localhost:5500', 'http://[::1]:5500'):
        response = client.options('/api/analyze', headers={
            'Origin': origin, 'Access-Control-Request-Method':'POST'})
        assert response.status_code == 200
        assert response.headers['access-control-allow-origin'] == origin
    for origin in ('https://example.com', 'http://127.0.0.1.attacker.test:5500', 'null'):
        response = client.options('/api/analyze', headers={
            'Origin':origin, 'Access-Control-Request-Method':'POST'})
        assert response.status_code == 400
        assert 'access-control-allow-origin' not in response.headers


def test_report_download_is_valid_pdf_and_expires(monkeypatch):
    import backend.main as main
    import pdfplumber
    monkeypatch.setattr(main, 'collect_market', lambda role: market([row()]))
    client = TestClient(app)
    result = client.post('/api/analyze', files={'file': ('course.pdf', pdf_bytes(), 'application/pdf')})
    assert result.status_code == 200
    report_id = result.json()['report_id']
    response = client.get(f'/api/reports/{report_id}.pdf')
    assert response.headers['content-type'] == 'application/pdf'
    assert 'bridgelabs-analysis.pdf' in response.headers['content-disposition']
    assert response.content.startswith(b'%PDF-')
    with pdfplumber.open(BytesIO(response.content)) as pdf:
        text = '\n'.join(p.extract_text() or '' for p in pdf.pages)
    for section in ['Curriculum evidence', 'Skill demand', 'Prioritized gaps', 'Optional lab extensions', 'Job evidence directory', 'Limitations', 'PostgreSQL', 'https://example.org/jobs/1']:
        assert section in text
    summary_response = client.get(f'/api/reports/{report_id}.pdf?version=summary')
    assert summary_response.headers['content-type'] == 'application/pdf'
    assert 'bridgelabs-executive-summary.pdf' in summary_response.headers['content-disposition']
    with pdfplumber.open(BytesIO(summary_response.content)) as summary_pdf:
        assert len(summary_pdf.pages) == 2
        summary_text = '\n'.join(p.extract_text() or '' for p in summary_pdf.pages)
    assert 'Executive Summary' in summary_text
    assert 'Recommended Next Steps' in summary_text
    assert 'PostgreSQL' in summary_text
    with pdfplumber.open(BytesIO(response.content)) as full_pdf:
        assert len(full_pdf.pages) > 2
    assert client.get(f'/api/reports/{report_id}.pdf?version=invalid').status_code == 422
    created, data = main.REPORTS[report_id]
    main.REPORTS[report_id] = (created-main.REPORT_TTL-1, data)
    assert client.get(f'/api/reports/{report_id}.pdf').status_code == 404
    assert client.get(f'/api/reports/{report_id}.pdf?version=summary').status_code == 404
    assert client.get('/api/reports/unknown.pdf').status_code == 404


def test_search_parameters_do_not_default_every_market_to_india(monkeypatch):
    import jobspy
    from backend.market import scrape_board
    captured = []
    class Frame:
        attrs = {}
        def to_dict(self, mode): return []
    monkeypatch.setattr(jobspy, 'scrape_jobs', lambda **kw: captured.append(kw) or Frame())
    scrape_board('indeed', 'Backend developer', 'Canada')
    scrape_board('linkedin', 'Backend developer', 'Worldwide')
    assert captured[0]['country_indeed'] == captured[0]['location'] == 'Canada'
    assert captured[1]['location'] is None


def test_summary_remains_two_pages_for_large_reports():
    import copy
    import pdfplumber
    from backend.pdf_report import generate_summary_pdf
    report = build_report(parse_pdf(pdf_bytes()), market([row()]), 'Backend developer')
    report['filename'] = 'Very long curriculum title ' * 200
    report['role'] = 'Backend developer ' * 200
    report['market']['sources'] = [{'source':'example', 'fetched':20} for _ in range(100)]
    lab = next(l for l in report['lab_patches'] if l['skill'] == 'PostgreSQL')
    report['lab_patches'] = [copy.deepcopy(lab) for _ in range(6)]
    for l in report['lab_patches']:
        l['title'] *= 100
        l['tasks'] = ['Very long task ' * 200] * 3
        l['prerequisites'] *= 100
    pdf = generate_summary_pdf(report)
    with pdfplumber.open(BytesIO(pdf)) as document:
        assert len(document.pages) == 2
        assert all(30 <= c['top'] <= page.height-25 for page in document.pages for c in page.chars)


def test_empty_evidence_summary_has_no_fabricated_recommendations():
    import pdfplumber
    from backend.pdf_report import generate_summary_pdf
    report = build_report(parse_pdf(pdf_bytes()), market([]), 'Backend developer')
    with pdfplumber.open(BytesIO(generate_summary_pdf(report))) as document:
        assert len(document.pages) == 2
        text = '\n'.join(p.extract_text() or '' for p in document.pages)
    assert 'Insufficient evidence' in text
    assert 'No market-backed missing skills' in text
