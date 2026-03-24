/**
 * JihanBot v2 — minimal UI: run → HITL planning → result
 */

const API = '/api';
let currentThreadId = null;
let eventSource = null;
let defaultBand = '7';

const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const runBtn = document.getElementById('runBtn');
const thinkingLog = document.getElementById('thinkingLog');
const thinkingBadge = document.getElementById('thinkingBadge');
const thinkingSection = document.getElementById('thinkingSection');
const essaySection = document.getElementById('essaySection');
const essayContent = document.getElementById('essayContent');
const planningModal = document.getElementById('planningModal');
const planningForm = document.getElementById('planningForm');
const planMode = document.getElementById('planMode');
const planBand = document.getElementById('planBand');
const planOutline = document.getElementById('planOutline');
const planEssay = document.getElementById('planEssay');
const outlineGroup = document.getElementById('outlineGroup');
const essayGroup = document.getElementById('essayGroup');

let selectedFile = null;

function openModal(overlay) {
  overlay.classList.add('visible');
  overlay.setAttribute('aria-hidden', 'false');
}

function closeModal(overlay) {
  overlay.classList.remove('visible');
  overlay.setAttribute('aria-hidden', 'true');
}

uploadZone.addEventListener('click', () => fileInput.click());
uploadZone.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    fileInput.click();
  }
});
fileInput.addEventListener('change', () => {
  const f = fileInput.files?.[0];
  selectedFile = f || null;
  uploadZone.querySelector('.upload-content p').textContent = f ? f.name : 'Optional: chart / task image';
});

planMode.addEventListener('change', () => {
  const g = planMode.value === 'generate';
  outlineGroup.style.display = g ? 'block' : 'none';
  essayGroup.style.display = g ? 'none' : 'block';
});

function appendThinking(text) {
  if (!text || typeof text !== 'string') return;
  const line = document.createElement('div');
  line.className = 'line';
  line.textContent = text;
  thinkingLog.appendChild(line);
  thinkingLog.scrollTop = thinkingLog.scrollHeight;
}

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

function renderResult(state) {
  const go = state.grading_output;
  if (!go) {
    essayContent.innerHTML = '<p class="placeholder">No grading output.</p>';
    return;
  }
  const band = go.overall_task_band ?? '';
  const refined = go.refined_essay || '';
  const parts = [
    `<p><strong>Overall task band:</strong> ${escapeHtml(String(band))}</p>`,
    `<p><strong>Task (TA/TR):</strong> ${escapeHtml(go.task_criterion_feedback || '')}</p>`,
    `<p><strong>CC:</strong> ${escapeHtml(go.coherence_cohesion_feedback || '')}</p>`,
    `<p><strong>LR:</strong> ${escapeHtml(go.lexical_resource_feedback || '')}</p>`,
    `<p><strong>GRA:</strong> ${escapeHtml(go.grammatical_range_feedback || '')}</p>`,
  ];
  if (go.revision_summary) {
    parts.push(`<p><strong>Revision summary:</strong> ${escapeHtml(go.revision_summary)}</p>`);
  }
  if (refined) {
    parts.push(`<h3 class="result-sub">Refined essay</h3>`);
    parts.push(refined.split('\n\n').map((p) => `<p class="paragraph">${escapeHtml(p)}</p>`).join(''));
  }
  essayContent.innerHTML = parts.join('');
}

runBtn.addEventListener('click', async () => {
  const promptText = document.getElementById('promptText').value.trim();
  const taskType = document.getElementById('taskType').value;
  defaultBand = document.getElementById('bandScore').value;

  if (!selectedFile && !promptText) {
    appendThinking('Error: provide prompt text and/or an image.');
    return;
  }

  runBtn.disabled = true;
  thinkingLog.innerHTML = '';
  thinkingBadge.textContent = 'starting...';
  thinkingBadge.className = 'badge active';
  thinkingSection.classList.add('thinking');
  essayContent.innerHTML = '<p class="placeholder">Running…</p>';

  const formData = new FormData();
  formData.append('task_type', taskType);
  formData.append('band_score', defaultBand);
  formData.append('prompt_text', promptText);
  if (selectedFile) formData.append('image', selectedFile);

  try {
    const res = await fetch(`${API}/run`, { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to start');
    currentThreadId = data.thread_id;
    connectSSE();
  } catch (err) {
    appendThinking(`Error: ${err.message}`);
    thinkingBadge.textContent = 'error';
    thinkingBadge.className = 'badge error';
    runBtn.disabled = false;
  }
});

function connectSSE() {
  if (eventSource) eventSource.close();
  eventSource = new EventSource(`${API}/stream/${currentThreadId}`);

  eventSource.addEventListener('thinking', (e) => {
    const data = JSON.parse(e.data || '{}');
    if (data.text) appendThinking(data.text);
    thinkingBadge.textContent = 'running';
    thinkingBadge.className = 'badge active';
  });

  eventSource.addEventListener('interrupt', (e) => {
    const data = JSON.parse(e.data || '{}');
    eventSource.close();
    eventSource = null;
    thinkingBadge.textContent = 'paused';
    thinkingSection.classList.remove('thinking');
    if (data.node === 'hitl_planning') {
      planBand.value = defaultBand;
      planMode.value = 'generate';
      planOutline.value = '';
      planEssay.value = '';
      outlineGroup.style.display = 'block';
      essayGroup.style.display = 'none';
      openModal(planningModal);
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
    renderResult(data.state || {});
  });

  eventSource.onerror = () => {
    if (eventSource?.readyState === EventSource.CLOSED) return;
    appendThinking('Connection error.');
    thinkingBadge.textContent = 'error';
    thinkingBadge.className = 'badge error';
    runBtn.disabled = false;
  };
}

planningForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const formData = new FormData();
  formData.append('thread_id', currentThreadId);
  formData.append('user_mode', planMode.value);
  formData.append('target_band', planBand.value);
  formData.append('user_outline', planOutline.value);
  formData.append('user_essay', planEssay.value);
  try {
    const res = await fetch(`${API}/hitl/planning`, { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed');
    closeModal(planningModal);
    thinkingBadge.textContent = 'running';
    thinkingBadge.className = 'badge active';
    thinkingSection.classList.add('thinking');
    connectSSE();
  } catch (err) {
    appendThinking(`Error: ${err.message}`);
  }
});
