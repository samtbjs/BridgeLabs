from collections import Counter
from datetime import datetime, timezone
from io import BytesIO
import re
import pdfplumber
from .skills import CATALOG, THEORY, LEGACY, ADVANCED, evidence, skills


def parse_pdf(data):
    if not data.startswith(b'%PDF-'):
        raise ValueError('The file is not a valid PDF.')
    try:
        with pdfplumber.open(BytesIO(data)) as pdf:
            if len(pdf.pages) > 100:
                raise ValueError('Please upload at most 100 pages at a time.')
            pages = [{'page': i+1, 'text': (page.extract_text(layout=True) or '').strip()}
                     for i, page in enumerate(pdf.pages)]
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('Cannot read this PDF. Remove password protection or export it again.') from exc
    text = '\n'.join(p['text'] for p in pages)
    if len(re.sub(r'\s', '', text)) < 80:
        raise ValueError('Too little readable text. This may be a scanned PDF; OCR is not included. Upload a searchable PDF.')
    outcomes = []
    for p in pages:
        for line in p['text'].splitlines():
            m = re.match(r'^\s*(CO\s*\d+)\s*[:.\-–]?\s+(.+)', line, re.I)
            if m:
                outcomes.append({'id': re.sub(r'\s', '', m[1]).upper(), 'statement': m[2].strip(), 'page': p['page']})
    detected = []
    for name, spec in CATALOG.items():
        for p in pages:
            excerpt = evidence(p['text'], spec[0])
            if excerpt:
                detected.append({'skill': name, 'page': p['page'], 'excerpt': excerpt})
                break
    concepts = [name for name, aliases in THEORY.items() if evidence(text, aliases)]
    legacy = []
    for name, aliases in LEGACY.items():
        for p in pages:
            excerpt = evidence(p['text'], aliases)
            if excerpt:
                legacy.append({'tool': name, 'page': p['page'], 'excerpt': excerpt,
                    'rationale': 'Legacy version mentioned. Faculty should check whether this is prescribed tooling or historical context before updating the lab.'})
                break
    return {'page_count': len(pages), 'pages': pages, 'skills': detected, 'concepts': concepts,
            'course_outcomes': outcomes, 'legacy_mentions': legacy,
            'warnings': ([f"{sum(not p['text'] for p in pages)} page(s) have no extractable text; coverage may be incomplete."] if any(not p['text'] for p in pages) else [])}


def build_report(curriculum, market, role):
    covered = {s['skill'] for s in curriculum['skills']}
    jobs = market['jobs']
    counts = Counter(s for j in jobs for s in set(j['skills']))
    denominator = len(jobs)
    total = sum(counts.values())
    alignment = round(100 * sum(n for s, n in counts.items() if s in covered) / total, 1) if total else None
    demands, gaps, labs = [], [], []
    for name, n in counts.most_common():
        spec = CATALOG[name]
        witnesses = [{'job_id': j['id'], 'url': j['url'], 'excerpt': evidence(j['analysis_text'], spec[0])} for j in jobs if name in j['skills']][:3]
        demand = {'skill': name, 'job_count': n, 'share_percent': round(100*n/denominator, 1),
                  'curriculum_status': 'mentioned' if name in covered else 'not found', 'evidence': witnesses}
        demands.append(demand)
        if name in covered:
            continue
        anchor = spec[2]
        anchor_page = next((p for p in curriculum['pages'] if evidence(p['text'], THEORY.get(anchor, [anchor]))), None)
        outcome = next((co for co in curriculum['course_outcomes'] if evidence(co['statement'], THEORY.get(anchor, [anchor]))), None)
        priority = 'High' if n >= 3 and n/denominator >= .3 else 'Medium' if n >= 2 else 'Exploratory'
        gap = {**demand, 'category': spec[1], 'priority': priority, 'foundation': anchor,
               'syllabus_anchor': {'page': anchor_page['page'], 'excerpt': evidence(anchor_page['text'], THEORY[anchor])} if anchor_page else None,
               'course_outcome': outcome, 'interpretation': 'Not found in extracted text; this does not prove the skill is not taught.'}
        gaps.append(gap)
        if len(labs) < 6 and anchor_page and name not in ADVANCED:
            labs.append({'skill': name, 'title': f'{name}: extend your existing {anchor} lab',
                'duration_minutes': 40, 'foundation': anchor, 'page': anchor_page['page'], 'course_outcome': outcome,
                'faculty_review_required': True, 'prerequisites': f'Existing {anchor} assignment; instructor-prepared starter environment for {name}.',
                'tasks': ['Reuse the inputs, learning objective, and core logic of the current assignment.', spec[3],
                          'Record the result and one limitation in the assignment README.'],
                'rubric': {'Original concept correctness': 40, 'Working extension and repeatable checks': 40, 'Explanation and reproducibility': 20},
                'verification_checklist': ['Core assignment still produces expected output.', 'Extension has a repeatable demonstration or automated check.', 'README records setup, commands, and observed results.'],
                'faculty_notes': 'Prepare the starter environment before class. Keep the original outcome text and marks; use this optional 40-minute extension only after confirming prerequisites. This is a task outline, not a generated or verified grading harness.'})
    return {'generated_at': datetime.now(timezone.utc).isoformat(), 'role': role, 'market': {k:v for k,v in market.items() if k != 'jobs'},
            'curriculum': {k:v for k,v in curriculum.items() if k != 'pages'},
            'summary': {'analyzed_jobs': denominator, 'detected_curriculum_skills': len(covered), 'demanded_skills': len(counts),
                'missing_skills': len(gaps), 'mention_alignment_percent': alignment},
            'methodology': 'Demand = unique eligible postings mentioning a catalog skill / all eligible postings. Alignment = matched skill mentions weighted by posting frequency / all detected skill mentions. Each skill counts once per posting. This is syllabus mention coverage, not student readiness or a representative estimate of the global job market.',
            'limitations': ['Rule-based alias matching can miss implicit skills and misread negated or optional requirements.',
                'Only a bounded sample of a selected role is searched. Cross-board duplicates without common titles and employers may remain.',
                'Seniority and role relevance use conservative text heuristics; unknown seniority is excluded.',
                'Course outcomes are extracted from explicit CO-numbered lines; wrapped lines and complex tables need faculty review.',
                'Lab outlines require instructor review and prepared environments; no GitHub competence verification is performed.'],
            'skill_demand': demands, 'gaps': gaps, 'lab_patches': labs,
            'warnings': curriculum['warnings'] + market['warnings'] + (['No catalog skill mentions detected in usable jobs; coverage cannot be calculated.'] if denominator and not total else []) + (['Fewer than 15 usable postings: interpret percentages cautiously.'] if denominator < 15 else [])}
