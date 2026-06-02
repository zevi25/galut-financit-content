const API = '/api';

const WA_SECTIONS = [
  { key: 'market_summary',      label: '📊 סיכום שוק יומי' },
  { key: 'investment_tip',      label: '💡 טיפ השקעות' },
  { key: 'news_analysis',       label: '📰 חדשות עם פרשנות' },
  { key: 'stock_of_week',       label: '📈 מניה השבוע' },
  { key: 'investor_psychology', label: '🧠 פסיכולוגיה של משקיע' },
  { key: 'weekly_events',       label: '🗓️ אירועי שבוע' },
];

let currentDate = todayStr();
let currentContent = null;
let currentTab = 'whatsapp';

function todayStr() {
  // Always use Israel timezone (UTC+2/+3) so date flips at Israeli midnight
  return new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Jerusalem' });
}
function hebrewDate(dateStr) {
  const d = new Date(dateStr + 'T12:00:00');
  return d.toLocaleDateString('he-IL', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
}

// ── Tab switching ─────────────────────────────────────────────
function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('main.main').forEach(m => m.classList.add('hidden'));
  document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
  document.getElementById(`tab-${tab}`).classList.remove('hidden');
  const btnGenerate = document.getElementById('btn-generate');
  if (btnGenerate) btnGenerate.style.display = (tab === 'video') ? 'none' : '';
  refreshCurrentTab();
}

function refreshCurrentTab() {
  if (currentTab === 'whatsapp') renderWhatsapp();
  if (currentTab === 'facebook') window.renderFacebook && renderFacebook();
  if (currentTab === 'instagram') window.renderInstagram && renderInstagram();
}

// ── Date navigation ───────────────────────────────────────────
function changeDate(delta) {
  const d = new Date(currentDate + 'T12:00:00');
  d.setDate(d.getDate() + delta);
  currentDate = d.toISOString().split('T')[0];
  loadContent();
}

// ── Load content ──────────────────────────────────────────────
async function loadContent() {
  // Update all date displays
  ['date-display', 'fb-date-display', 'ig-date-display'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = hebrewDate(currentDate);
  });

  try {
    const res = await fetch(`${API}/content/${currentDate}`);
    if (!res.ok) { currentContent = null; }
    else { currentContent = await res.json(); }
  } catch { currentContent = null; }

  refreshCurrentTab();
  loadHistory();
  updateGenerateButton();
}

function updateGenerateButton() {
  const btn = document.getElementById('btn-generate');
  if (!btn) return;
  const isToday = currentDate === todayStr();
  if (isToday && currentContent) {
    btn.textContent = '🔄 עדכן סיכום שוק';
    btn.title = 'תוכן קיים להיום — ילחץ יעדכן רק את סיכום השוק';
  } else {
    btn.textContent = '✨ צור תוכן עכשיו';
    btn.title = '';
  }
}

// ══════════════════════════════════════════════════════════════
// WHATSAPP
// ══════════════════════════════════════════════════════════════
function renderWhatsapp() {
  const area = document.getElementById('content-area');
  document.getElementById('final-panel').classList.add('hidden');
  if (!currentContent) { area.innerHTML = '<div class="empty-state"><p>📭 אין תוכן לתאריך זה</p><p style="margin-top:8px;font-size:.85rem;color:#9ca3af">לחץ "צור תוכן עכשיו" כדי להתחיל</p></div>'; return; }

  area.innerHTML = '';
  WA_SECTIONS.forEach(({ key, label }) => {
    const text = currentContent[key] || '';
    const approved = currentContent[`${key}_status`] === 'approved';
    const card = document.createElement('div');
    card.className = `card${approved ? ' approved' : ''}`;
    card.id = `card-${key}`;
    card.innerHTML = `
      <div class="card-header">
        <span class="card-title">${label}${approved ? ' ✅' : ''}</span>
        <div class="card-actions">
          <button class="btn btn-ghost btn-sm copy-btn" onclick="copySection('${key}')" title="העתק טקסט">📋</button>
          <button class="btn btn-regen" onclick="regenSection('${key}')" ${approved ? 'disabled' : ''}>🔄 חדש</button>
          <button class="btn btn-ghost" onclick="toggleEdit('${key}')">✏️ ערוך</button>
          <button class="btn btn-approve${approved ? ' approved' : ''}" id="approve-btn-${key}"
            onclick="${approved ? '' : `approveSection('${key}')`}">${approved ? '✅ אושר' : '✅ אשר'}</button>
        </div>
      </div>
      <div class="card-body">
        <div class="content-display" id="display-${key}">${escHtml(text)}</div>
        <div id="editor-wrap-${key}" class="hidden">
          <textarea class="content-editor" id="editor-${key}">${escHtml(text)}</textarea>
          <div class="edit-actions">
            <button class="btn btn-primary" onclick="saveEdit('${key}')">💾 שמור</button>
            <button class="btn btn-ghost" onclick="cancelEdit('${key}')">ביטול</button>
          </div>
        </div>
      </div>`;
    area.appendChild(card);
  });
  checkAllApproved();
}

function copySection(key) {
  const text = currentContent?.[key] || '';
  navigator.clipboard.writeText(text).then(() => {
    if (window.showToast) showToast('✅ הועתק!');
  });
}

function toggleEdit(key) {
  const wrap = document.getElementById(`editor-wrap-${key}`);
  const display = document.getElementById(`display-${key}`);
  if (wrap.classList.contains('hidden')) { wrap.classList.remove('hidden'); display.classList.add('hidden'); }
  else cancelEdit(key);
}
function cancelEdit(key) {
  document.getElementById(`editor-wrap-${key}`).classList.add('hidden');
  document.getElementById(`display-${key}`).classList.remove('hidden');
}
async function saveEdit(key) {
  const text = document.getElementById(`editor-${key}`).value;
  await fetch(`${API}/content/${currentDate}/section/${key}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }),
  });
  currentContent[key] = text;
  document.getElementById(`display-${key}`).textContent = text;
  cancelEdit(key);
}

async function approveSection(key) {
  await fetch(`${API}/content/${currentDate}/approve/${key}`, { method: 'POST' });
  currentContent[`${key}_status`] = 'approved';
  const card = document.getElementById(`card-${key}`);
  card.classList.add('approved');
  const btn = document.getElementById(`approve-btn-${key}`);
  btn.textContent = '✅ אושר'; btn.classList.add('approved'); btn.onclick = null;
  const regenBtn = card.querySelector('.btn-regen');
  if (regenBtn) regenBtn.disabled = true;
  const title = card.querySelector('.card-title');
  if (!title.textContent.includes('✅')) title.textContent += ' ✅';
  checkAllApproved();
  // Also notify social.js if needed
  if (window.onSectionApproved) window.onSectionApproved(key);
}

function checkAllApproved() {
  if (!currentContent) return;
  const allApproved = WA_SECTIONS.every(({ key }) => currentContent[`${key}_status`] === 'approved');
  if (allApproved) showFinalPanel();
}

function showFinalPanel() {
  const parts = WA_SECTIONS.map(({ key, label }) => `${label}\n${'─'.repeat(30)}\n${currentContent[key]}`);
  document.getElementById('final-text').textContent = parts.join('\n\n');
  document.getElementById('final-panel').classList.remove('hidden');
  document.getElementById('final-panel').scrollIntoView({ behavior: 'smooth' });
}

function copyAll() {
  const text = document.getElementById('final-text').textContent;
  navigator.clipboard.writeText(text).then(() => {
    const c = document.getElementById('copy-confirm');
    c.classList.remove('hidden');
    setTimeout(() => c.classList.add('hidden'), 2500);
  });
}

async function regenSection(key) {
  const display = document.getElementById(`display-${key}`);
  const origText = currentContent?.[key] || '';
  display.textContent = '⏳ מייצר מחדש...';
  try {
    const res = await fetch(`${API}/generate/section/${key}`, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      currentContent[key] = data.text;
      display.textContent = data.text;
      const editor = document.getElementById(`editor-${key}`);
      if (editor) editor.value = data.text;
      if (window.showToast) showToast('✅ נוצר מחדש!');
    } else {
      display.textContent = origText;
      alert('שגיאה: ' + (data.error || 'לא ידוע'));
    }
  } catch {
    display.textContent = origText;
  }
}

// ── Generate ──────────────────────────────────────────────────
async function generateContent() {
  const btn = document.getElementById('btn-generate');
  const badge = document.getElementById('status-badge');
  const isRefresh = currentContent && currentDate === todayStr();
  btn.disabled = true;
  btn.innerHTML = `${isRefresh ? '🔄' : '✨'} ${isRefresh ? 'מעדכן שוק...' : 'מייצר...'} <span class="spinner"></span>`;
  badge.className = 'badge badge-loading'; badge.textContent = isRefresh ? 'מעדכן...' : 'מייצר...';

  try {
    const res = await fetch(`${API}/generate`, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      currentDate = todayStr();
      currentContent = data.content;
      ['date-display','fb-date-display','ig-date-display'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = hebrewDate(currentDate);
      });
      refreshCurrentTab();
      const successMsg = data.mode === 'market_refresh' ? 'שוק עודכן ✅' : 'נוצר ✅';
      badge.className = 'badge badge-success'; badge.textContent = successMsg;
      loadHistory();
    } else {
      badge.className = 'badge badge-error'; badge.textContent = 'שגיאה ❌';
      alert('שגיאה: ' + (data.error || 'לא ידוע'));
    }
  } catch {
    badge.className = 'badge badge-error'; badge.textContent = 'שגיאת חיבור';
  } finally {
    btn.disabled = false;
    updateGenerateButton();
    setTimeout(() => { badge.className = 'badge badge-idle'; badge.textContent = 'מוכן'; }, 4000);
  }
}

// ── History ───────────────────────────────────────────────────
async function loadHistory() {
  try {
    const res = await fetch(`${API}/history`);
    const items = await res.json();
    const list = document.getElementById('history-list');
    list.innerHTML = '';
    items.forEach(item => {
      const statuses = Object.values(item).filter(v => v === 'approved' || v === 'draft');
      const approved = statuses.filter(v => v === 'approved').length;
      const total = statuses.length;
      const allApproved = approved === total && total > 0;
      const anyApproved = approved > 0;
      const div = document.createElement('div');
      div.className = `history-item${allApproved ? ' all-approved' : anyApproved ? ' partial' : ''}`;
      div.textContent = item.date;
      div.onclick = () => { currentDate = item.date; loadContent(); };
      list.appendChild(div);
    });
  } catch {}
}

function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  ['date-display','fb-date-display','ig-date-display'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = hebrewDate(currentDate);
  });
  loadContent();
});
