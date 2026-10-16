const $ = id => document.getElementById(id);
let selectedFile = null;
let busy = false;
const input = $('file-input'), drop = $('drop-zone'), analyze = $('analyze-button');
function selectFile(file) {
  if (busy) return;
  $('error').textContent = '';
  if (!file) return;
  if (!/\.pdf$/i.test(file.name) || (file.type && file.type !== 'application/pdf')) { $('error').textContent = 'Please choose a PDF file.'; input.value = ''; return; }
  if (file.size > 10 * 1024 * 1024) { $('error').textContent = 'This file is too large. Please choose a PDF under 10 MB.'; input.value = ''; return; }
  if (!file.size) { $('error').textContent = 'This file is empty. Please choose another PDF.'; input.value = ''; return; }
  selectedFile = file;
  $('analysis-status').textContent = '';
  $('file-name').textContent = file.name;
  $('file-size').textContent = `${(file.size / 1024).toFixed(1)} KB · Ready for analysis`;
  $('file-selected').hidden = false;
  $('drop-title').textContent = 'Want to use a different curriculum?';
  $('drop-subtitle').innerHTML = 'Drop another PDF or <u>browse files</u>';
  analyze.disabled = false;
  $('file-count').textContent = '1';
  $('results').hidden = true;
}
drop.addEventListener('click', () => input.click());
drop.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); } });
input.addEventListener('change', () => selectFile(input.files[0]));
['dragenter', 'dragover'].forEach(event => drop.addEventListener(event, e => { e.preventDefault(); drop.classList.add('dragging'); }));
['dragleave', 'drop'].forEach(event => drop.addEventListener(event, e => { e.preventDefault(); drop.classList.remove('dragging'); }));
drop.addEventListener('drop', e => { if (e.dataTransfer.files.length !== 1) { $('error').textContent = 'Please select one PDF at a time.'; return; } selectFile(e.dataTransfer.files[0]); });
$('remove-file').addEventListener('click', () => {
 $('analysis-status').textContent = ''; selectedFile = null; input.value = ''; $('file-selected').hidden = true; analyze.disabled = true; $('file-count').textContent = '0'; $('results').hidden = true; $('error').textContent = ''; $('drop-title').textContent = 'Drop your curriculum here'; $('drop-subtitle').innerHTML = 'or <u>browse files</u> to get started';
});
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
const bullets = items => `<ul>${items.map(x => `<li>${esc(x)}</li>`).join('')}</ul>`;
const jobLink = (url, text) => {
 try { const u = new URL(url); if (!['https:', 'http:'].includes(u.protocol)) return esc(text); }
 catch { return esc(text); }
 return `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(text)} ↗</a>`;
};
function renderReport(r, apiBase) {
 const stats = r.summary;
 const section = $('results');
 section.innerHTML = `<span class="tag">INTERNATIONAL · LIVE JOB SAMPLE${r.market.cached ? ' · CACHED' : ''}</span>
 <h2>Your curriculum, compared with hiring demand.</h2><p>${esc(r.filename)} · ${esc(r.role)} · ${esc(r.market.location_query)}<br>
 Collected ${esc(new Date(r.market.collected_at).toLocaleString())} · ${r.curriculum.page_count} PDF pages</p>
 <div class="report-downloads" aria-label="Download analysis reports">
 <button id="download-report" class="primary-button">Download full report (PDF) <span>↓</span></button>
 <button id="download-summary" class="primary-button secondary-button">Download Executive Summary (PDF) <span>↓</span></button>
 </div><p class="download-note">Full report: all evidence and lab details. Executive Summary: a two-page overview of findings and next steps.</p>
 <p class="download-note">Downloads are available for 30 minutes, until the server restarts, or until newer reports replace them.</p>
 <div class="result-grid"><article class="result-card"><h3>${stats.analyzed_jobs} usable jobs</h3><p>${r.market.fetched_count} fetched before relevance, seniority, date and duplicate filtering.</p></article>
 <article class="result-card"><h3>${stats.mention_alignment_percent === null ? 'Insufficient evidence' : stats.mention_alignment_percent + '% mention coverage'}</h3><p>Demand-weighted syllabus mentions. This is not a student readiness score.</p></article>
 <article class="result-card"><h3>${stats.missing_skills} possible gaps</h3><p>${stats.detected_curriculum_skills} catalog skills mentioned in the PDF. Missing mentions need faculty confirmation.</p></article></div>
 ${!stats.analyzed_jobs ? '<p class="report-warning">No usable live postings were returned. No demand score or market-backed recommendations can be produced. Retry later to collect a fresh sample.</p>' : ''}
 <h3>Data quality and source coverage</h3>${bullets(r.market.sources.map(s => `${s.source}: ${s.status} (${s.fetched} postings)`))}
 <p>Excluded: ${esc(Object.entries(r.market.excluded).map(([k,v]) => `${k.replaceAll('_',' ')}: ${v}`).join(' · '))}</p>
 ${bullets(r.warnings)}
 <h3>Foundations to preserve</h3><p>${esc(r.curriculum.concepts.join(', ') || 'No catalog foundation matched. Faculty review is needed.')}</p>
 <details><summary>Curriculum evidence and original course outcomes</summary>${r.curriculum.skills.map(s => `<p><strong>${esc(s.skill)}</strong> · p.${s.page}<br>${esc(s.excerpt)}</p>`).join('')}
 ${r.curriculum.course_outcomes.map(co => `<p>${esc(co.id)} · p.${co.page}: ${esc(co.statement)}</p>`).join('') || '<p>No explicit CO-numbered outcome lines detected.</p>'}</details>
 ${r.curriculum.legacy_mentions.length ? `<h3>Legacy tooling mentions to review</h3>${r.curriculum.legacy_mentions.map(x => `<p><strong>${esc(x.tool)}</strong> · p.${x.page}: ${esc(x.excerpt)}<br>${esc(x.rationale)}</p>`).join('')}` : ''}
 <h3>Skill demand in this sample</h3><div class="table-scroll"><table><thead><tr><th>Skill</th><th>Jobs mentioning skill</th><th>Share</th><th>PDF evidence</th></tr></thead><tbody>
 ${r.skill_demand.map(d => `<tr><td>${esc(d.skill)}</td><td>${d.job_count} / ${stats.analyzed_jobs}</td><td>${d.share_percent}%</td><td>${esc(d.curriculum_status)}</td></tr>`).join('')}</tbody></table></div>
 <h3>Prioritized gaps</h3>${r.gaps.map(g => `<details><summary>${esc(g.skill)} · ${esc(g.priority)} · ${esc(g.category)} · ${g.share_percent}% of sample</summary>
 <p>${esc(g.interpretation)}</p><p>${g.syllabus_anchor ? `Related foundation on p.${g.syllabus_anchor.page}: ${esc(g.syllabus_anchor.excerpt)}` : 'No related foundation found. Assess prerequisites before adding this topic.'}</p>
 ${g.course_outcome ? `<p>Possible outcome link (review required): ${esc(g.course_outcome.id)} — ${esc(g.course_outcome.statement)}</p>` : '<p>No explicit outcome mapping found.</p>'}
 ${g.evidence.map(e => `<blockquote>${esc(e.excerpt)}<br>${jobLink(e.url, 'View supporting posting')}</blockquote>`).join('')}</details>`).join('') || '<p>No market-backed missing skills identified.</p>'}
 <h3>Optional weekly lab extensions</h3><p>Keep the original theory and outcomes. These task outlines require faculty review and prepared starter environments.</p>
 <div class="result-grid">${r.lab_patches.map(l => `<article class="result-card"><span>40 MINUTES · FACULTY REVIEW</span><h3>${esc(l.title)}</h3><p>Related syllabus topic: p.${l.page}${l.course_outcome ? ' · '+esc(l.course_outcome.id) : ''}</p><p>${esc(l.prerequisites)}</p>${bullets(l.tasks)}<h4>Suggested rubric</h4>${bullets(Object.entries(l.rubric).map(([k,v]) => `${k}: ${v}%`))}<h4>Verification checklist</h4>${bullets(l.verification_checklist)}<p>${esc(l.faculty_notes)}</p></article>`).join('')}</div>
 <details><summary>Job evidence (${r.jobs.length})</summary>${r.jobs.map(j => `<p>${jobLink(j.url,j.title)} · ${esc(j.company)} · ${esc(j.site)}<br>${esc(j.location)} · Posted: ${esc(j.date_posted || 'unknown')}</p>`).join('')}</details>
 <details><summary>How this report is calculated and its limits</summary><p>${esc(r.methodology)}</p>${bullets(r.limitations)}</details>
 `;
 for (const [id, version, filename] of [
   ['download-report', 'full', 'bridgelabs-analysis.pdf'],
   ['download-summary', 'summary', 'bridgelabs-executive-summary.pdf']
 ]) {
   $(id).onclick = () => {
     const a = document.createElement('a');
     a.href = `${apiBase}/api/reports/${encodeURIComponent(r.report_id)}.pdf?version=${version}`;
     a.download = filename; a.click();
   };
 }
 section.hidden = false; section.scrollIntoView({behavior:'smooth', block:'start'});
}
// Probe before uploading so a static preview never receives the curriculum PDF.
async function resolveAnalysisServer(signal) {
 const loopback = ['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname);
 const candidates = window.location.protocol === 'file:' ? [] : [window.location.origin];
 if (loopback && window.location.origin !== 'http://127.0.0.1:8000') candidates.push('http://127.0.0.1:8000');
 for (const base of candidates) {
   try {
     const response = await fetch(`${base}/api/health`, {signal, cache:'no-store'});
     if (!response.ok || !(response.headers.get('content-type') || '').includes('application/json')) continue;
     const health = await response.json();
     if (health.status === 'ok' && health.service === 'bridgelabs') return base;
   } catch (error) { if (signal.aborted) throw error; }
 }
 throw new Error('Cannot reach BridgeLabs analysis. From the BridgeLabs folder, run: .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000, then retry. You can also open http://127.0.0.1:8000.');
}
analyze.addEventListener('click', async () => {
 if (!selectedFile || busy) return;
 busy = true; analyze.disabled = true;
 $('remove-file').disabled = true; input.disabled = true; drop.setAttribute('aria-disabled', 'true');
 $('error').textContent = ''; $('results').hidden = true;
 $('analysis-status').textContent = 'Reading your PDF and collecting international job postings… This can take up to 90 seconds.';
 const body = new FormData(); body.append('file', selectedFile); body.append('role', $('target-role').value);
 const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 120000);
 try {
   const base = await resolveAnalysisServer(controller.signal);
   const response = await fetch(`${base}/api/analyze`, {method:'POST', body, signal:controller.signal});
   const type = response.headers.get('content-type') || '';
   if (!type.includes('application/json')) throw new Error(`The analysis server returned an unexpected response (HTTP ${response.status}). Check the backend terminal and retry.`);
   const data = await response.json();
   if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Please check the PDF and selected search options.');
   renderReport(data, base); $('analysis-status').textContent = 'Analysis complete. Review the evidence and data-quality notes below.';
 } catch (error) {
   $('error').textContent = error.name === 'AbortError' ? 'Analysis timed out. Retry shortly; a completed market search may now be cached.' : (error.message === 'Failed to fetch' ? 'Cannot reach the analysis server. Start the Python server and retry.' : error.message);
   $('analysis-status').textContent = '';
 } finally {
   clearTimeout(timeout); busy = false; analyze.disabled = !selectedFile; $('remove-file').disabled = false; input.disabled = false; drop.removeAttribute('aria-disabled');
 }
});
const dialog = $('info-dialog');
$('help-button').onclick = $('profile-button').onclick = () => dialog.showModal();
$('close-dialog').onclick = $('dialog-done').onclick = () => dialog.close();
dialog.addEventListener('click', e => { if (e.target === dialog) { const r = dialog.getBoundingClientRect(); if(e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) dialog.close(); } });
document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => {
 const view = button.dataset.view;
 if (view === 'roadmap' || view === 'github') { dialog.showModal(); return; }
 document.querySelectorAll('[data-view]').forEach(b => b.classList.toggle('active', b === button));
 const section = $('curricula-view');
 if (view === 'home') { section.hidden = true; window.scrollTo({top:0,behavior:'smooth'}); return; }
 section.innerHTML = '<span class="tag">MY CURRICULA</span><h2>Your learning starts here.</h2><p id="curricula-description"></p>';
 $('curricula-description').textContent = selectedFile ? `${selectedFile.name} is selected in this session. Use the upload panel to analyze it or replace your file.` : 'No curriculum selected yet. Add your first PDF in the upload panel above.';
 section.hidden = false; section.scrollIntoView({behavior:'smooth'});
}));
