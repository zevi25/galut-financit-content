const STUDIO_API = '/api/video';
let _currentJobId = null;
let _pollInterval = null;
let _currentScenes = [];

// ── Tab switching ─────────────────────────────────────────────
function switchTab(tab) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.main').forEach(m => m.classList.add('hidden'));
  document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
  document.getElementById(`tab-${tab}`).classList.remove('hidden');
  // Hide WhatsApp generate button when in video studio
  const btnGenerate = document.getElementById('btn-generate');
  if (btnGenerate) btnGenerate.style.display = tab === 'whatsapp' ? '' : 'none';
}

// ── Prompts only ──────────────────────────────────────────────
async function generatePromptsOnly() {
  const script = document.getElementById('video-script').value.trim();
  if (!script) { alert('נא להדביק מלל לסרטון'); return; }
  const numScenes = parseInt(document.getElementById('num-scenes').value);

  setStudioStatus('loading', 'מייצר פרומפטים...');
  document.getElementById('prompts-panel').classList.add('hidden');
  document.getElementById('gallery-panel').classList.add('hidden');
  document.getElementById('studio-error').classList.add('hidden');

  try {
    const res = await fetch(`${STUDIO_API}/generate-prompts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ script, num_scenes: numScenes }),
    });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || 'שגיאה');
    _currentScenes = data.scenes;
    renderPromptsPanel(data.scenes);
    setStudioStatus('idle');
  } catch (e) {
    showStudioError(e.message);
    setStudioStatus('idle');
  }
}

function renderPromptsPanel(scenes) {
  const list = document.getElementById('prompts-list');
  list.innerHTML = '';
  scenes.forEach(s => {
    const card = document.createElement('div');
    card.className = 'prompt-card';
    card.innerHTML = `
      <div class="prompt-card-header" onclick="togglePrompt(this)">
        <span class="prompt-scene-num">פריים ${s.scene_number}</span>
        <span class="prompt-hebrew">${escHtml(s.hebrew_text)}</span>
        <span class="prompt-toggle">▼</span>
      </div>
      <div class="prompt-card-body">
        <div class="prompt-english">${escHtml(s.english_prompt)}</div>
        <button class="btn btn-ghost btn-sm prompt-copy-btn"
          onclick="copyText(this, ${JSON.stringify(s.english_prompt)})">📋 העתק</button>
      </div>`;
    list.appendChild(card);
  });
  document.getElementById('prompts-panel').classList.remove('hidden');
}

function togglePrompt(header) {
  const body = header.nextElementSibling;
  const open = body.classList.toggle('open');
  header.querySelector('.prompt-toggle').textContent = open ? '▲' : '▼';
}

function copyText(btn, text) {
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.textContent;
    btn.textContent = '✅ הועתק';
    setTimeout(() => { btn.textContent = orig; }, 1500);
  });
}

function copyAllPrompts() {
  const text = _currentScenes.map(s =>
    `[פריים ${s.scene_number}]\n${s.english_prompt}`
  ).join('\n\n');
  navigator.clipboard.writeText(text);
}

// ── Full image generation ─────────────────────────────────────
async function startVideoGeneration() {
  const script = document.getElementById('video-script').value.trim();
  if (!script) { alert('נא להדביק מלל לסרטון'); return; }
  const numScenes = parseInt(document.getElementById('num-scenes').value);

  document.getElementById('prompts-panel').classList.add('hidden');
  document.getElementById('gallery-panel').classList.add('hidden');
  document.getElementById('studio-error').classList.add('hidden');
  document.getElementById('gallery-grid').innerHTML = '';
  Object.keys(_renderedItems).forEach(k => delete _renderedItems[k]);

  showProgress('מייצר פרומפטים...', 0, numScenes);

  try {
    const res = await fetch(`${STUDIO_API}/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ script, num_scenes: numScenes }),
    });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || 'שגיאה');
    _currentJobId = data.job_id;
    startPolling(numScenes);
  } catch (e) {
    showStudioError(e.message);
    hideProgress();
  }
}

function startPolling(total) {
  if (_pollInterval) clearInterval(_pollInterval);
  _pollInterval = setInterval(() => pollJob(total), 2500);
}

async function pollJob(total) {
  if (!_currentJobId) return;
  try {
    const res = await fetch(`${STUDIO_API}/status/${_currentJobId}`);
    const data = await res.json();

    if (data.status === 'generating_prompts') {
      updateProgress('מייצר פרומפטים...', 0, total);
    } else if (data.status === 'generating_images') {
      updateProgress(`מייצר תמונות... ${data.completed}/${data.total}`, data.completed, data.total);
      renderGallery(data.scenes);
    } else if (data.status === 'done') {
      clearInterval(_pollInterval);
      updateProgress(`הושלם! ${data.total} תמונות`, data.total, data.total);
      renderGallery(data.scenes);
      document.getElementById('btn-download-zip').dataset.jobId = _currentJobId;
      setTimeout(hideProgress, 2000);
    } else if (data.status === 'error') {
      clearInterval(_pollInterval);
      hideProgress();
      showStudioError(data.error || 'שגיאה לא ידועה');
    }
  } catch {}
}

const _renderedItems = {};

function renderGallery(scenes) {
  const grid = document.getElementById('gallery-grid');

  scenes.forEach(s => {
    const key = s.scene_number;
    let item = _renderedItems[key];

    if (!item) {
      item = document.createElement('div');
      item.className = 'gallery-item';
      item.id = `gi-${key}`;
      item.innerHTML = `
        <div class="gallery-placeholder">
          <div class="spinner" style="border-color:rgba(0,0,0,0.12);border-top-color:#2563eb;width:24px;height:24px;border-width:3px"></div>
          <p>פריים ${key}</p>
        </div>
        <span class="gallery-item-num">${key}</span>`;
      grid.appendChild(item);
      _renderedItems[key] = item;
    }

    if (s.done && s.image_b64 && !item.dataset.loaded) {
      item.dataset.loaded = '1';
      item.innerHTML = `
        <img src="data:image/jpeg;base64,${s.image_b64}" alt="פריים ${key}" loading="lazy" />
        <span class="gallery-item-num">${key}</span>
        <button class="gallery-item-download" onclick="downloadSingle(this)"
          data-b64="${s.image_b64}" data-num="${key}">⬇</button>`;
    }
  });

  document.getElementById('gallery-panel').classList.remove('hidden');
}

function downloadSingle(btn) {
  const link = document.createElement('a');
  link.href = `data:image/jpeg;base64,${btn.dataset.b64}`;
  link.download = `frame_${String(btn.dataset.num).padStart(2, '0')}.jpg`;
  link.click();
}

async function downloadZip() {
  const jobId = _currentJobId;
  if (!jobId) return;
  window.location.href = `${STUDIO_API}/download/${jobId}`;
}

// ── Helpers ───────────────────────────────────────────────────
function setStudioStatus(state, msg) {
  const badge = document.getElementById('status-badge');
  if (state === 'loading') {
    badge.className = 'badge badge-loading';
    badge.textContent = msg || 'טוען...';
  } else {
    badge.className = 'badge badge-idle';
    badge.textContent = 'מוכן';
  }
}

function showProgress(label, done, total) {
  document.getElementById('studio-progress').classList.remove('hidden');
  updateProgress(label, done, total);
}

function updateProgress(label, done, total) {
  document.getElementById('progress-label').textContent = label;
  document.getElementById('progress-count').textContent = total ? `${done}/${total}` : '';
  const pct = total ? Math.round((done / total) * 100) : 0;
  document.getElementById('progress-bar-fill').style.width = `${pct}%`;
}

function hideProgress() {
  document.getElementById('studio-progress').classList.add('hidden');
}

function showStudioError(msg) {
  const el = document.getElementById('studio-error');
  el.textContent = `❌ שגיאה: ${msg}`;
  el.classList.remove('hidden');
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
