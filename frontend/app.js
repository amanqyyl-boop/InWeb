// ==========================================
//  全局配置
// ==========================================
const API_BASE = 'http://127.0.0.1:5000/api';

// ==========================================
//  状态
// ==========================================
const state = {
  novels: [],
  currentPage: 'home',
  currentNovelId: null,
  currentChapterIndex: 0,
  categoryFilter: 'all',
  catFilter: 'all',
  sortFilter: 'hot',
  isNight: false,
  currentUser: null,
  scrollPositions: {}
};

// ==========================================
//  DOM 引用
// ==========================================
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

const pages = {
  home: $('#page-home'),
  category: $('#page-category'),
  detail: $('#page-detail'),
  bookshelf: $('#page-bookshelf'),
  reader: $('#page-reader')
};

const navLinks        = $$('.nav-links li');
const navDetail       = $('#navDetail');
const navReader       = $('#navReader');
const navBookshelf    = $('#navBookshelf');
const hotGrid         = $('#hotGrid');
const topGrid         = $('#topGrid');
const categoryGrid    = $('#categoryGrid');
const resultCount     = $('#resultCount');
const recommendGrid   = $('#recommendGrid');
const recommendSection = $('#recommendSection');
const recommendTags   = $('#recommendTags');
const detailHeader    = $('#detailHeader');
const chapterItems    = $('#chapterItems');
const readerChapterTitle = $('#readerChapterTitle');
const readerContent   = $('#readerContent');
const readerChInfo    = $('#readerChInfo');
const prevChapterBtn  = $('#prevChapter');
const nextChapterBtn  = $('#nextChapter');
const searchInput     = $('#searchInput');
const heroSearchInput = $('#heroSearchInput');
const searchBtn       = $('#searchBtn');
const heroSearchBtn   = $('#heroSearchBtn');
const themeToggle     = $('#themeToggle');
const backTop         = $('#backTop');
const mobileMenuBtn   = $('#mobileMenuBtn');
const navLinksEl      = $('#navLinks');
const homeCategoryTabs = $$('#homeCategoryTabs .tab');
const catFilter       = $('#catFilter');
const sortFilter      = $('#sortFilter');
const loginBtn        = $('#loginBtn');
const registerBtn     = $('#registerBtn');
const userAvatar      = $('#userAvatar');
const avatarLetter    = $('#avatarLetter');
const userDropdown    = $('#userDropdown');
const dropdownProfile = $('#dropdownProfile');
const dropdownBookshelf = $('#dropdownBookshelf');
const dropdownHistory = $('#dropdownHistory');
const dropdownLogout  = $('#dropdownLogout');
const modalOverlay    = $('#modalOverlay');
const modalContent    = $('#modalContent');
const toastContainer  = $('#toastContainer');
const bookshelfGrid   = $('#bookshelfGrid');
const commentList     = $('#commentList');
const commentInput    = $('#commentInput');
const commentSubmitBtn = $('#commentSubmitBtn');

// ==========================================
//  本地存储（书架 / 评论 / 阅读进度）
// ==========================================

// --- 书架 ---
function getBookshelf() {
  try { return JSON.parse(localStorage.getItem('gbu_bookshelf') || '[]'); }
  catch { return []; }
}

function saveBookshelf(list) {
  localStorage.setItem('gbu_bookshelf', JSON.stringify(list));
}

function isInBookshelf(id) {
  return getBookshelf().indexOf(id) !== -1;
}

function toggleBookshelf(id) {
  const list = getBookshelf();
  const idx  = list.indexOf(id);
  if (idx !== -1) {
    list.splice(idx, 1);
    saveBookshelf(list);
    return false;
  } else {
    list.push(id);
    saveBookshelf(list);
    return true;
  }
}

// --- 评论 ---
function getComments(novelId) {
  try { return JSON.parse(localStorage.getItem('gbu_comments_' + novelId) || '[]'); }
  catch { return []; }
}

function saveComments(novelId, comments) {
  localStorage.setItem('gbu_comments_' + novelId, JSON.stringify(comments));
}

function addComment(novelId, username, text) {
  const comments = getComments(novelId);
  comments.unshift({
    id: Date.now(),
    username: username,
    text: text,
    time: new Date().toLocaleString('zh-CN')
  });
  if (comments.length > 50) comments.length = 50;
  saveComments(novelId, comments);
}

function deleteComment(novelId, commentId) {
  const comments = getComments(novelId).filter(c => c.id !== commentId);
  saveComments(novelId, comments);
}

// --- 阅读进度 ---
function getReadingProgress(userId) {
  try { return JSON.parse(localStorage.getItem('gbu_progress_' + userId) || '{}'); }
  catch { return {}; }
}

function saveReadingProgress(userId, novelId, chapterIdx) {
  const progress = getReadingProgress(userId);
  progress[novelId] = chapterIdx;
  localStorage.setItem('gbu_progress_' + userId, JSON.stringify(progress));
}

function getLastChapter(userId, novelId) {
  const progress = getReadingProgress(userId);
  return progress[novelId] !== undefined ? progress[novelId] : 0;
}

// ==========================================
//  API 调用
// ==========================================
async function api(url, options = {}) {
  try {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    options.headers = headers;
    const res  = await fetch(API_BASE + url, options);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || '请求失败');
    return data;
  } catch (e) {
    showToast(e.message, 'error');
    throw e;
  }
}

async function loadNovels(category = 'all', sort = 'hot') {
  return await api(`/novels?category=${category}&sort=${sort}`);
}

async function loadRecommend() {
  if (!state.currentUser) return;
  const recs = await api(`/recommend/${state.currentUser.id}`);
  renderGrid(recommendGrid, recs, true);
}

// ==========================================
//  工具函数
// ==========================================
function renderGrid(gridEl, novels, isRecommend = false) {
  if (!novels.length) {
    gridEl.innerHTML = `
      <div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--text-muted);">
        暂无结果
      </div>`;
    return;
  }

  gridEl.innerHTML = novels.map(n => {
    const badge  = n.rating >= 9 ? '<span class="badge">神作</span>' : '';
    const recTag = isRecommend
      ? '<span class="rec-tag"><i class="fas fa-star"></i> 推荐</span>'
      : '';
    return `
      <div class="novel-card" data-id="${n.id}">
        <div class="novel-cover">
          ${n.cover}${badge}${recTag}
        </div>
        <div class="novel-info">
          <h3>${n.title}</h3>
          <div class="author">${n.author}</div>
          <div class="meta">
            <span class="rating">
              <i class="fas fa-star"></i> ${n.rating}
            </span>
            <span>${n.category}</span>
          </div>
        </div>
      </div>`;
  }).join('');

  gridEl.querySelectorAll('.novel-card').forEach(card => {
    card.addEventListener('click', () => openDetail(card.dataset.id));
  });
}

function showToast(message, type = 'info') {
  const icons = {
    success: '<i class="fas fa-check-circle"></i>',
    error: '<i class="fas fa-exclamation-circle"></i>',
    info: '<i class="fas fa-info-circle"></i>'
  };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `${icons[type] || icons.info} ${message}`;
  toastContainer.appendChild(toast);
  setTimeout(() => { if (toast.parentNode) toast.remove(); }, 3200);
}

function closeModal() {
  modalOverlay.classList.remove('show');
}

function openModal(html) {
  modalContent.innerHTML = html;
  modalOverlay.classList.add('show');
}

// ==========================================
//  页面渲染
// ==========================================

// --- 首页 ---
function renderHome() {
  Promise.all([
    loadNovels(state.categoryFilter, 'hot'),
    loadNovels(state.categoryFilter, 'rating')
  ]).then(([hot, top]) => {
    renderGrid(hotGrid, hot.slice(0, 6));
    renderGrid(topGrid, top.slice(0, 6));
  });

  if (state.currentUser) {
    recommendSection.style.display = 'block';
    const prefs = state.currentUser.preferences || [];
    recommendTags.innerHTML = prefs.map(p => `<span>${p}</span>`).join('');
    loadRecommend();
  } else {
    recommendSection.style.display = 'none';
  }

  homeCategoryTabs.forEach(tab =>
    tab.classList.toggle('active', tab.dataset.cat === state.categoryFilter)
  );
}

// --- 分类页 ---
function renderCategory() {
  loadNovels(state.catFilter, state.sortFilter).then(list => {
    resultCount.textContent = `共 ${list.length} 部`;
    renderGrid(categoryGrid, list);
  });
  catFilter.value  = state.catFilter;
  sortFilter.value = state.sortFilter;
}

// --- 书架页 ---
function renderBookshelf() {
  const ids = getBookshelf();
  if (!ids.length) {
    bookshelfGrid.innerHTML = `
      <div style="grid-column:1/-1;text-align:center;padding:60px 20px;color:var(--text-muted);">
        <i class="fas fa-bookmark"
           style="font-size:48px;display:block;margin-bottom:16px;opacity:0.4;">
        </i>
        书架是空的<br>去书库找本喜欢的书吧
      </div>`;
    return;
  }

  loadNovels('all', 'hot').then(all => {
    const books = all.filter(n => ids.indexOf(n.id) !== -1);
    renderGrid(bookshelfGrid, books);
    // 移除后端已经不存在的 ID
    if (books.length < ids.length) {
      const validIds = books.map(b => b.id);
      saveBookshelf(ids.filter(id => validIds.indexOf(id) !== -1));
    }
  });
}

// --- 评论区渲染 ---
function renderComments(novelId) {
  const comments = getComments(novelId);
  if (!comments.length) {
    commentList.innerHTML = '<div class="comment-empty">暂无评论，来写第一条吧</div>';
    return;
  }

  const currentName = state.currentUser ? state.currentUser.username : '';

  commentList.innerHTML = comments.map(c => {
    const deleteBtn = (currentName && currentName === c.username)
      ? `<span class="comment-delete" data-cid="${c.id}">
           <i class="fas fa-trash-alt"></i>
         </span>`
      : '';
    return `
      <div class="comment-item">
        <div class="comment-user">
          ${c.username}
          <span class="comment-time">${c.time}</span>
          ${deleteBtn}
        </div>
        <div class="comment-text">${c.text}</div>
      </div>`;
  }).join('');

  commentList.querySelectorAll('.comment-delete').forEach(el => {
    el.addEventListener('click', () => {
      const cid = parseInt(el.dataset.cid);
      deleteComment(novelId, cid);
      renderComments(novelId);
      showToast('评论已删除', 'info');
    });
  });
}

// --- 详情页 ---
function openDetail(id) {
  state.currentNovelId = id;

  if (state.currentUser) {
    api('/browse', {
      method: 'POST',
      body: JSON.stringify({ user_id: state.currentUser.id, novel_id: id })
    });
  }

  api(`/novels/${id}`).then(novel => {
    if (!novel) return;

    const lastCh = state.currentUser
      ? getLastChapter(state.currentUser.id, id)
      : 0;
    state.currentChapterIndex = lastCh;

    const inShelf  = isInBookshelf(id);
    const icon     = inShelf ? 'fas fa-check' : 'fas fa-plus';
    const text     = inShelf ? '已在书架' : '加入书架';
    const btnText  = lastCh > 0
      ? `继续阅读 (第${lastCh + 1}章)`
      : '开始阅读';

    detailHeader.innerHTML = `
      <div class="detail-cover">${novel.cover}</div>
      <div class="detail-meta">
        <h1>${novel.title}</h1>
        <div class="author">${novel.author}</div>
        <div class="desc">${novel.desc}</div>
        <div class="tags">
          <span>${novel.category}</span>
          <span>评分 ${novel.rating}</span>
        </div>
        <div class="stats">
          <span><i class="fas fa-fire"></i> ${novel.hot} 人气</span>
          <span><i class="fas fa-book"></i> ${novel.chapters.length} 章</span>
        </div>
        <div class="detail-actions">
          <button class="btn btn-primary" id="startReadBtn">
            <i class="fas fa-book-open"></i> ${btnText}
          </button>
          <button class="btn btn-secondary" id="shelfBtn">
            <i class="${icon}"></i> ${text}
          </button>
        </div>
      </div>`;

    detailHeader.querySelector('#startReadBtn')
      .addEventListener('click', () => openReader(novel.id, lastCh));

    detailHeader.querySelector('#shelfBtn')
      .addEventListener('click', () => {
        const added = toggleBookshelf(novel.id);
        const btn   = detailHeader.querySelector('#shelfBtn');
        btn.innerHTML = added
          ? '<i class="fas fa-check"></i> 已在书架'
          : '<i class="fas fa-plus"></i> 加入书架';
        showToast(added ? '已加入书架' : '已从书架移除', 'info');
      });

    chapterItems.innerHTML = novel.chapters.map((ch, i) => {
      const highlight = i === lastCh
        ? ' style="color:var(--accent);font-weight:600;"'
        : '';
      return `<li data-index="${i}"${highlight}>
        ${i === lastCh ? '📖 ' : ''}${ch}
      </li>`;
    }).join('');

    chapterItems.querySelectorAll('li').forEach(li => {
      li.addEventListener('click', () =>
        openReader(novel.id, parseInt(li.dataset.index))
      );
    });

    renderComments(novel.id);
    navigateTo('detail');
  });
}

// --- 阅读器 ---
function openReader(id, idx) {
  state.currentNovelId = id;
  state.currentChapterIndex = idx;
  if (state.currentUser) {
    saveReadingProgress(state.currentUser.id, id, idx);
  }
  navigateTo('reader');
  renderReader();
}

function renderReader() {
  api(`/novels/${state.currentNovelId}`).then(novel => {
    if (!novel) return;

    const idx    = state.currentChapterIndex;
    const title  = novel.chapters[idx] || '未知章节';

    readerChapterTitle.textContent = title;
    readerChInfo.textContent = `${idx + 1} / ${novel.chapters.length}`;

    const paragraphs = [
      `${novel.title} · ${title}`,
      novel.desc,
      '『湾区书屋 · GBU』为您呈现精彩内容。',
      '窗外细雨霏霏，屋檐滴水成线。',
      '他抬手轻轻翻过一页，仿佛掀开了一段尘封的岁月。',
      '"你来了。"一个低沉的声音从暗处传来。',
      '脚步停住，他没有回头，只是淡淡道："我来了。"',
      '风从窗缝中挤进来，灯焰摇晃，墙上的影子也随之扭曲……',
      '—— 未完待续 ——'
    ];

    readerContent.innerHTML = paragraphs.map(p => `<p>${p}</p>`).join('');
    prevChapterBtn.disabled = idx <= 0;
    nextChapterBtn.disabled = idx >= novel.chapters.length - 1;
  });
}

// ==========================================
//  导航
// ==========================================
function navigateTo(page) {
  // 离开前保存滚动位置
  if (state.currentPage && pages[state.currentPage]) {
    state.scrollPositions[state.currentPage] = window.scrollY;
  }

  // 切换页面
  Object.values(pages).forEach(p => p.classList.remove('active'));
  if (pages[page]) pages[page].classList.add('active');
  state.currentPage = page;

  // 导航栏激活状态
  navLinks.forEach(li => li.classList.toggle('active', li.dataset.page === page));
  navDetail.style.display    = page === 'detail' ? 'block' : 'none';
  navReader.style.display    = page === 'reader' ? 'block' : 'none';
  navBookshelf.style.display = state.currentUser ? 'block' : 'none';
  navLinksEl.classList.remove('open');

  // 滚动位置恢复
  const savedPos = state.scrollPositions[page];
  if (savedPos !== undefined && (page === 'home' || page === 'category')) {
    window.scrollTo({ top: savedPos });
  } else {
    window.scrollTo(0, 0);
  }

  // 渲染对应页面
  if (page === 'home')       renderHome();
  else if (page === 'category')  renderCategory();
  else if (page === 'bookshelf') renderBookshelf();
  else if (page === 'reader')    renderReader();
}

// ==========================================
//  用户系统
// ==========================================
function register(username, password, preferences) {
  api('/register', {
    method: 'POST',
    body: JSON.stringify({ username, password, preferences })
  }).then(user => {
    state.currentUser = user;
    sessionStorage.setItem('userId', user.id);
    updateUserUI();
    showToast('注册成功', 'success');
    closeModal();
    renderHome();
  }).catch(() => {});
}

function login(username, password) {
  api('/login', {
    method: 'POST',
    body: JSON.stringify({ username, password })
  }).then(user => {
    state.currentUser = user;
    sessionStorage.setItem('userId', user.id);
    updateUserUI();
    showToast('登录成功', 'success');
    closeModal();
    renderHome();
  }).catch(() => {});
}

function logout() {
  state.currentUser = null;
  sessionStorage.removeItem('userId');
  updateUserUI();
  showToast('已退出登录', 'info');
  closeDropdown();
  if (state.currentPage === 'detail' || state.currentPage === 'reader') {
    navigateTo('home');
  }
  renderHome();
}

function updatePreferences(preferences) {
  api(`/user/${state.currentUser.id}/preferences`, {
    method: 'PUT',
    body: JSON.stringify({ preferences })
  }).then(data => {
    state.currentUser.preferences = data.preferences;
    showToast('偏好已更新', 'success');
    closeModal();
    renderHome();
  }).catch(() => {});
}

function updateUserUI() {
  const user = state.currentUser;
  if (user) {
    loginBtn.style.display       = 'none';
    registerBtn.style.display    = 'none';
    userAvatar.style.display     = 'flex';
    avatarLetter.textContent     = user.username.charAt(0).toUpperCase();
    recommendSection.style.display = 'block';
    navBookshelf.style.display   = 'block';
  } else {
    loginBtn.style.display       = 'inline-block';
    registerBtn.style.display    = 'inline-block';
    userAvatar.style.display     = 'none';
    recommendSection.style.display = 'none';
    navBookshelf.style.display   = 'none';
  }
}

function restoreSession() {
  const userId = sessionStorage.getItem('userId');
  if (userId) {
    api(`/user/${userId}`)
      .then(user => {
        state.currentUser = user;
        updateUserUI();
        renderHome();
      })
      .catch(() => sessionStorage.removeItem('userId'));
  }
}

function closeDropdown() {
  userDropdown.classList.remove('show');
}

// ==========================================
//  模态框
// ==========================================
const ALL_CATEGORIES = ['玄幻', '仙侠', '都市', '言情', '历史', '科幻', '悬疑'];

function showRegisterModal() {
  const tagsHtml = ALL_CATEGORIES
    .map(c => `<span class="ptag" data-tag="${c}">${c}</span>`)
    .join('');

  openModal(`
    <button class="close-modal" id="modalCloseBtn">&times;</button>
    <h2>📝 注册账号</h2>
    <div class="subtitle">加入湾区书屋，享受个性化推荐</div>

    <div class="form-group">
      <label>用户名</label>
      <input type="text" id="regUsername" placeholder="请输入用户名" />
    </div>

    <div class="form-group">
      <label>密码</label>
      <input type="password" id="regPassword" placeholder="至少3位密码" />
    </div>

    <div class="form-group">
      <label>偏好类型（至少选2项）</label>
      <div class="pref-tags" id="regPrefTags">${tagsHtml}</div>
      <div class="hint" id="regPrefHint">已选择 0 项</div>
    </div>

    <button class="btn-block" id="regSubmitBtn">注册并开启推荐</button>

    <div class="switch-action">
      已有账号？ <span id="switchToLogin">去登录</span>
    </div>
  `);

  const selected = new Set();
  const tagEls   = modalContent.querySelectorAll('#regPrefTags .ptag');
  const hint     = modalContent.querySelector('#regPrefHint');

  tagEls.forEach(el => {
    el.addEventListener('click', () => {
      const tag = el.dataset.tag;
      if (selected.has(tag)) {
        selected.delete(tag);
        el.classList.remove('selected');
      } else {
        selected.add(tag);
        el.classList.add('selected');
      }
      hint.textContent = `已选择 ${selected.size} 项`;
    });
  });

  modalContent.querySelector('#regSubmitBtn')
    .addEventListener('click', () => {
      const username = modalContent.querySelector('#regUsername').value.trim();
      const password = modalContent.querySelector('#regPassword').value;
      register(username, password, Array.from(selected));
    });

  modalContent.querySelector('#switchToLogin')
    .addEventListener('click', showLoginModal);

  modalContent.querySelector('#modalCloseBtn')
    .addEventListener('click', closeModal);
}

function showLoginModal() {
  openModal(`
    <button class="close-modal" id="modalCloseBtn">&times;</button>
    <h2>🔑 登录</h2>
    <div class="subtitle">欢迎回来</div>

    <div class="form-group">
      <label>用户名</label>
      <input type="text" id="loginUsername" placeholder="请输入用户名" />
    </div>

    <div class="form-group">
      <label>密码</label>
      <input type="password" id="loginPassword" placeholder="请输入密码" />
    </div>

    <button class="btn-block" id="loginSubmitBtn">登录</button>

    <div class="switch-action">
      还没有账号？ <span id="switchToRegister">去注册</span>
    </div>
  `);

  modalContent.querySelector('#loginSubmitBtn')
    .addEventListener('click', () => {
      const username = modalContent.querySelector('#loginUsername').value.trim();
      const password = modalContent.querySelector('#loginPassword').value;
      login(username, password);
    });

  modalContent.querySelector('#switchToRegister')
    .addEventListener('click', showRegisterModal);

  modalContent.querySelector('#modalCloseBtn')
    .addEventListener('click', closeModal);
}

function showPreferenceModal() {
  if (!state.currentUser) return;

  const currentPrefs = state.currentUser.preferences || [];
  const tagsHtml = ALL_CATEGORIES.map(c => {
    const sel = currentPrefs.includes(c) ? ' selected' : '';
    return `<span class="ptag${sel}" data-tag="${c}">${c}</span>`;
  }).join('');

  openModal(`
    <button class="close-modal" id="modalCloseBtn">&times;</button>
    <h2>🎯 我的偏好</h2>
    <div class="subtitle">选择你喜欢的类型</div>

    <div class="form-group">
      <label>偏好类型（至少选2项）</label>
      <div class="pref-tags" id="prefEditTags">${tagsHtml}</div>
      <div class="hint" id="prefEditHint">已选择 ${currentPrefs.length} 项</div>
    </div>

    <button class="btn-block" id="prefSaveBtn">保存偏好</button>
  `);

  const selected = new Set(currentPrefs);
  const tagEls   = modalContent.querySelectorAll('#prefEditTags .ptag');
  const hint     = modalContent.querySelector('#prefEditHint');

  tagEls.forEach(el => {
    el.addEventListener('click', () => {
      const tag = el.dataset.tag;
      if (selected.has(tag)) {
        selected.delete(tag);
        el.classList.remove('selected');
      } else {
        selected.add(tag);
        el.classList.add('selected');
      }
      hint.textContent = `已选择 ${selected.size} 项`;
    });
  });

  modalContent.querySelector('#prefSaveBtn')
    .addEventListener('click', () => updatePreferences(Array.from(selected)));

  modalContent.querySelector('#modalCloseBtn')
    .addEventListener('click', closeModal);
}

function showHistoryModal() {
  if (!state.currentUser) return;

  api(`/history/${state.currentUser.id}`).then(novels => {
    let listHtml = '';
    if (!novels.length) {
      listHtml = '<p style="color:var(--text-muted);padding:20px 0;">还没有浏览记录</p>';
    } else {
      listHtml = novels.map(n => `
        <div style="display:flex;align-items:center;gap:14px;
                    padding:10px 0;border-bottom:1px solid var(--border);cursor:pointer;"
             data-id="${n.id}">
          <span style="font-size:28px;">${n.cover}</span>
          <div>
            <strong>${n.title}</strong>
            <div style="font-size:13px;color:var(--text-muted);">
              ${n.author} · ${n.category}
            </div>
          </div>
        </div>
      `).join('');
    }

    openModal(`
      <button class="close-modal" id="modalCloseBtn">&times;</button>
      <h2>📖 浏览记录</h2>
      <div class="subtitle">最近阅读过的小说 (最多20条)</div>
      <div style="max-height:400px;overflow-y:auto;">${listHtml}</div>
    `);

    modalContent.querySelectorAll('[data-id]').forEach(el => {
      el.addEventListener('click', () => {
        closeModal();
        openDetail(el.dataset.id);
      });
    });

    modalContent.querySelector('#modalCloseBtn')
      .addEventListener('click', closeModal);
  });
}

// ==========================================
//  事件绑定
// ==========================================

// --- 导航 ---
navLinks.forEach(li => {
  li.addEventListener('click', () => {
    if (pages[li.dataset.page]) navigateTo(li.dataset.page);
  });
});

document.querySelector('.logo').addEventListener('click', () => navigateTo('home'));

// --- 首页分类标签 ---
homeCategoryTabs.forEach(tab => {
  tab.addEventListener('click', () => {
    state.categoryFilter = tab.dataset.cat;
    homeCategoryTabs.forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    renderHome();
  });
});

// --- 分类页筛选 ---
catFilter.addEventListener('change', () => {
  state.catFilter = catFilter.value;
  renderCategory();
});

sortFilter.addEventListener('change', () => {
  state.sortFilter = sortFilter.value;
  renderCategory();
});

// --- 搜索 ---
function performSearch(query) {
  if (!query.trim()) return;
  state.catFilter  = 'all';
  state.sortFilter = 'hot';
  catFilter.value  = 'all';
  sortFilter.value = 'hot';

  loadNovels('all', 'hot').then(all => {
    const filtered = all.filter(n =>
      n.title.includes(query) || n.author.includes(query)
    );
    renderGrid(categoryGrid, filtered);
    resultCount.textContent = `搜索 "${query}" 共 ${filtered.length} 部`;
    navigateTo('category');
  });
}

searchBtn.addEventListener('click', () => performSearch(searchInput.value));
searchInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') performSearch(searchInput.value);
});
heroSearchBtn.addEventListener('click', () => performSearch(heroSearchInput.value));
heroSearchInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') performSearch(heroSearchInput.value);
});

// --- 阅读器翻页 ---
prevChapterBtn.addEventListener('click', () => {
  if (state.currentChapterIndex > 0) {
    state.currentChapterIndex--;
    if (state.currentUser) {
      saveReadingProgress(
        state.currentUser.id,
        state.currentNovelId,
        state.currentChapterIndex
      );
    }
    renderReader();
    window.scrollTo(0, 0);
  }
});

nextChapterBtn.addEventListener('click', () => {
  api(`/novels/${state.currentNovelId}`).then(novel => {
    if (state.currentChapterIndex < novel.chapters.length - 1) {
      state.currentChapterIndex++;
      if (state.currentUser) {
        saveReadingProgress(
          state.currentUser.id,
          state.currentNovelId,
          state.currentChapterIndex
        );
      }
      renderReader();
      window.scrollTo(0, 0);
    }
  });
});

// --- 夜间模式 ---
themeToggle.addEventListener('click', () => {
  state.isNight = !state.isNight;
  document.body.classList.toggle('night-mode', state.isNight);
  themeToggle.innerHTML = state.isNight
    ? '<i class="fas fa-sun"></i>'
    : '<i class="fas fa-moon"></i>';
  localStorage.setItem('gbu_night', state.isNight);
});

if (localStorage.getItem('gbu_night') === 'true') {
  state.isNight = true;
  document.body.classList.add('night-mode');
  themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
}

// --- 回到顶部 ---
window.addEventListener('scroll', () => {
  backTop.classList.toggle('visible', window.scrollY > 400);
});
backTop.addEventListener('click', () => window.scrollTo(0, 0));

// --- 移动端菜单 ---
mobileMenuBtn.addEventListener('click', () => navLinksEl.classList.toggle('open'));
document.addEventListener('click', e => {
  if (!e.target.closest('.header')) navLinksEl.classList.remove('open');
});

// --- 登录 / 注册 ---
loginBtn.addEventListener('click', showLoginModal);
registerBtn.addEventListener('click', showRegisterModal);

// --- 用户下拉菜单 ---
userAvatar.addEventListener('click', e => {
  e.stopPropagation();
  userDropdown.classList.toggle('show');
});
document.addEventListener('click', () => userDropdown.classList.remove('show'));

dropdownProfile.addEventListener('click', () => {
  closeDropdown();
  showPreferenceModal();
});

dropdownBookshelf.addEventListener('click', () => {
  closeDropdown();
  if (state.currentUser) {
    navigateTo('bookshelf');
  } else {
    showToast('请先登录', 'error');
  }
});

dropdownHistory.addEventListener('click', () => {
  closeDropdown();
  showHistoryModal();
});

dropdownLogout.addEventListener('click', () => {
  closeDropdown();
  logout();
});

// --- 模态框 ---
modalOverlay.addEventListener('click', e => {
  if (e.target === modalOverlay) closeModal();
});

// --- 发表评论 ---
commentSubmitBtn.addEventListener('click', () => {
  if (!state.currentUser) {
    showToast('请先登录后再评论', 'error');
    return;
  }
  const text = commentInput.value.trim();
  if (!text) {
    showToast('请输入评论内容', 'error');
    return;
  }
  addComment(state.currentNovelId, state.currentUser.username, text);
  commentInput.value = '';
  renderComments(state.currentNovelId);
  showToast('评论发表成功', 'success');
});

// --- 键盘快捷键 ---
document.addEventListener('keydown', e => {
  if (state.currentPage === 'reader') {
    if (e.key === 'ArrowLeft' || e.key === 'a') {
      prevChapterBtn.click();
      e.preventDefault();
    } else if (e.key === 'ArrowRight' || e.key === 'd') {
      nextChapterBtn.click();
      e.preventDefault();
    }
  }
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    searchInput.focus();
  }
  if (e.key === 'Escape') closeModal();
});

// ==========================================
//  初始化
// ==========================================
restoreSession();
navigateTo('home');