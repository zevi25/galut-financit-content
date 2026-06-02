const API = '/api';
const SECTIONS = [
  { key: 'market_summary',  label: '📊 סיכום שוק יומי' },
  { key: 'investment_tip',  label: '💡 טיפ השקעות' },
  { key: 'news_analysis',   label: '📰 חדשות עם פרשנות' },
];

let currentDate = todayStr();
let currentContent = null;

function todayStr() {
  return new Date().toISOString().split('T')[0];
}

function hebrewDate(dateStr) {
  const d = new Date(dateStr + 'T12:00:00');
  return d.toLocaleDateString('he-IL', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
}

// ── Date navigation ──────────────────────────────────────────
function changeDate(delta) {
  const d = new Date(currentDate + 'T12:00:00');
  d.setDate(d.getDate() + delta);
  currentDate = d.toISOString().split('T')[0];
  loadContent();
}

// ── Load content ─────────────────────────────────────────────
async function loadContent() {
  document.getElementById('date-display').textContent = hebrewDate(currentDate);
  document.getElementById('content-area').innerHTML =
    '<div class="empty-state"><p>⏳ טוען...</p></div>';
  document.getElementById('final-panel').classList.add('hidden');

  try {
    const res = await fetch(`${API}/content/${currentDate}`);
    if (!res.ok) {
      currentContent = null;
      renderEmpty();
      return;
    }
    currentContent = await res.json();
    renderCards(currentContent);
    loadHistory();
  } catch {
    renderEmpty('שגיאת חיבור לשרת');
  }
}

function renderEmpty(msg) {
  document.getElementById('content-area').innerHTML =
    `<div class="empty-state"><p>📭 ${msg || 'אין תוכן לתאריך זה'}</p><p style="margin-top:8px;font-size:0.85rem;color:#9ca3af">לחץ "צור תוכן עכשיו" כדי להתחיל</p></div>`;
}

// ── Render cards ─────────────────────────────────────────────
function renderCards(content) {
  const area = document.getElementById('content-area');
  area.innerHTML = '';

  SECTIONS.forEach(({ key, label }) => {
    const text = content[key] || '';
    const status = content[`${key}_status`] || 'draft';
    const approved = status === 'approved';

    const card = document.createElement('div');
    card.className = `card${approved ? ' approved' : ''}`;
    card.id = `card-${key}`;
    card.innerHTML = `
      <div class="card-header">
        <span class="card-title">${label} ${approved ? '✅' : ''}</span>
        <div class="card-actions">
          <button class="btn btn-regen" onclick="regenerateSection('${key}')" ${approved ? 'disabled' : ''}>🔄 צור מחדש</button>
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

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ── Edit ─────────────────────────────────────────────────────
function toggleEdit(key) {
  const wrap = document.getElementById(`editor-wrap-${key}`);
  const display = document.getElementById(`display-${key}`);
  if (wrap.classList.contains('hidden')) {
    wrap.classList.remove('hidden');
    display.classList.add('hidden');
  } else {
    cancelEdit(key);
  }
}

function cancelEdit(key) {
  document.getElementById(`editor-wrap-${key}`).classList.add('hidden');
  document.getElementById(`display-${key}`).classList.remove('hidden');
}

async function saveEdit(key) {
  const text = document.getElementById(`editor-${key}`).value;
  await fetch(`${API}/content/${currentDate}/section/${key}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  currentContent[key] = text;
  document.getElementById(`display-${key}`).textContent = text;
  cancelEdit(key);
}

// ── Approve ───────────────────────────────────────────────────
async function approveSection(key) {
  await fetch(`${API}/content/${currentDate}/approve/${key}`, { method: 'POST' });
  currentContent[`${key}_status`] = 'approved';
  const card = document.getElementById(`card-${key}`);
  card.classList.add('approved');
  const btn = document.getElementById(`approve-btn-${key}`);
  btn.textContent = '✅ אושר';
  btn.classList.add('approved');
  btn.onclick = null;

  const regenBtn = card.querySelector('.btn-regen');
  if (regenBtn) regenBtn.disabled = true;

  const title = card.querySelector('.card-title');
  if (!title.textContent.includes('✅')) title.textContent += ' ✅';

  checkAllApproved();
}

function checkAllApproved() {
  if (!currentContent) return;
  const allApproved = SECTIONS.every(
    ({ key }) => currentContent[`${key}_status`] === 'approved'
  );
  if (allApproved) showFinalPanel();
}

function showFinalPanel() {
  const parts = SECTIONS.map(({ key, label }) =>
    `${label}\n${'─'.repeat(30)}\n${currentContent[key]}`
  );
  document.getElementById('final-text').textContent = parts.join('\n\n');
  document.getElementById('final-panel').classList.remove('hidden');
  document.getElementById('final-panel').scrollIntoView({ behavior: 'smooth' });
}

// ── Copy all ──────────────────────────────────────────────────
function copyAll() {
  const text = document.getElementById('final-text').textContent;
  navigator.clipboard.writeText(text).then(() => {
    const confirm = document.getElementById('copy-confirm');
    confirm.classList.remove('hidden');
    setTimeout(() => confirm.classList.add('hidden'), 2500);
  });
}

// ── Generate ──────────────────────────────────────────────────
async function generateContent() {
  const btn = document.getElementById('btn-generate');
  const badge = document.getElementById('status-badge');
  btn.disabled = true;
  btn.innerHTML = '✨ מייצר תוכן... <span class="spinner"></span>';
  badge.className = 'badge badge-loading';
  badge.textContent = 'מייצר...';

  try {
    const res = await fetch(`${API}/generate`, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      currentDate = todayStr();
      currentContent = data.content;
      document.getElementById('date-display').textContent = hebrewDate(currentDate);
      renderCards(currentContent);
      badge.className = 'badge badge-success';
      badge.textContent = 'נוצר בהצלחה ✅';
      loadHistory();
    } else {
      badge.className = 'badge badge-error';
      badge.textContent = 'שגיאה ❌';
      alert('שגיאה: ' + (data.error || 'לא ידוע'));
    }
  } catch {
    badge.className = 'badge badge-error';
    badge.textContent = 'שגיאת חיבור';
  } finally {
    btn.disabled = false;
    btn.textContent = '✨ צור תוכן עכשיו';
    setTimeout(() => {
      badge.className = 'badge badge-idle';
      badge.textContent = 'מוכן';
    }, 4000);
  }
}

// ── Regenerate section ────────────────────────────────────────
async function regenerateSection(key) {
  const display = document.getElementById(`display-${key}`);
  display.textContent = '⏳ מייצר מחדש...';
  try {
    const res = await fetch(`${API}/generate`, { method: 'POST' });
    const data = await res.json();
    if (data.ok && data.content) {
      currentContent = data.content;
      display.textContent = data.content[key];
      const editor = document.getElementById(`editor-${key}`);
      if (editor) editor.value = data.content[key];
    }
  } catch {
    display.textContent = currentContent[key];
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
      const allApproved = SECTIONS.every(
        ({ key }) => item[`${key}_status`] === 'approved'
      );
      const anyApproved = SECTIONS.some(
        ({ key }) => item[`${key}_status`] === 'approved'
      );
      const div = document.createElement('div');
      div.className = `history-item${allApproved ? ' all-approved' : anyApproved ? ' partial' : ''}`;
      div.textContent = item.date;
      div.onclick = () => { currentDate = item.date; loadContent(); };
      list.appendChild(div);
    });
  } catch {}
}

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('date-display').textContent = hebrewDate(currentDate);
  loadContent();
});
