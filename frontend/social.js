// ══════════════════════════════════════════════════════════════
// FACEBOOK
// ══════════════════════════════════════════════════════════════

function renderFacebook() {
  const area = document.getElementById('fb-content-area');
  if (!currentContent || !currentContent.facebook_post) {
    area.innerHTML = '<div class="empty-state"><p>📭 אין תוכן לתאריך זה</p><p style="margin-top:8px;font-size:.85rem;color:#9ca3af">לחץ "צור תוכן עכשיו" כדי להתחיל</p></div>';
    return;
  }

  const text   = currentContent.facebook_post;
  const status = currentContent.facebook_post_status || 'draft';
  const approved = status === 'approved';

  area.innerHTML = `
    <div class="card fb-card${approved ? ' approved' : ''}" id="card-facebook_post">
      <div class="card-header">
        <span class="card-title">📘 פוסט פייסבוק${approved ? ' ✅' : ''}</span>
        <div class="card-actions">
          <button class="btn btn-ghost btn-sm" onclick="copyFbPost()" title="העתק פוסט">📋 העתק</button>
          <button class="btn btn-regen" onclick="regenFacebookPost()" title="צור פוסט חדש">🔄 חדש</button>
          <button class="btn btn-ghost" onclick="toggleFbEdit()">✏️ ערוך</button>
          <button class="btn btn-approve${approved ? ' approved' : ''}" id="approve-btn-facebook_post"
            onclick="${approved ? '' : "approveSocialSection('facebook_post')"}">${approved ? '✅ אושר' : '✅ אשר'}</button>
        </div>
      </div>
      <div class="card-body">
        <!-- Preview mock -->
        <div class="fb-preview" id="fb-preview">
          <div class="fb-mock-header">
            <div class="fb-avatar">ל</div>
            <div>
              <div class="fb-page-name">לצאת מהגלות הפיננסית</div>
              <div class="fb-meta">עכשיו · 🌐</div>
            </div>
          </div>
          <div class="fb-post-text" id="fb-post-text">${escHtml(text)}</div>
          <div class="fb-mock-footer">
            <span>👍 אהבתי</span><span>💬 תגובה</span><span>↗️ שיתוף</span>
          </div>
        </div>
        <!-- Editor (hidden) -->
        <div id="fb-editor-wrap" class="hidden">
          <textarea class="content-editor fb-editor" id="fb-editor">${escHtml(text)}</textarea>
          <div class="edit-actions">
            <button class="btn btn-primary" onclick="saveFbEdit()">💾 שמור</button>
            <button class="btn btn-ghost" onclick="toggleFbEdit()">ביטול</button>
          </div>
        </div>
      </div>
    </div>`;
}

function toggleFbEdit() {
  const wrap    = document.getElementById('fb-editor-wrap');
  const preview = document.getElementById('fb-preview');
  if (wrap.classList.contains('hidden')) {
    wrap.classList.remove('hidden');
    preview.classList.add('hidden');
  } else {
    wrap.classList.add('hidden');
    preview.classList.remove('hidden');
  }
}

async function saveFbEdit() {
  const text = document.getElementById('fb-editor').value;
  await fetch(`${API}/content/${currentDate}/section/facebook_post`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }),
  });
  currentContent.facebook_post = text;
  document.getElementById('fb-post-text').textContent = text;
  toggleFbEdit();
}

function copyFbPost() {
  const text = currentContent.facebook_post || '';
  navigator.clipboard.writeText(text).then(() => showToast('✅ הועתק לפייסבוק!'));
}


// ══════════════════════════════════════════════════════════════
// INSTAGRAM
// ══════════════════════════════════════════════════════════════

let _carouselIndex = 0;
let _carouselData  = null;

function renderInstagram() {
  const area = document.getElementById('ig-content-area');
  if (!currentContent || (!currentContent.instagram_carousel && !currentContent.instagram_story)) {
    area.innerHTML = '<div class="empty-state"><p>📭 אין תוכן לתאריך זה</p><p style="margin-top:8px;font-size:.85rem;color:#9ca3af">לחץ "צור תוכן עכשיו" כדי להתחיל</p></div>';
    return;
  }

  area.innerHTML = `
    <div class="ig-grid">
      <div class="ig-col" id="ig-carousel-col"></div>
      <div class="ig-col" id="ig-story-col"></div>
    </div>`;

  renderCarousel();
  renderStory();
}

// ── Carousel ──────────────────────────────────────────────────

function renderCarousel() {
  const col = document.getElementById('ig-carousel-col');
  const raw = currentContent.instagram_carousel;
  const approved = currentContent.instagram_carousel_status === 'approved';

  if (!raw) { col.innerHTML = ''; return; }

  try {
    _carouselData  = typeof raw === 'string' ? JSON.parse(raw) : raw;
    _carouselIndex = 0;
  } catch {
    col.innerHTML = '<div class="empty-state">❌ שגיאה בנתוני הקרוסלה</div>';
    return;
  }

  const slides = _carouselData.slides || [];
  const topic  = _carouselData.topic  || '';

  col.innerHTML = `
    <div class="card${approved ? ' approved' : ''}">
      <div class="card-header">
        <span class="card-title">🎠 קרוסלה אינסטגרם${approved ? ' ✅' : ''}</span>
        <div class="card-actions">
          <button class="btn btn-ghost btn-sm" onclick="copyCarouselText()" title="העתק את כל הטקסטים">📋 העתק</button>
          <button class="btn btn-ghost btn-sm" onclick="downloadCarouselText()" title="הורד כקובץ טקסט">💾 הורד</button>
          <button class="btn btn-regen" onclick="regenCarousel()" title="צור קרוסלה חדשה בנושא אחר">🔄 חדשה</button>
          <button class="btn btn-approve${approved ? ' approved' : ''}" id="approve-btn-instagram_carousel"
            onclick="${approved ? '' : "approveSocialSection('instagram_carousel')"}">${approved ? '✅ אושר' : '✅ אשר'}</button>
        </div>
      </div>
      <div class="card-body">
        <p class="carousel-topic">נושא: <strong>${escHtml(topic)}</strong> · ${slides.length} שקופיות</p>

        <!-- Phone mock with slide -->
        <div class="ig-phone-wrap">
          <div class="ig-phone">
            <div class="ig-phone-top">
              <div class="ig-dots">
                ${slides.map((_, i) => `<span class="ig-dot${i === 0 ? ' active' : ''}" id="dot-${i}"></span>`).join('')}
              </div>
            </div>
            <div class="ig-slide-area" id="ig-slide-area">
              ${renderSlideHtml(slides[0])}
            </div>
            <div class="ig-phone-nav">
              <button class="ig-nav-btn" onclick="prevSlide()">‹</button>
              <span id="slide-counter">1 / ${slides.length}</span>
              <button class="ig-nav-btn" onclick="nextSlide()">›</button>
            </div>
          </div>
        </div>

        <!-- Slides list -->
        <div class="slides-list">
          ${slides.map((s, i) => `
            <div class="slide-item${i === 0 ? ' active' : ''}" id="slide-item-${i}" onclick="goToSlide(${i})">
              <span class="slide-num">${s.num}</span>
              <span class="slide-preview">${escHtml(getSlidePreview(s))}</span>
            </div>`).join('')}
        </div>
      </div>
    </div>`;
}

function renderSlideHtml(slide) {
  if (!slide) return '';
  const type = slide.type;
  if (type === 'hook') return `
    <div class="ig-slide ig-slide-hook">
      <div class="ig-slide-badge">1</div>
      <h2 class="ig-hook-headline">${escHtml(slide.headline || '')}</h2>
      <p class="ig-hook-sub">${escHtml(slide.sub || '')}</p>
    </div>`;
  if (type === 'point') return `
    <div class="ig-slide ig-slide-point">
      <div class="ig-slide-badge">${slide.num}</div>
      <div class="ig-point-emoji">${slide.emoji || '💡'}</div>
      <h3 class="ig-point-title">${escHtml(slide.title || '')}</h3>
      <p class="ig-point-body">${escHtml(slide.body || '')}</p>
    </div>`;
  if (type === 'summary') return `
    <div class="ig-slide ig-slide-summary">
      <div class="ig-slide-badge">${slide.num}</div>
      <div class="ig-point-emoji">⭐</div>
      <h3 class="ig-point-title">${escHtml(slide.headline || '')}</h3>
      <p class="ig-point-body">${escHtml(slide.body || '')}</p>
    </div>`;
  if (type === 'cta') return `
    <div class="ig-slide ig-slide-cta">
      <div class="ig-slide-badge">${slide.num}</div>
      <h2 class="ig-cta-headline">${escHtml(slide.headline || '')}</h2>
      <p class="ig-cta-action">${escHtml(slide.action || '')}</p>
      <div class="ig-cta-logo">לצאת מהגלות הפיננסית</div>
    </div>`;
  return `<div class="ig-slide"><p>${escHtml(JSON.stringify(slide))}</p></div>`;
}

function getSlidePreview(s) {
  return s.headline || s.title || s.body || '';
}

function goToSlide(i) {
  if (!_carouselData) return;
  const slides = _carouselData.slides;
  _carouselIndex = Math.max(0, Math.min(i, slides.length - 1));
  document.getElementById('ig-slide-area').innerHTML = renderSlideHtml(slides[_carouselIndex]);
  document.getElementById('slide-counter').textContent = `${_carouselIndex + 1} / ${slides.length}`;
  document.querySelectorAll('.ig-dot').forEach((d, j) => d.classList.toggle('active', j === _carouselIndex));
  document.querySelectorAll('.slide-item').forEach((el, j) => el.classList.toggle('active', j === _carouselIndex));
}

function nextSlide() {
  if (!_carouselData) return;
  goToSlide((_carouselIndex + 1) % _carouselData.slides.length);
}
function prevSlide() {
  if (!_carouselData) return;
  goToSlide((_carouselIndex - 1 + _carouselData.slides.length) % _carouselData.slides.length);
}

function copyCarouselText() {
  if (!_carouselData) return;
  const lines = _carouselData.slides.map(s => {
    const parts = [`שקופית ${s.num}:`];
    if (s.headline) parts.push(s.headline);
    if (s.sub)      parts.push(s.sub);
    if (s.title)    parts.push(s.title);
    if (s.body)     parts.push(s.body);
    if (s.action)   parts.push(s.action);
    return parts.join('\n');
  });
  navigator.clipboard.writeText(lines.join('\n\n')).then(() => showToast('✅ הועתק!'));
}

// ── Story ─────────────────────────────────────────────────────

function renderStory() {
  const col  = document.getElementById('ig-story-col');
  const text = currentContent.instagram_story;
  const approved = currentContent.instagram_story_status === 'approved';

  if (!text) { col.innerHTML = ''; return; }

  col.innerHTML = `
    <div class="card${approved ? ' approved' : ''}">
      <div class="card-header">
        <span class="card-title">📖 סטורי אינסטגרם${approved ? ' ✅' : ''}</span>
        <div class="card-actions">
          <button class="btn btn-ghost btn-sm" onclick="copyStory()" title="העתק סטורי">📋 העתק</button>
          <button class="btn btn-regen" onclick="regenStory()" title="צור סטורי חדש">🔄 חדש</button>
          <button class="btn btn-ghost btn-sm" onclick="toggleStoryEdit()">✏️</button>
          <button class="btn btn-approve${approved ? ' approved' : ''}" id="approve-btn-instagram_story"
            onclick="${approved ? '' : "approveSocialSection('instagram_story')"}">${approved ? '✅ אושר' : '✅ אשר'}</button>
        </div>
      </div>
      <div class="card-body">
        <!-- Story phone mock -->
        <div class="ig-story-wrap">
          <div class="ig-story-phone">
            <div class="ig-story-bar"></div>
            <div class="ig-story-avatar">ל</div>
            <div class="ig-story-text" id="story-text">${escHtml(text)}</div>
            <div class="ig-story-bottom">לצאת מהגלות הפיננסית</div>
          </div>
        </div>
        <div id="story-editor-wrap" class="hidden" style="margin-top:12px">
          <textarea class="content-editor" id="story-editor" style="min-height:120px">${escHtml(text)}</textarea>
          <div class="edit-actions">
            <button class="btn btn-primary" onclick="saveStoryEdit()">💾 שמור</button>
            <button class="btn btn-ghost" onclick="toggleStoryEdit()">ביטול</button>
          </div>
        </div>
      </div>
    </div>`;
}

function toggleStoryEdit() {
  const wrap = document.getElementById('story-editor-wrap');
  wrap.classList.toggle('hidden');
}
async function saveStoryEdit() {
  const text = document.getElementById('story-editor').value;
  await fetch(`${API}/content/${currentDate}/section/instagram_story`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }),
  });
  currentContent.instagram_story = text;
  document.getElementById('story-text').textContent = text;
  toggleStoryEdit();
}
function copyStory() {
  navigator.clipboard.writeText(currentContent.instagram_story || '').then(() => showToast('✅ הועתק לסטורי!'));
}

// ── Shared approve ────────────────────────────────────────────
async function approveSocialSection(key) {
  await fetch(`${API}/content/${currentDate}/approve/${key}`, { method: 'POST' });
  currentContent[`${key}_status`] = 'approved';
  const btn = document.getElementById(`approve-btn-${key}`);
  if (btn) { btn.textContent = '✅ אושר'; btn.classList.add('approved'); btn.onclick = null; }
  const card = btn?.closest('.card');
  if (card) card.classList.add('approved');
  const title = card?.querySelector('.card-title');
  if (title && !title.textContent.includes('✅')) title.textContent += ' ✅';
}

// ── Toast ─────────────────────────────────────────────────────
function showToast(msg) {
  let t = document.getElementById('_toast');
  if (!t) {
    t = document.createElement('div');
    t.id = '_toast';
    t.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#1f2937;color:white;padding:10px 20px;border-radius:8px;font-weight:600;z-index:9999;transition:opacity .3s';
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.style.opacity = '1';
  clearTimeout(t._timer);
  t._timer = setTimeout(() => { t.style.opacity = '0'; }, 2000);
}

async function regenFacebookPost() {
  const area = document.getElementById('fb-content-area');
  area.innerHTML = '<div class="empty-state"><span class="spinner"></span> מייצר פוסט חדש...</div>';
  try {
    const res = await fetch(`/api/generate/section/facebook_post`, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      if (window.currentContent) currentContent.facebook_post = data.text;
      renderFacebook();
      showToast('✅ פוסט פייסבוק חדש נוצר!');
    } else {
      renderFacebook();
      alert('שגיאה: ' + (data.error || ''));
    }
  } catch { renderFacebook(); }
}

async function regenStory() {
  const col = document.getElementById('ig-story-col');
  if (col) col.innerHTML = '<div class="empty-state"><span class="spinner"></span> מייצר סטורי חדש...</div>';
  try {
    const res = await fetch(`/api/generate/section/instagram_story`, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      if (window.currentContent) currentContent.instagram_story = data.text;
      renderStory();
      showToast('✅ סטורי חדש נוצר!');
    } else {
      renderStory();
      alert('שגיאה: ' + (data.error || ''));
    }
  } catch { renderStory(); }
}

function downloadCarouselText() {
  if (!_carouselData) return;
  const lines = _carouselData.slides.map(s => {
    const parts = [`── שקופית ${s.num} ──`];
    if (s.headline) parts.push(s.headline);
    if (s.sub)      parts.push(s.sub);
    if (s.title)    parts.push(s.title);
    if (s.body)     parts.push(s.body);
    if (s.action)   parts.push(s.action);
    return parts.join('\n');
  });
  const text = `קרוסלה: ${_carouselData.topic || ''}\n${'═'.repeat(30)}\n\n` + lines.join('\n\n');
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `carousel_${new Date().toISOString().split('T')[0]}.txt`;
  a.click();
  URL.revokeObjectURL(url);
}

async function regenCarousel() {
  const col = document.getElementById('ig-carousel-col');
  if (!col) return;
  col.innerHTML = '<div class="empty-state"><span class="spinner"></span> מייצר קרוסלה חדשה...</div>';
  try {
    const res = await fetch(`/api/generate/section/instagram_carousel`, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      if (window.currentContent) currentContent.instagram_carousel = data.text;
      renderCarousel();
      showToast('✅ קרוסלה חדשה נוצרה!');
    } else {
      col.innerHTML = `<div class="empty-state">❌ שגיאה: ${data.error || ''}</div>`;
    }
  } catch (e) {
    col.innerHTML = `<div class="empty-state">❌ שגיאת חיבור</div>`;
  }
}

function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
