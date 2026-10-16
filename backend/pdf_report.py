"""Paginated PDF export of the exact server-generated report snapshot."""
from io import BytesIO
from pathlib import Path
import re
from urllib.parse import urlsplit
from xml.sax.saxutils import escape
import reportlab
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

FONT_DIR = Path(reportlab.__file__).parent / 'fonts'
for name, file in [('BridgeSans', 'Vera.ttf'), ('BridgeSans-Bold', 'VeraBd.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / file)))
pdfmetrics.registerFontFamily('BridgeSans', normal='BridgeSans', bold='BridgeSans-Bold', italic='BridgeSans', boldItalic='BridgeSans-Bold')
GLYPHS = pdfmetrics.getFont('BridgeSans').face.charToGlyph
GREEN = colors.HexColor('#214c3e')
MUTED = colors.HexColor('#5c6c65')


def safe_text(value):
    text = str(value if value is not None else 'Unknown')
    text = text.translate(str.maketrans({'\u2011':'-', '\u2013':'-', '\u2014':'-', '\u2022':'-'}))
    text = ''.join(c if ord(c) in GLYPHS or c in '\n\t' else '?' for c in text)
    return escape(re.sub(r'[\x00-\x08\x0b-\x1f]', '', text)).replace('\n', '<br/>')


def generate_pdf(report):
    output = BytesIO()
    body = ParagraphStyle('Body', fontName='BridgeSans', fontSize=9, leading=14, spaceAfter=8, textColor=GREEN, splitLongWords=1)
    heading = ParagraphStyle('Section', parent=body, fontName='BridgeSans-Bold', fontSize=16, leading=21, spaceBefore=14, spaceAfter=12, keepWithNext=True)
    sub = ParagraphStyle('Sub', parent=body, fontName='BridgeSans-Bold', fontSize=11, leading=16, spaceBefore=10, keepWithNext=True)
    small = ParagraphStyle('Small', parent=body, fontSize=8, leading=12, textColor=MUTED)
    title = ParagraphStyle('Title', parent=heading, fontSize=27, leading=33, spaceBefore=18, spaceAfter=18)
    story = []
    def p(text, style=body): story.append(Paragraph(safe_text(text), style))
    def h(text): p(text, heading)
    def lines(items):
        for item in items: p('- ' + str(item))
    def link(url, label='Source posting'):
        parsed = urlsplit(str(url or ''))
        if parsed.scheme in ('http', 'https') and parsed.netloc:
            target = escape(str(url), {'"':'&quot;', "'":'&#39;'})
            story.append(Paragraph(f'<link href="{target}" color="#276c59">{safe_text(label)}: {safe_text(url)}</link>', small))
    def table(headers, rows, widths):
        data = [[Paragraph(safe_text(v), small) for v in headers]]
        data += [[Paragraph(safe_text(v), small) for v in row] for row in rows]
        grid = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
        grid.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf2e6')),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),
            ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
            ('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#e1e6dc'))]))
        story.append(grid)
        story.append(Spacer(1,12))
    def outcome(co):
        if co: p(f"Possible original outcome link (faculty review): {co['id']} - {co['statement']} (p.{co['page']})")
        else: p('No explicit course outcome mapping found.', small)
    market, curriculum, summary = report['market'], report['curriculum'], report['summary']
    p('BRIDGELABS / CURRICULUM-TO-CAREER', sub)
    p('Your curriculum.\nYour next steps.', title)
    p(report.get('filename', 'Curriculum report'), sub)
    p(f"Role: {report['role']} | Market: {market.get('focus', 'International')}")
    p(f"Report generated (UTC): {report['generated_at']}\nMarket collected (UTC): {market.get('collected_at', 'Unknown')}", small)
    coverage = summary['mention_alignment_percent']
    table(['Measure','Result'], [
        ['Usable job postings', summary['analyzed_jobs']],
        ['Demand-weighted syllabus mention coverage', 'Insufficient evidence' if coverage is None else f'{coverage}%'],
        ['Skills mentioned in the curriculum',summary['detected_curriculum_skills']],
        ['Skills detected in job postings',summary['demanded_skills']],
        ['Possible missing skill mentions',summary['missing_skills']],
        ['PDF pages analyzed',curriculum['page_count']]], [310,181])
    p('Coverage measures syllabus mentions, not student competence. Missing mentions require faculty confirmation. Retain foundational theory and original course outcomes.')
    h('How the analysis works')
    p(report['methodology'])
    h('Data quality and search coverage')
    p(f"Search scope: {market.get('location_query', 'Across countries')}. Fetched before filtering: {market.get('fetched_count', 0)}. Cached: {market.get('cached', False)}.")
    p('Searched markets: ' + ', '.join(market.get('searched_markets', [])))
    table(['Source / market','Status','Fetched'], [[s['source'],s['status'],s['fetched']] for s in market.get('sources',[])], [250,170,71])
    lines([f"Excluded - {key.replace('_', ' ')}: {value}" for key,value in market.get('excluded',{}).items()])
    h('Warnings')
    lines(report['warnings'] or ['No additional warnings.'])
    h('Curriculum evidence')
    p('Foundations to preserve: ' + (', '.join(curriculum['concepts']) or 'No catalog foundation detected.'))
    for skill in curriculum['skills']:
        p(f"{skill['skill']} / PDF p.{skill['page']}", sub)
        p(skill['excerpt'])
    h('Original course outcomes')
    for co in curriculum['course_outcomes']:
        p(f"{co['id']} / p.{co['page']}: {co['statement']}")
    if not curriculum['course_outcomes']: p('No explicit CO-numbered outcome lines detected.')
    h('Legacy tooling mentions to review')
    for item in curriculum['legacy_mentions']:
        p(f"{item['tool']} / p.{item['page']}", sub)
        p(item['excerpt']); p(item['rationale'])
    if not curriculum['legacy_mentions']: p('No catalog legacy-version mentions detected.')
    h('Skill demand in this sample')
    table(['Skill','Jobs','Share','PDF evidence'], [[d['skill'],f"{d['job_count']} / {summary['analyzed_jobs']}",f"{d['share_percent']}%",d['curriculum_status']] for d in report['skill_demand']], [160,80,65,186])
    gap_start = len(story)
    h('Prioritized gaps and supporting evidence')
    for index, gap in enumerate(report['gaps']):
        block_start = gap_start if index == 0 else len(story)
        p(f"{gap['skill']} / {gap['priority']} / {gap['category']}", sub)
        p(f"Mentioned in {gap['job_count']} postings ({gap['share_percent']}% of sample). {gap['interpretation']}")
        anchor = gap['syllabus_anchor']
        p(f"Related syllabus foundation (p.{anchor['page']}): {anchor['excerpt']}" if anchor else 'No related foundation detected; assess prerequisites first.')
        outcome(gap['course_outcome'])
        for witness in gap['evidence']:
            p(f"Job {witness['job_id']}: {witness['excerpt']}", small)
            link(witness['url'])
        story[block_start:] = [KeepTogether(story[block_start:])]
    if not report['gaps']: p('No market-backed missing skills identified.')
    lab_start = len(story)
    h('Optional lab extensions')
    p('Faculty review and prepared starter environments are required. Keep the original theory and outcomes. These are task outlines, not executable grading harnesses.')
    for index, lab in enumerate(report['lab_patches']):
        block_start = lab_start if index == 0 else len(story)
        p(lab['title'], sub)
        p(f"Duration: {lab['duration_minutes']} minutes | Related syllabus topic: p.{lab['page']} | Foundation: {lab['foundation']}")
        outcome(lab['course_outcome'])
        p('Prerequisites: ' + lab['prerequisites'])
        lines(lab['tasks'])
        p('Suggested rubric', sub)
        lines([f'{k}: {v}%' for k,v in lab['rubric'].items()])
        p('Verification checklist', sub)
        lines(lab['verification_checklist'])
        p(lab['faculty_notes'], small)
        story[block_start:] = [KeepTogether(story[block_start:])]
    if not report['lab_patches']: p('No automatically anchored lab outline available for this sample.')
    job_start = len(story)
    h('Job evidence directory')
    for index, job in enumerate(report.get('jobs',[])):
        block_start = job_start if index == 0 else len(story)
        p(f"{job['title']} / {job['company']}", sub)
        p(f"ID: {job['id']} | Source: {job['site']} | Location: {job['location']}\nPosted: {job['date_posted'] or 'Unknown'} | Search market: {job.get('search_market', 'Unknown')}\nSeniority: {job.get('seniority', 'Unknown')}", small)
        p('Detected skills: ' + ', '.join(job['skills']), small)
        link(job['url'])
        story[block_start:] = [KeepTogether(story[block_start:])]
    if not report.get('jobs'): p('No usable live postings were returned. No demand score or market-backed recommendations can be produced.')
    h('Limitations')
    lines(report['limitations'])
    p('PDF export uses an embedded font. Characters outside its supported set are shown as question marks.', small)
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#dfe6da')); canvas.line(52,46,A4[0]-52,46)
        canvas.setFont('BridgeSans',8); canvas.setFillColor(MUTED)
        canvas.drawString(52,32,'BridgeLabs / Curriculum analysis')
        canvas.drawRightString(A4[0]-52,32,f'Page {doc.page}')
        canvas.restoreState()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=52, leftMargin=52, topMargin=48, bottomMargin=62,
                            title='BridgeLabs - Curriculum and job market analysis', author='BridgeLabs')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()


def generate_summary_pdf(report):
    """A bounded two-page executive summary; full evidence stays in the full report."""
    from reportlab.platypus import PageBreak
    output = BytesIO()
    body = ParagraphStyle('SummaryBody', fontName='BridgeSans', fontSize=9, leading=13, spaceAfter=7, textColor=GREEN)
    heading = ParagraphStyle('SummaryHeading', parent=body, fontName='BridgeSans-Bold', fontSize=14, leading=19, spaceBefore=12, spaceAfter=9, keepWithNext=True)
    title = ParagraphStyle('SummaryTitle', parent=heading, fontSize=24, leading=30)
    small = ParagraphStyle('SummarySmall', parent=body, fontSize=8, leading=11, textColor=MUTED)
    story = []
    def clip(value, limit=150):
        text = re.sub(r'\s+', ' ', str(value or '')).strip()
        return text if len(text) <= limit else text[:limit-3].rsplit(' ',1)[0]+'...'
    def p(value, style=body): story.append(Paragraph(safe_text(value), style))
    def h(value): p(value, heading)
    def table(headers, rows, widths):
        data = [[Paragraph(safe_text(c),small) for c in row] for row in [headers]+rows]
        grid = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
        grid.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf2e6')),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
            ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
            ('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#e1e6dc'))]))
        story.extend([grid,Spacer(1,8)])
    stats, market, curriculum = report['summary'], report['market'], report['curriculum']
    p('BRIDGELABS / DECISION BRIEF', small)
    p('Executive Summary', title)
    p(clip(report.get('filename', 'Curriculum analysis'),100))
    p(f"Role: {clip(report['role'],60)} | International job sample", small)
    p(f"Generated (UTC): {clip(report['generated_at'],40)}", small)
    coverage = stats['mention_alignment_percent']
    table(['Measure','Finding'], [
        ['Usable job postings',stats['analyzed_jobs']],
        ['Syllabus mention coverage','Insufficient evidence' if coverage is None else f'{coverage}%'],
        ['Possible skill gaps',stats['missing_skills']],
        ['Skills found in curriculum',stats['detected_curriculum_skills']]], [310,181])
    p('Coverage reflects skill mentions in this job sample, not student competence. Missing mentions do not prove a skill is not taught.',small)
    h('Priority skills to review')
    if report['gaps']:
        table(['Skill','Jobs','Share','Priority'], [[clip(g['skill'],40),str(g['job_count']),f"{g['share_percent']}%",g['priority']] for g in report['gaps'][:5]], [220,65,70,136])
        p(f"Showing {min(5,len(report['gaps']))} of {len(report['gaps'])} possible gaps. See the full report for evidence and all remaining skills.",small)
    else: p('No market-backed missing skills identified. If the sample is empty, collect more job evidence first.')
    h('Foundations to preserve')
    p(clip(', '.join(curriculum['concepts']) or 'No catalog foundation detected; faculty review needed.',200))
    h('Evidence at a glance')
    sources = market.get('sources',[])
    returned = sum(s['fetched'] > 0 for s in sources)
    p(f"{market.get('fetched_count',stats['analyzed_jobs'])} postings fetched before filtering. {returned} of {len(sources)} searches returned data. Source availability and country coverage vary.",small)
    if stats['analyzed_jobs'] < 15:
        p('Small sample: fewer than 15 usable postings. Treat percentages cautiously.',small)
    p('This is a bounded international sample, not a census of global hiring. Skill matching uses a fixed alias catalog; faculty should confirm the findings.',small)
    story.append(PageBreak())
    p('Recommended Next Steps', title)
    p('Choose one small extension for an existing lab. Preserve the original learning objective and confirm prerequisites before assigning it.')
    labs = report['lab_patches'][:3]
    for index, lab in enumerate(labs,1):
        h(f"{index}. {clip(lab['title'],90)}")
        co = lab.get('course_outcome')
        p(f"{lab['duration_minutes']} minutes | Syllabus p.{lab['page']}" + (f" | {clip(co['id'],15)} (review required)" if co else ' | Faculty review required'),small)
        p(clip(lab['tasks'][1] if len(lab['tasks']) > 1 else lab['tasks'][0],180))
        p('Prepare: '+clip(lab['prerequisites'],130),small)
    if not labs:
        p('No lab extension could be safely anchored to a syllabus foundation. Review the full report with faculty to select an appropriate topic and prerequisites.')
    h('Faculty checklist')
    p('Confirm each proposed gap against what is actually taught. Keep foundational theory and original course outcomes. Prepare the starter environment and use a repeatable check for each extension.')
    p('Suggested assessment: original concept correctness 40%, working extension and checks 40%, explanation and reproducibility 20%.',small)
    if curriculum['legacy_mentions']:
        h('Tooling to review')
        p(clip(', '.join(item['tool'] for item in curriculum['legacy_mentions'][:4]),160),small)
        p('Confirm whether these mentions prescribe lab tooling or describe historical context.',small)
    h('Read alongside the full report')
    p('The full report includes original curriculum excerpts, course outcomes, complete skill-demand tables, all gap mappings, detailed lab rubrics, job links, source failures, and methodology. This two-page brief intentionally omits that detail.',small)
    def footer(canvas,doc):
        canvas.saveState();canvas.setFillColor(MUTED);canvas.setFont('BridgeSans',8)
        canvas.drawString(52,32,'BridgeLabs / Executive Summary')
        canvas.drawRightString(A4[0]-52,32,f'{doc.page} / 2');canvas.restoreState()
    SimpleDocTemplate(output,pagesize=A4,leftMargin=52,rightMargin=52,topMargin=44,bottomMargin=55,
        title='BridgeLabs - Executive Summary',author='BridgeLabs').build(story,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()
