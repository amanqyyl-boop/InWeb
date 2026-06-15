// ==========================================
//  全局配置
// ==========================================
// 如果是从 Flask 前端页面访问则用相对路径，否则用绝对路径
const API_BASE = window.location.origin.includes('127.0.0.1:5000') || window.location.origin.includes('localhost:5000')
  ? '/api'
  : 'http://127.0.0.1:5000/api';

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
const prevChapterBtn     = $('#prevChapter');
const nextChapterBtn     = $('#nextChapter');
const backToChaptersBtn  = $('#backToChapters');
const searchInput     = $('#searchInput');
const heroSearchInput = $('#heroSearchInput');
const searchBtn       = $('#searchBtn');
const heroSearchBtn   = $('#heroSearchBtn');
const uploadBtn       = $('#uploadBtn');
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

// --- 评论（服务端 API）---
async function loadComments(novelId, chapterIndex, paragraphIndex = -1) {
  try {
    const res = await fetch(`${API_BASE}/comments/${novelId}/${chapterIndex}?pi=${paragraphIndex}`);
    return await res.json();
  } catch { return []; }
}

async function postComment(novelId, chapterIndex, text, paragraphIndex = -1, parentId = null) {
  if (!state.currentUser) { showToast('请先登录', 'error'); return null; }
  const res = await fetch(`${API_BASE}/comments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: state.currentUser.id, novel_id: novelId,
      chapter_index: chapterIndex, paragraph_index: paragraphIndex, text, parent_id: parentId })
  });
  const data = await res.json();
  if (!res.ok) { showToast(data.error || '评论失败', 'error'); return null; }
  return data;
}

async function voteComment(commentId, vote) {
  if (!state.currentUser) { showToast('请先登录', 'error'); return; }
  await fetch(`${API_BASE}/comments/${commentId}/vote`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: state.currentUser.id, vote })
  });
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
  renderGrid(recommendGrid, recs.slice(0, 10), true);
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
    renderGrid(hotGrid, hot.slice(0, 5));
    renderGrid(topGrid, top.slice(0, 5));
  });

  if (state.currentUser && state.categoryFilter === 'all') {
    recommendSection.style.display = 'block';
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

// --- 评论区渲染（服务端）---
function renderComments(novelId, chapterIndex = -1, container = null) {
  const list = container || commentList;
  list.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);"><i class="fas fa-spinner fa-pulse"></i> 加载中...</div>';
  loadComments(novelId, chapterIndex >= 0 ? chapterIndex : 0).then(comments => {
    if (!comments.length) {
      list.innerHTML = '<div class="comment-empty">暂无评论，来写第一条吧</div>';
      return;
    }
    list.innerHTML = comments.map(c => _renderCommentItem(c, novelId, chapterIndex)).join('');
    // 绑定回复/投票事件
    list.querySelectorAll('.c-reply-btn').forEach(btn => {
      btn.addEventListener('click', () => _toggleReplyForm(btn.dataset.cid, novelId, chapterIndex, list));
    });
    list.querySelectorAll('.c-vote-up, .c-vote-down').forEach(btn => {
      btn.addEventListener('click', async () => {
        await voteComment(parseInt(btn.dataset.cid), parseInt(btn.dataset.vote));
        renderComments(novelId, chapterIndex, container);
      });
    });
  });
}

function _renderCommentItem(c, novelId, chapterIndex, isReply = false) {
  const time = new Date(c.created_at * 1000).toLocaleString('zh-CN');
  const voteCls = (v) => v > 0 ? 'c-vote-active' : '';
  return `
    <div class="comment-item" style="${isReply ? 'margin-left:32px;padding:8px 12px;background:var(--bg);border-radius:var(--radius-sm);' : ''}">
      <div class="comment-user">
        <span class="c-avatar">${c.username.charAt(0).toUpperCase()}</span>
        <strong>${c.username}</strong>
        <span class="comment-time">${time}</span>
      </div>
      <div class="comment-text">${c.text}</div>
      <div class="comment-actions">
        <span class="c-vote-up ${voteCls(c.upvotes - c.downvotes)}" data-cid="${c.id}" data-vote="1">
          <i class="fas fa-thumbs-up"></i> ${c.upvotes}
        </span>
        <span class="c-vote-down" data-cid="${c.id}" data-vote="-1">
          <i class="fas fa-thumbs-down"></i> ${c.downvotes}
        </span>
        ${!isReply ? `<span class="c-reply-btn" data-cid="${c.id}"><i class="fas fa-reply"></i> 回复</span>` : ''}
      </div>
      ${c.replies && c.replies.length ? c.replies.map(r => _renderCommentItem(r, novelId, chapterIndex, true)).join('') : ''}
      <div class="c-reply-form" id="replyForm-${c.id}" style="display:none;">
        <input type="text" placeholder="写下回复..." class="c-reply-input" />
        <button class="c-reply-submit" data-cid="${c.id}">发送</button>
      </div>
    </div>`;
}

function _toggleReplyForm(cid, novelId, chapterIndex, list) {
  const form = list.querySelector(`#replyForm-${cid}`);
  if (!form) return;
  const shown = form.style.display !== 'none';
  form.style.display = shown ? 'none' : 'flex';
  if (!shown) {
    const input = form.querySelector('.c-reply-input');
    const btn = form.querySelector('.c-reply-submit');
    btn.onclick = async () => {
      const text = input.value.trim();
      if (!text) return;
      await postComment(novelId, chapterIndex, text, -1, parseInt(cid));
      input.value = '';
      form.style.display = 'none';
      renderComments(novelId, chapterIndex, list);
      showToast('回复成功', 'success');
    };
  }
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

    renderComments(novel.id, 0);
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
  const nid = state.currentNovelId;
  const idx = state.currentChapterIndex;

  api(`/novels/${nid}`).then(novel => {
    if (!novel) return;
    readerChInfo.textContent = `${idx + 1} / ${novel.chapters.length}`;
    prevChapterBtn.disabled = idx <= 0;
    nextChapterBtn.disabled = idx >= novel.chapters.length - 1;

    api(`/novels/${nid}/content/${idx}`).then(async data => {
      const title = data.chapter_title || novel.chapters[idx] || '未知章节';
      readerChapterTitle.textContent = title;

      const paragraphs = data.content.split('\n').filter(p => p.trim());
      // 一次性加载本章所有评论，前端按段落分组
      const allComments = await loadComments(nid, idx);
      const commentMap = {};
      allComments.forEach(c => {
        const pi = c.paragraph_index;
        if (!commentMap[pi]) commentMap[pi] = [];
        commentMap[pi].push(c);
      });

      readerContent.innerHTML = paragraphs.map((p, pi) => {
        const pc = commentMap[pi] || [];
        return `
          <div class="p-wrap">
            <p class="p-text">${p.trim()}</p>
            <div class="p-comments">
              <span class="p-cmt-btn" data-pi="${pi}">
                <i class="fas fa-comment-dots"></i>
                ${pc.length ? `<span class="p-cmt-count">${pc.length}</span>` : ''}
              </span>
              <div class="p-cmts" id="pCmts-${pi}" style="display:none;">
                ${pc.length
                  ? pc.map(c => _renderCommentItem(c, nid, idx)).join('')
                  : '<div style="font-size:12px;color:var(--text-muted);padding:4px 0;">暂无段落评论</div>'
                }
              </div>
            </div>
          </div>`;
      }).join('');

      // 绑定段落评论按钮事件
      readerContent.querySelectorAll('.p-cmt-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const pi = btn.dataset.pi;
          const panel = document.getElementById(`pCmts-${pi}`);
          const isOpen = panel.style.display !== 'none';
          readerContent.querySelectorAll('.p-cmts').forEach(el => el.style.display = 'none');
          panel.style.display = isOpen ? 'none' : 'block';
          if (!isOpen && !panel.querySelector('.p-cmt-form')) {
            const form = document.createElement('div');
            form.className = 'p-cmt-form';
            form.innerHTML = `<input type="text" class="p-cmt-input" placeholder="在此段落下写评论..." /><button class="p-cmt-send">发送</button>`;
            panel.appendChild(form);
            form.querySelector('.p-cmt-send').addEventListener('click', async () => {
              const input = form.querySelector('.p-cmt-input');
              const text = input.value.trim();
              if (!text) return;
              const result = await postComment(nid, idx, text, parseInt(pi));
              if (result) {
                input.value = '';
                showToast('评论已发表', 'success');
                loadComments(nid, idx, parseInt(pi)).then(cs => {
                  panel.innerHTML = cs.map(c => _renderCommentItem(c, nid, idx)).join('');
                });
              }
            });
          }
        });
      });
      // 绑定回复/投票事件（预渲染的评论）
      readerContent.querySelectorAll('.c-reply-btn').forEach(btn => {
        btn.addEventListener('click', () => _toggleReplyForm(btn.dataset.cid, nid, idx, btn.closest('.p-cmts')));
      });
      readerContent.querySelectorAll('.c-vote-up, .c-vote-down').forEach(btn => {
        btn.addEventListener('click', async () => {
          await voteComment(parseInt(btn.dataset.cid), parseInt(btn.dataset.vote));
          const panel = btn.closest('.p-cmts');
          if (panel) {
            const pi = parseInt(panel.id.replace('pCmts-', ''));
            loadComments(nid, idx, pi).then(cs => {
              panel.innerHTML = cs.map(c => _renderCommentItem(c, nid, idx)).join('');
            });
          }
        });
      });
    }).catch(() => {
      readerChapterTitle.textContent = novel.chapters[idx] || '未知章节';
      readerContent.innerHTML = '<p style="color:var(--text-muted);">章节内容加载失败</p>';
    });
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
    recommendSection.style.display = state.categoryFilter === 'all' ? 'block' : 'none';
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
//  上传小说模态框（双模式）
// ==========================================

function showUploadModal() {
  const catOptions = ALL_CATEGORIES.map(c =>
    `<option value="${c}">${c}</option>`
  ).join('');
  const isLoggedIn = !!state.currentUser;

  openModal(`
    <button class="close-modal" id="modalCloseBtn">&times;</button>
    <h2>📤 上传小说</h2>
    <div class="subtitle">支持 txt 格式文件，文件将自动入库</div>

    <div class="upload-tabs">
      <span class="upload-tab active" data-mode="existing">📖 已有小说</span>
      <span class="upload-tab" data-mode="own">✍️ 我的创作</span>
    </div>

    <div class="form-group">
      <label>小说标题</label>
      <input type="text" id="uploadTitle" placeholder="请输入小说标题" />
    </div>

    <div class="form-group" id="uploadAuthorGroup">
      <label>作者</label>
      <input type="text" id="uploadAuthor" placeholder="请输入作者名" />
    </div>

    <div class="form-group" id="uploadAuthorAuto" style="display:none;">
      <label>作者</label>
      <div class="upload-author-auto">
        <i class="fas fa-user-circle"></i>
        <span id="uploadAuthorDisplay">${isLoggedIn ? state.currentUser.username : '未登录'}</span>
        ${!isLoggedIn ? '<span class="upload-login-hint">（请先登录）</span>' : ''}
      </div>
    </div>

    <div class="form-group">
      <label>分类</label>
      <select id="uploadCategory" class="upload-select">
        ${catOptions}
      </select>
    </div>

    <div class="form-group">
      <label>上传文件</label>
      <div class="upload-dropzone" id="uploadDropzone">
        <div class="dropzone-icon"><i class="fas fa-cloud-upload-alt"></i></div>
        <div class="dropzone-text">拖拽 txt 文件到此处，或点击选择</div>
        <div class="dropzone-hint">仅支持 .txt 格式</div>
        <input type="file" id="uploadFile" accept=".txt" hidden />
        <div class="dropzone-file" id="dropzoneFile" style="display:none;">
          <i class="fas fa-file-alt"></i>
          <span id="dropzoneFileName"></span>
          <span class="dropzone-remove" id="dropzoneRemove">&times;</span>
        </div>
      </div>
    </div>

    <button class="btn-block" id="uploadSubmitBtn" disabled>
      <i class="fas fa-upload"></i> 上传
    </button>

    <div class="upload-progress" id="uploadProgress" style="display:none;"></div>
  `);

  // ---- 模式切换 ----
  let currentMode = 'existing';
  const tabs       = modalContent.querySelectorAll('.upload-tab');
  const authorGrp  = modalContent.querySelector('#uploadAuthorGroup');
  const authorAuto = modalContent.querySelector('#uploadAuthorAuto');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      currentMode = tab.dataset.mode;

      if (currentMode === 'own') {
        authorGrp.style.display  = 'none';
        authorAuto.style.display = 'block';
        if (!isLoggedIn) {
          showToast('请先登录后再上传自己的作品', 'error');
          setTimeout(closeModal, 800);
          return;
        }
      } else {
        authorGrp.style.display  = 'block';
        authorAuto.style.display = 'none';
      }
    });
  });

  // ---- 拖拽 / 点击上传逻辑 ----
  const dropzone   = modalContent.querySelector('#uploadDropzone');
  const fileInput  = modalContent.querySelector('#uploadFile');
  const fileTag    = modalContent.querySelector('#dropzoneFile');
  const fileName   = modalContent.querySelector('#dropzoneFileName');
  const removeBtn  = modalContent.querySelector('#dropzoneRemove');
  const submitBtn  = modalContent.querySelector('#uploadSubmitBtn');
  let selectedFile = null;

  function updateFileUI(file) {
    if (file) {
      selectedFile = file;
      dropzone.classList.add('has-file');
      fileTag.style.display = 'flex';
      fileName.textContent = file.name;
      dropzone.querySelector('.dropzone-icon').style.display = 'none';
      dropzone.querySelector('.dropzone-text').textContent = '已选择文件';
      dropzone.querySelector('.dropzone-text').style.color = 'var(--accent)';
      dropzone.querySelector('.dropzone-hint').style.display = 'none';
      submitBtn.disabled = false;
    } else {
      selectedFile = null;
      dropzone.classList.remove('has-file');
      fileTag.style.display = 'none';
      dropzone.querySelector('.dropzone-icon').style.display = 'block';
      dropzone.querySelector('.dropzone-text').textContent = '拖拽 txt 文件到此处，或点击选择';
      dropzone.querySelector('.dropzone-text').style.color = '';
      dropzone.querySelector('.dropzone-hint').style.display = 'block';
      submitBtn.disabled = true;
    }
  }

  dropzone.addEventListener('click', e => {
    if (e.target.closest('.dropzone-remove')) return;
    fileInput.click();
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length) updateFileUI(fileInput.files[0]);
  });

  removeBtn.addEventListener('click', e => {
    e.stopPropagation();
    fileInput.value = '';
    updateFileUI(null);
  });

  dropzone.addEventListener('dragover', e => {
    e.preventDefault();
    dropzone.style.borderColor = 'var(--accent)';
    dropzone.style.background  = 'color-mix(in srgb, var(--accent) 8%, var(--bg-card))';
  });
  dropzone.addEventListener('dragleave', () => {
    dropzone.style.borderColor = '';
    dropzone.style.background  = '';
  });
  dropzone.addEventListener('drop', e => {
    e.preventDefault();
    dropzone.style.borderColor = '';
    dropzone.style.background  = '';
    const f = e.dataTransfer.files[0];
    if (f && f.name.endsWith('.txt')) {
      fileInput.files = e.dataTransfer.files;
      updateFileUI(f);
    } else {
      showToast('仅支持 .txt 格式文件', 'error');
    }
  });

  modalContent.querySelector('#uploadSubmitBtn')
    .addEventListener('click', () => handleUpload(selectedFile, currentMode));

  modalContent.querySelector('#modalCloseBtn')
    .addEventListener('click', closeModal);
}

async function handleUpload(file, mode) {
  const title    = modalContent.querySelector('#uploadTitle').value.trim();
  const category = modalContent.querySelector('#uploadCategory').value;
  const progress = modalContent.querySelector('#uploadProgress');

  let author;
  if (mode === 'own') {
    if (!state.currentUser) { showToast('请先登录', 'error'); return; }
    author = state.currentUser.username;
  } else {
    author = modalContent.querySelector('#uploadAuthor').value.trim();
    if (!author) { showToast('请输入作者', 'error'); return; }
  }

  if (!title)  { showToast('请输入小说标题', 'error'); return; }
  if (!file)   { showToast('请选择 txt 文件', 'error'); return; }

  const formData = new FormData();
  formData.append('title', title);
  formData.append('author', author);
  formData.append('category', category);
  formData.append('file', file);

  progress.style.display = 'block';
  progress.innerHTML = '<i class="fas fa-spinner fa-pulse"></i> 上传中...';

  try {
    const res = await fetch(API_BASE + '/novels/upload', { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || '上传失败');
    showToast(`《${data.novel.title}》上传成功！`, 'success');
    closeModal();
    renderHome();
  } catch (e) {
    progress.innerHTML = '';
    progress.style.display = 'none';
    showToast(e.message, 'error');
  }
}

// ==========================================
//  事件绑定
// ==========================================

// --- 上传按钮 ---
uploadBtn.addEventListener('click', showUploadModal);

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

// --- 返回章节列表 ---
backToChaptersBtn.addEventListener('click', () => {
  if (state.currentNovelId) {
    openDetail(state.currentNovelId);
  }
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

// --- 发表评论（详情页）---
commentSubmitBtn.addEventListener('click', async () => {
  if (!state.currentUser) { showToast('请先登录后再评论', 'error'); return; }
  const text = commentInput.value.trim();
  if (!text) { showToast('请输入评论内容', 'error'); return; }
  const result = await postComment(state.currentNovelId, 0, text);
  if (result) {
    commentInput.value = '';
    renderComments(state.currentNovelId);
    showToast('评论发表成功', 'success');
  }
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