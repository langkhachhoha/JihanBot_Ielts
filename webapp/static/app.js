/**
 * JihanBot Web Demo - Frontend
 */

const API = '/api';
let selectedFile = null;
let currentThreadId = null;
let eventSource = null;
let interruptState = null;

// DOM elements
const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const runBtn = document.getElementById('runBtn');
const thinkingSection = document.getElementById('thinkingSection');
const thinkingBadge = document.getElementById('thinkingBadge');
const thinkingLog = document.getElementById('thinkingLog');
const essaySection = document.getElementById('essaySection');
const essayContent = document.getElementById('essayContent');
const extractionsSection = document.getElementById('extractionsSection');
const extractionsList = document.getElementById('extractionsList');
const saveExtractionsBtn = document.getElementById('saveExtractionsBtn');
const galleryGrid = document.getElementById('galleryGrid');
const galleryFilters = document.getElementById('galleryFilters');
const gallerySection = document.getElementById('gallerySection');
const openGalleryBtn = document.getElementById('openGalleryBtn');
const closeGalleryBtn = document.getElementById('closeGalleryBtn');
const proposedButtonRow = document.getElementById('proposedButtonRow');
const openProposedBtn = document.getElementById('openProposedBtn');
const closeProposedBtn = document.getElementById('closeProposedBtn');
const editExtractionModal = document.getElementById('editExtractionModal');
const editExtractionForm = document.getElementById('editExtractionForm');

// Modals
const featuresModal = document.getElementById('featuresModal');
const gradingModal = document.getElementById('gradingModal');
const featuresForm = document.getElementById('featuresForm');
const gradingForm = document.getElementById('gradingForm');
const gfEditFields = document.getElementById('gfEditFields');
const gfSkipBtn = document.getElementById('gfSkipBtn');
const gfEditToggle = document.getElementById('gfEditToggle');

// Upload
uploadZone.addEventListener('click', () => fileInput.click());
uploadZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  uploadZone.classList.add('dragover');
});
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
uploadZone.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadZone.classList.remove('dragover');
  const file = e.dataTransfer?.files?.[0];
  if (file?.type.startsWith('image/')) {
    setFile(file);
  }
});
fileInput.addEventListener('change', () => {
  const file = fileInput.files?.[0];
  if (file) setFile(file);
});

function setFile(file) {
  selectedFile = file;
  uploadZone.querySelector('.upload-content p').textContent = file.name;
  runBtn.disabled = false;
}

// Run pipeline
runBtn.addEventListener('click', async () => {
  if (!selectedFile) return;
  runBtn.disabled = true;
  thinkingLog.innerHTML = '';
  thinkingCurrentLine = null;
  thinkingBadge.textContent = 'starting...';
  thinkingBadge.className = 'badge active';
  thinkingSection.classList.add('thinking');
  essayContent.innerHTML = '<p class="placeholder">Generating...</p>';
  extractionsList.innerHTML = '';
  proposedItems.length = 0;
  proposedButtonRow.style.display = 'none';
  extractionsSection.classList.add('extractions-collapsed');

  const formData = new FormData();
  formData.append('image', selectedFile);
  formData.append('band_score', document.getElementById('bandScore').value);

  try {
    const res = await fetch(`${API}/run`, {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to start');
    currentThreadId = data.thread_id;
    connectSSE();
  } catch (err) {
    appendThinking(`Error: ${err.message}`);
    thinkingBadge.textContent = 'error';
    runBtn.disabled = false;
  }
});

// Buffer: status messages = new line; token stream = append to current line
let thinkingCurrentLine = null;
function isStatusLine(t) {
  return /^[📖📊✏️🔍📋📚✅❌⚠️👤⏸️▶️🔄]/.test(t) || (t.length > 30 && t.includes(' '));
}

function appendThinking(text) {
  if (!text || typeof text !== 'string') return;
  const hasNewline = text.includes('\n');
  const isStatus = isStatusLine(text);
  if (hasNewline || isStatus) {
    const parts = text.split('\n');
    parts.forEach((part) => {
      if (part || isStatus) {
        const line = document.createElement('div');
        line.className = 'line';
        line.textContent = part;
        thinkingLog.appendChild(line);
        thinkingCurrentLine = null;
      }
    });
  } else {
    if (!thinkingCurrentLine) {
      thinkingCurrentLine = document.createElement('div');
      thinkingCurrentLine.className = 'line thinking-inline';
      thinkingLog.appendChild(thinkingCurrentLine);
    }
    thinkingCurrentLine.textContent = (thinkingCurrentLine.textContent || '') + text;
  }
  thinkingLog.scrollTop = thinkingLog.scrollHeight;
}

function connectSSE() {
  if (eventSource) eventSource.close();
  eventSource = new EventSource(`${API}/stream/${currentThreadId}`);

  eventSource.addEventListener('thinking', (e) => {
    const data = JSON.parse(e.data || '{}');
    if (data.text) appendThinking(data.text);
    thinkingBadge.textContent = 'thinking...';
    thinkingBadge.className = 'badge active';
  });

  eventSource.addEventListener('interrupt', (e) => {
    const data = JSON.parse(e.data || '{}');
    interruptState = data.state || {};
    eventSource.close();
    eventSource = null;
    thinkingBadge.textContent = 'paused';
    thinkingSection.classList.remove('thinking');

    if (data.node === 'hitl_review_features') {
      showFeaturesModal(interruptState);
    } else if (data.node === 'hitl_review_grading') {
      showGradingModal(interruptState);
    } else if (data.node === 'hitl_review_extractions') {
      showExtractionsPanel(interruptState);
    }
  });

  eventSource.addEventListener('done', (e) => {
    const data = JSON.parse(e.data || '{}');
    eventSource.close();
    eventSource = null;
    thinkingBadge.textContent = 'done';
    thinkingBadge.className = 'badge done';
    thinkingSection.classList.remove('thinking');
    runBtn.disabled = false;

    const state = data.state || {};
    const essay = state.essay || '';
    if (essay) {
      essayContent.innerHTML = essay.split('\n\n').map(p => 
        `<p class="paragraph">${escapeHtml(p)}</p>`
      ).join('');
    } else {
      essayContent.innerHTML = '<p class="placeholder">No essay generated.</p>';
    }

    const proposed = state.proposed_language_items || [];
    if (proposed.length > 0 && proposedItems.length === 0) {
      showExtractionsPanel({ ...state, proposed_language_items: proposed });
    }
  });

  eventSource.onerror = () => {
    if (eventSource?.readyState === EventSource.CLOSED) return;
    appendThinking('Connection interrupted. You may need to resubmit.');
    thinkingBadge.textContent = 'error';
  };
}

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

// Features modal
function showFeaturesModal(state) {
  const ef = state.extracted_features || {};
  document.getElementById('feOverview').value = ef.overview || '';
  document.getElementById('feParagraph1').value = ef.paragraph_1 || '';
  document.getElementById('feParagraph2').value = ef.paragraph_2 || '';
  document.getElementById('feGrouping').value = ef.grouping_logic || '';
  featuresModal.classList.add('visible');
}

featuresForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const formData = new FormData();
  formData.append('thread_id', currentThreadId);
  formData.append('overview', document.getElementById('feOverview').value);
  formData.append('paragraph_1', document.getElementById('feParagraph1').value);
  formData.append('paragraph_2', document.getElementById('feParagraph2').value);
  formData.append('grouping_logic', document.getElementById('feGrouping').value);

  try {
    const res = await fetch(`${API}/hitl/features`, {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed');
    featuresModal.classList.remove('visible');
    thinkingBadge.textContent = 'thinking...';
    thinkingBadge.className = 'badge active';
    thinkingSection.classList.add('thinking');
    connectSSE();
  } catch (err) {
    appendThinking(`Error: ${err.message}`);
  }
});

// Grading modal
function showGradingModal(state) {
  const essay = state.essay || '';
  const gf = state.grading_feedback || {};
  document.getElementById('gradingEssay').textContent = essay;
  document.getElementById('gradingFeedback').innerHTML = formatGradingFeedback(gf);
  document.getElementById('gfTA').value = gf.task_achievement_feedback || '';
  document.getElementById('gfCC').value = gf.coherence_cohesion_feedback || '';
  document.getElementById('gfLR').value = gf.lexical_resource_feedback || '';
  document.getElementById('gfGR').value = gf.grammatical_range_feedback || '';
  document.getElementById('gfSuggestion').value = gf.suggestion || '';
  document.getElementById('gfScore').value = gf.overall_score ?? '';
  document.getElementById('gfPassed').value = gf.passed ? 'true' : 'false';
  document.getElementById('gfAction').value = 'accept';
  gfEditFields.style.display = 'none';
  gradingModal.classList.add('visible');
}

function formatGradingFeedback(gf) {
  const status = gf.passed ? '<span class="status passed">PASSED</span>' : '<span class="status failed">NEEDS REVISION</span>';
  let html = `<div class="status">${status}</div>`;
  if (gf.overall_score != null) html += `<p><strong>Score:</strong> ${gf.overall_score}</p>`;
  if (gf.task_achievement_feedback) html += `<p><strong>Task Achievement:</strong> ${escapeHtml(gf.task_achievement_feedback)}</p>`;
  if (gf.coherence_cohesion_feedback) html += `<p><strong>Coherence & Cohesion:</strong> ${escapeHtml(gf.coherence_cohesion_feedback)}</p>`;
  if (gf.lexical_resource_feedback) html += `<p><strong>Lexical Resource:</strong> ${escapeHtml(gf.lexical_resource_feedback)}</p>`;
  if (gf.grammatical_range_feedback) html += `<p><strong>Grammatical Range:</strong> ${escapeHtml(gf.grammatical_range_feedback)}</p>`;
  if (gf.suggestion) html += `<p><strong>Suggestions:</strong> ${escapeHtml(gf.suggestion)}</p>`;
  return html || '<p>No feedback details.</p>';
}

gfSkipBtn.addEventListener('click', async () => {
  const formData = new FormData();
  formData.append('thread_id', currentThreadId);
  formData.append('action', 'skip_revision');
  try {
    const res = await fetch(`${API}/hitl/grading`, { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed');
    gradingModal.classList.remove('visible');
    thinkingBadge.textContent = 'thinking...';
    thinkingBadge.className = 'badge active';
    thinkingSection.classList.add('thinking');
    connectSSE();
  } catch (err) {
    appendThinking(`Error: ${err.message}`);
  }
});

gfEditToggle.addEventListener('click', () => {
  gfEditFields.style.display = gfEditFields.style.display === 'none' ? 'block' : 'none';
});

gradingForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const formData = new FormData();
  formData.append('thread_id', currentThreadId);
  formData.append('action', document.getElementById('gfAction').value);
  formData.append('passed', document.getElementById('gfPassed').value);
  formData.append('task_achievement_feedback', document.getElementById('gfTA').value);
  formData.append('coherence_cohesion_feedback', document.getElementById('gfCC').value);
  formData.append('lexical_resource_feedback', document.getElementById('gfLR').value);
  formData.append('grammatical_range_feedback', document.getElementById('gfGR').value);
  formData.append('suggestion', document.getElementById('gfSuggestion').value);
  formData.append('overall_score', document.getElementById('gfScore').value);

  try {
    const res = await fetch(`${API}/hitl/grading`, { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed');
    gradingModal.classList.remove('visible');
    thinkingBadge.textContent = 'thinking...';
    thinkingBadge.className = 'badge active';
    thinkingSection.classList.add('thinking');
    connectSSE();
  } catch (err) {
    appendThinking(`Error: ${err.message}`);
  }
});

// Extractions
const proposedItems = [];

function showExtractionsPanel(state) {
  const items = state.proposed_language_items || [];
  proposedItems.length = 0;
  items.forEach((item) => {
    proposedItems.push({ ...item, approved: false, rejected: false });
  });
  renderExtractions();
  proposedButtonRow.style.display = '';
  extractionsSection.classList.remove('extractions-collapsed');
}

function renderExtractions() {
  extractionsList.innerHTML = '';
  proposedItems.forEach((item, i) => {
    if (item.rejected) return;
    const el = document.createElement('div');
    el.className = `extraction-item ${item.approved ? 'approved' : ''}`;
    el.dataset.index = i;
    el.innerHTML = `
      <span class="meta">${escapeHtml(item.category || '')} / ${escapeHtml(item.subcategory || '')}</span>
      <span class="structure">${escapeHtml(item.structure || '')}</span>
      <span class="example">${escapeHtml(item.example || '')}</span>
      <div class="extraction-actions">
        <button type="button" class="btn btn-sm ${item.approved ? 'btn-secondary' : 'btn-primary'}" data-action="approve" data-i="${i}">${item.approved ? 'Undo' : 'Approve'}</button>
        <button type="button" class="btn btn-sm btn-secondary" data-action="edit" data-i="${i}">Edit</button>
        <button type="button" class="btn btn-sm btn-secondary" data-action="reject" data-i="${i}">Reject</button>
      </div>
    `;
    el.querySelector('[data-action="approve"]').addEventListener('click', () => {
      proposedItems[i].approved = !proposedItems[i].approved;
      renderExtractions();
    });
    el.querySelector('[data-action="edit"]').addEventListener('click', () => openEditModal(i));
    el.querySelector('[data-action="reject"]').addEventListener('click', () => {
      proposedItems[i].rejected = true;
      renderExtractions();
    });
    extractionsList.appendChild(el);
  });
}

function openEditModal(idx) {
  const item = proposedItems[idx];
  if (!item) return;
  document.getElementById('editExtractionIdx').value = idx;
  document.getElementById('editCategory').value = item.category || '';
  document.getElementById('editSubcategory').value = item.subcategory || '';
  document.getElementById('editStructure').value = item.structure || '';
  document.getElementById('editExample').value = item.example || '';
  editExtractionModal.classList.add('visible');
}

editExtractionForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const idx = parseInt(document.getElementById('editExtractionIdx').value, 10);
  proposedItems[idx] = {
    ...proposedItems[idx],
    category: document.getElementById('editCategory').value.trim(),
    subcategory: document.getElementById('editSubcategory').value.trim(),
    structure: document.getElementById('editStructure').value.trim(),
    example: document.getElementById('editExample').value.trim(),
  };
  editExtractionModal.classList.remove('visible');
  renderExtractions();
});

document.getElementById('cancelEditExtraction').addEventListener('click', () => {
  editExtractionModal.classList.remove('visible');
});

saveExtractionsBtn.addEventListener('click', async () => {
  const approved = proposedItems.filter(i => !i.rejected && i.approved).map(({ category, subcategory, structure, example }) =>
    ({ category, subcategory, structure, example }));
  const formData = new FormData();
  formData.append('thread_id', currentThreadId);
  formData.append('body', JSON.stringify(approved));

  try {
    const res = await fetch(`${API}/hitl/extractions`, { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed');
    proposedButtonRow.style.display = 'none';
    extractionsSection.classList.add('extractions-collapsed');
    proposedItems.length = 0;
    thinkingBadge.textContent = 'thinking...';
    thinkingBadge.className = 'badge active';
    thinkingSection.classList.add('thinking');
    connectSSE();
    loadGallery();
  } catch (err) {
    appendThinking(`Error: ${err.message}`);
  }
});

// Gallery
let galleryCategoryFilter = '';

async function loadGallery() {
  try {
    const res = await fetch(`${API}/gallery`);
    const data = await res.json();
    renderGallery(data.items || [], data.taxonomy || {});
    renderGalleryFilters(data.items || [], data.taxonomy || {});
  } catch (err) {
    galleryGrid.innerHTML = '<p class="placeholder">Failed to load gallery.</p>';
  }
}

function renderGalleryFilters(items, taxonomy) {
  const categories = [...new Set(items.map(i => i.category).filter(Boolean))];
  galleryFilters.innerHTML = `
    <button type="button" class="filter-btn ${!galleryCategoryFilter ? 'active' : ''}" data-cat="">All</button>
    ${categories.map(c => 
      `<button type="button" class="filter-btn ${galleryCategoryFilter === c ? 'active' : ''}" data-cat="${escapeHtml(c)}">${escapeHtml(c)}</button>`
    ).join('')}
  `;
  galleryFilters.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      galleryCategoryFilter = btn.dataset.cat || '';
      renderGalleryFilters(items, taxonomy);
      renderGallery(items, taxonomy);
    });
  });
}

function renderGallery(items, taxonomy) {
  let filtered = items;
  if (galleryCategoryFilter) {
    filtered = items.filter(i => i.category === galleryCategoryFilter);
  }
  galleryGrid.innerHTML = filtered.map(item => `
    <div class="gallery-card">
      <span class="category">${escapeHtml(item.category || '')}</span>
      <span class="subcategory">${escapeHtml(item.subcategory || '')}</span>
      <span class="structure">${escapeHtml(item.structure || '')}</span>
      <span class="example">${escapeHtml(item.example || '')}</span>
    </div>
  `).join('') || '<p class="placeholder">No items yet. Approve language units from generated essays to build your gallery.</p>';
}

openGalleryBtn.addEventListener('click', () => {
  gallerySection.classList.remove('gallery-collapsed');
});

closeGalleryBtn.addEventListener('click', () => {
  gallerySection.classList.add('gallery-collapsed');
});

openProposedBtn.addEventListener('click', () => {
  extractionsSection.classList.remove('extractions-collapsed');
});

closeProposedBtn.addEventListener('click', () => {
  extractionsSection.classList.add('extractions-collapsed');
});

loadGallery();
