const $ = id => document.getElementById(id);
let selectedFile = null;
const input = $('file-input'), drop = $('drop-zone'), analyze = $('analyze-button');
function selectFile(file) {
  $('error').textContent = '';
  if (!file) return;
  if (!/\.pdf$/i.test(file.name) || (file.type && file.type !== 'application/pdf')) { $('error').textContent = 'Please choose a PDF file.'; input.value = ''; return; }
  if (file.size > 10 * 1024 * 1024) { $('error').textContent = 'This file is too large. Please choose a PDF under 10 MB.'; input.value = ''; return; }
  if (!file.size) { $('error').textContent = 'This file is empty. Please choose another PDF.'; input.value = ''; return; }
  selectedFile = file;
  $('file-name').textContent = file.name;
  $('file-size').textContent = `${(file.size / 1024).toFixed(1)} KB · Ready for preview`;
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
 selectedFile = null; input.value = ''; $('file-selected').hidden = true; analyze.disabled = true; $('file-count').textContent = '0'; $('results').hidden = true; $('error').textContent = ''; $('drop-title').textContent = 'Drop your curriculum here'; $('drop-subtitle').innerHTML = 'or <u>browse files</u> to get started';
});
analyze.addEventListener('click', () => {
 if (!selectedFile) return;
 const result = $('results');
 result.innerHTML = `<span class="tag">SAMPLE ANALYSIS · DEMONSTRATION ONLY</span><h2>A glimpse of your next steps.</h2><p id="analysis-filename"></p><p>This preview illustrates the planned experience. It does not read your PDF or compare live job postings. The suggestions below are examples, not findings from your curriculum.</p><div class="result-grid"><article class="result-card"><span>EXAMPLE SKILL GAP</span><h3>From code to collaboration</h3><p>Pair programming fundamentals with Git branches, pull requests, and code review.</p></article><article class="result-card"><span>EXAMPLE LAB UPDATE</span><h3>Give your project an API</h3><p>Add one REST endpoint to an existing assignment, with input validation and a short test.</p></article><article class="result-card"><span>EXAMPLE PORTFOLIO PROOF</span><h3>Make your work visible</h3><p>Publish a clear README, setup instructions, and a small working demo in your repository.</p></article></div>`;
 $('analysis-filename').textContent = `Selected curriculum: ${selectedFile.name}`;
 result.hidden = false; result.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
 $('curricula-description').textContent = selectedFile ? `${selectedFile.name} is selected in this session. Use the upload panel to preview the analysis flow or replace your file.` : 'No curriculum selected yet. Add your first PDF in the upload panel above.';
 section.hidden = false; section.scrollIntoView({behavior:'smooth'});
}));
