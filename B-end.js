// ================================================================
//  墨书 - 智能小说阅读平台
// ================================================================

// ================================================================
//  Tailwind 配置
// ================================================================
tailwind.config = {
  theme: {
    extend: {
      colors: {
        primary: '#6366F1',
        secondary: '#EC4899',
        dark: '#1E293B',
        light: '#F8FAFC'
      }
    }
  }
};

// ================================================================
//  API 配置
// ================================================================
const API_BASE = 'http://localhost:3000/api';

// ================================================================
//  Toast 通知
// ================================================================
function showToast(msg, type = 'info') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast ' + type + ' show';
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), 3000);
}

// ================================================================
//  Token 管理
// ================================================================
function getToken() { return localStorage.getItem('token'); }
function getCurrentUser() {
  const u = localStorage.getItem('currentUser');
  return u ? JSON.parse(u) : null;
}

function saveAuth(user, token) {
  localStorage.setItem('token', token);
  localStorage.setItem('currentUser', JSON.stringify(user));
  updateUserUI();
}

function clearAuth() {
  localStorage.removeItem('token');
  localStorage.removeItem('currentUser');
  updateUserUI();
}

function updateUserUI() {
  const user = getCurrentUser();
  const loginBtn = document.getElementById('loginBtn');
  const logoutBtn = document.getElementById('logoutBtn');
  const userDisplay = document.getElementById('userDisplay');
  const nameSpan = document.getElementById('usernameDisplay');

  if (user) {
    loginBtn.classList.add('hidden');
    logoutBtn.classList.remove('hidden');
    userDisplay.classList.remove('hidden');
    nameSpan.textContent = user.username;
  } else {
    loginBtn.classList.remove('hidden');
    logoutBtn.classList.add('hidden');
    userDisplay.classList.add('hidden');
  }
}

// ================================================================
//  API 通用请求
// ================================================================
async function api(path, options = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = 'Bearer ' + token;

  const res = await fetch(API_BASE + path, { ...options, headers });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || '请求失败');
  return data;
}

// ================================================================
//  页面切换
// ================================================================
let currentPage = 'home';

function showPage(pageId) {
  document.querySelectorAll('section[id^="page-"]').forEach(s => s.classList.add('hidden'));
  const page = document.getElementById('page-' + pageId);
  if (page) page.classList.remove('hidden');

  document.querySelectorAll('.nav-link').forEach(a => a.classList.remove('active'));
  document.querySelectorAll(`.nav-link[data-page="${pageId}"]`).forEach(a => a.classList.add('active'));

  currentPage = pageId;
}

function goBack() { showPage('home'); }

document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const page = link.dataset.page;
    showPage(page);
    // 进入页面时刷新数据
    if (page === 'home') { loadNovels(); loadRanking(); loadRecommend(); }
    if (page === 'ranking') loadFullRanking('weekly');
    if (page === 'history') loadHistory();
  });
});

// ================================================================
//  模态框控制
// ================================================================
function openModal(id) { document.getElementById(id).classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

function switchAuthModal(type) {
  closeModal('loginModal');
  closeModal('registerModal');
  if (type === 'login') openModal('loginModal');
  else openModal('registerModal');
}

// 点击蒙层关闭
document.querySelectorAll('.fixed.inset-0').forEach(el => {
  el.addEventListener('click', e => {
    if (e.target === el) el.classList.add('hidden');
  });
});

// ================================================================
//  登录 / 注销
// ================================================================
document.getElementById('loginBtn').addEventListener('click', () => openModal('loginModal'));

document.getElementById('logoutBtn').addEventListener('click', () => {
  clearAuth();
  showToast('已退出登录', 'info');
  loadRecommend(); // 刷新推荐
  loadRanking();
});

// 登录表单
document.getElementById('loginForm').addEventListener('submit', async e => {
  e.preventDefault();
  const username = document.getElementById('loginUsername').value;
  const password = document.getElementById('loginPassword').value;

  try {
    const data = await api('/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
    saveAuth(data.user, data.token);
    closeModal('loginModal');
    showToast('欢迎回来，' + username + '！', 'success');
    document.getElementById('loginForm').reset();
    loadRecommend();
  } catch (err) {
    showToast(err.message, 'error');
  }
});

// 注册表单
document.getElementById('registerForm').addEventListener('submit', async e => {
  e.preventDefault();
  const username = document.getElementById('regUsername').value;
  const password = document.getElementById('regPassword').value;
  const password2 = document.getElementById('regPassword2').value;

  if (password !== password2) {
    showToast('两次密码输入不一致', 'error');
    return;
  }

  try {
    const data = await api('/register', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
    saveAuth(data.user, data.token);
    closeModal('registerModal');
    showToast('注册成功，欢迎你，' + username + '！', 'success');
    document.getElementById('registerForm').reset();
    loadRecommend();
  } catch (err) {
    showToast(err.message, 'error');
  }
});

// ================================================================
//  加载小说列表
// ================================================================
async function loadNovels() {
  const container = document.getElementById('novelList');
  const category = document.getElementById('categoryFilter').value;

  try {
    const url = '/novels?limit=50' + (category !== '全部' ? '&category=' + category : '');
    const data = await api(url);

    if (data.novels.length === 0) {
      container.innerHTML = '<div class="text-center py-12 text-gray-500"><i class="fa fa-book-open mr-2"></i>暂无小说，快去上传吧！</div>';
      return;
    }

    container.innerHTML = data.novels.map(n => `
      <div class="bg-white rounded-xl shadow-sm overflow-hidden flex hover:shadow-md transition cursor-pointer" onclick="readNovel(${n.id})">
        <img src="${n.cover}" class="w-24 h-32 object-cover flex-shrink-0" alt="${n.title}"
          onerror="this.src='https://via.placeholder.com/200x280/e2e8f0/94a3b8?text=${encodeURIComponent(n.title.substring(0,2))}'">
        <div class="p-4 flex-1 flex flex-col justify-between">
          <div>
            <h3 class="font-bold text-lg">${n.title}</h3>
            <div class="flex gap-2 text-xs text-gray-400 mt-1">
              <span class="bg-primary/10 text-primary px-2 py-0.5 rounded">${n.category}</span>
              <span>👤 ${n.author}</span>
            </div>
            <p class="text-sm text-gray-500 mt-2">
              <i class="fa fa-eye mr-1"></i>${n.views} 阅读
              <span class="mx-2">·</span>
              <i class="fa fa-calendar mr-1"></i>${n.created_at || ''}
            </p>
          </div>
          <div class="text-primary text-sm hover:underline">开始阅读 <i class="fa fa-arrow-right ml-1"></i></div>
        </div>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = '<div class="text-center py-12 text-red-400">加载失败：' + err.message + '</div>';
  }
}

// ================================================================
//  阅读小说
// ================================================================
async function readNovel(id) {
  try {
    // 先记录阅读
    await api('/novels/' + id + '/read', { method: 'POST' }).catch(() => {});

    const data = await api('/novels/' + id);

    document.getElementById('readTitle').textContent = data.title;
    document.getElementById('readMeta').textContent =
      data.category + ' | 作者：' + data.author + ' | 阅读量：' + data.views;

    let html = '';
    data.paragraphs.forEach(p => {
      const paraComments = p.comments || [];
      html += `
        <div class="relative">
          <p class="text-lg leading-8 my-6">${p.text}</p>
          <div class="flex items-center gap-3 mb-1">
            <span class="para-comment-btn" onclick="toggleComment(${data.id}, ${p.index})">
              <i class="fa fa-comment-o mr-1"></i>评论（${paraComments.length}）
            </span>
            <span class="text-xs text-gray-400">段落 ${p.index + 1}</span>
          </div>
          <div id="comment-box-${data.id}-${p.index}" class="comment-box">
            <div class="mb-2 max-h-40 overflow-y-auto text-sm space-y-2" id="comment-list-${data.id}-${p.index}">
              ${paraComments.map(c => `
                <div class="border-b border-gray-200 pb-2">
                  <div class="flex items-center gap-2 mb-0.5">
                    <span class="font-medium text-sm">${c.username}</span>
                    <span class="text-xs text-gray-400">${c.created_at || ''}</span>
                  </div>
                  <p class="text-gray-700 text-sm">${c.content}</p>
                </div>
              `).join('')}
              ${paraComments.length === 0 ? '<p class="text-gray-400 text-xs">暂无评论，来说点什么吧</p>' : ''}
            </div>
            <div class="flex gap-2">
              <input type="text" id="comment-input-${data.id}-${p.index}"
                placeholder="写下你的评论..." class="flex-1 text-sm px-3 py-1.5 border rounded-lg outline-none focus:border-primary">
              <button onclick="postComment(${data.id}, ${p.index})"
                class="bg-primary text-white px-3 py-1.5 rounded-lg text-sm hover:bg-primary/90 transition">发送</button>
            </div>
          </div>
        </div>
        <hr class="border-gray-100">
      `;
    });

    document.getElementById('readContent').innerHTML = html;
    showPage('read');
  } catch (err) {
    showToast('加载失败：' + err.message, 'error');
  }
}

// ================================================================
//  评论功能
// ================================================================
function toggleComment(novelId, paraId) {
  const box = document.getElementById(`comment-box-${novelId}-${paraId}`);
  if (box) box.classList.toggle('hidden');
}

async function postComment(novelId, paraId) {
  const user = getCurrentUser();
  if (!user) {
    showToast('请先登录后再评论', 'error');
    openModal('loginModal');
    return;
  }

  const input = document.getElementById(`comment-input-${novelId}-${paraId}`);
  const text = input.value.trim();
  if (!text) return;

  try {
    await api('/novels/' + novelId + '/comments', {
      method: 'POST',
      body: JSON.stringify({ paragraph_index: paraId, content: text })
    });
    input.value = '';
    showToast('评论成功', 'success');
    readNovel(novelId); // 刷新页面
  } catch (err) {
    showToast('评论失败：' + err.message, 'error');
  }
}

// ================================================================
//  排行榜
// ================================================================
let rankingType = 'weekly';

async function loadRanking() {
  try {
    const data = await api('/ranking?type=weekly');
    const side = document.getElementById('rankingSide');

    if (data.length === 0) {
      side.innerHTML = '<p class="text-sm text-gray-400">暂无数据</p>';
      return;
    }

    const medals = ['🥇', '🥈', '🥉'];
    side.innerHTML = data.slice(0, 5).map((n, i) => `
      <div class="ranking-item flex items-center gap-2 p-1.5 rounded-lg cursor-pointer" onclick="readNovel(${n.id})">
        <span class="w-6 h-6 rounded-full ${i < 3 ? 'bg-primary' : 'bg-gray-100'} text-white text-xs flex items-center justify-center flex-shrink-0 font-bold">
          ${i < 3 ? medals[i] : (i + 1)}
        </span>
        <p class="truncate flex-1 text-sm font-medium">${n.title}</p>
        <span class="text-xs text-gray-500 flex-shrink-0">${n.weekly_views || 0} 次</span>
      </div>
    `).join('');
  } catch {
    document.getElementById('rankingSide').innerHTML = '<p class="text-sm text-red-400">加载失败</p>';
  }
}

async function loadFullRanking(type) {
  rankingType = type;
  const container = document.getElementById('fullRanking');
  const weeklyBtn = document.getElementById('rankWeeklyBtn');
  const allBtn = document.getElementById('rankAllBtn');

  weeklyBtn.className = type === 'weekly'
    ? 'px-4 py-2 rounded-lg bg-primary text-white text-sm font-medium'
    : 'px-4 py-2 rounded-lg bg-gray-100 text-gray-600 text-sm font-medium hover:bg-gray-200';
  allBtn.className = type === 'all'
    ? 'px-4 py-2 rounded-lg bg-primary text-white text-sm font-medium'
    : 'px-4 py-2 rounded-lg bg-gray-100 text-gray-600 text-sm font-medium hover:bg-gray-200';

  try {
    const data = await api('/ranking?type=' + type);
    const medals = ['🥇', '🥈', '🥉'];

    if (data.length === 0) {
      container.innerHTML = '<div class="text-center py-12 text-gray-500">暂无数据</div>';
      return;
    }

    container.innerHTML = data.map((n, i) => {
      const viewCount = type === 'weekly' ? (n.weekly_views || 0) : n.views;
      return `
      <div class="ranking-item flex items-center p-3 border-b border-gray-100 last:border-0 cursor-pointer hover:bg-gray-50 rounded-lg"
        onclick="readNovel(${n.id})">
        <span class="w-8 h-8 rounded-full ${i < 3 ? 'bg-primary' : 'bg-gray-100'} text-white text-sm flex items-center justify-center mr-3 font-bold flex-shrink-0">
          ${i < 3 ? medals[i] : (i + 1)}
        </span>
        <div class="flex-1 min-w-0">
          <p class="font-medium truncate">${n.title}</p>
          <p class="text-sm text-gray-500">${n.category} · ${n.author}</p>
        </div>
        <span class="text-primary font-medium flex-shrink-0 ml-2">${viewCount} 阅读</span>
      </div>`;
    }).join('');
  } catch {
    container.innerHTML = '<div class="text-center py-12 text-red-400">加载失败</div>';
  }
}

function switchRanking(type) {
  loadFullRanking(type);
}

// ================================================================
//  智能推荐
// ================================================================
async function loadRecommend() {
  const container = document.getElementById('recommendSide');
  const user = getCurrentUser();

  if (!user) {
    container.innerHTML = `
      <p class="text-sm text-gray-400 mb-2">登录后获取个性化推荐</p>
      <button onclick="openModal('loginModal')" class="text-primary text-sm hover:underline">
        <i class="fa fa-sign-in mr-1"></i>立即登录
      </button>
    `;
    return;
  }

  try {
    const data = await api('/recommend');
    if (data.recommends.length === 0) {
      container.innerHTML = '<p class="text-sm text-gray-400">暂无更多推荐</p>';
      return;
    }

    container.innerHTML = `
      <p class="text-xs text-gray-400 mb-2">${data.reason}</p>
      ${data.recommends.map(n => `
        <div class="recommend-card p-2 rounded-lg cursor-pointer" onclick="readNovel(${n.id})">
          <p class="text-sm font-medium hover:text-primary transition truncate">${n.title}</p>
          <p class="text-xs text-gray-400">${n.category} · ${n.views} 阅读</p>
        </div>
      `).join('')}
    `;
  } catch {
    container.innerHTML = '<p class="text-sm text-red-400">推荐加载失败</p>';
  }
}

// ================================================================
//  阅读历史
// ================================================================
async function loadHistory() {
  const container = document.getElementById('historyList');
  const user = getCurrentUser();

  if (!user) {
    container.innerHTML = `
      <div class="text-center py-12">
        <i class="fa fa-history text-4xl text-gray-300 mb-3 block"></i>
        <p class="text-gray-500 mb-2">登录后查看阅读记录</p>
        <button onclick="openModal('loginModal')" class="text-primary hover:underline">
          <i class="fa fa-sign-in mr-1"></i>立即登录
        </button>
      </div>
    `;
    return;
  }

  try {
    const data = await api('/history');
    if (data.length === 0) {
      container.innerHTML = `
        <div class="text-center py-12 text-gray-400">
          <i class="fa fa-book-open text-4xl mb-3 block"></i>
          还没有阅读记录，去首页看看吧
        </div>
      `;
      return;
    }

    container.innerHTML = data.map(n => `
      <div class="flex items-center p-3 border-b border-gray-100 last:border-0 cursor-pointer hover:bg-gray-50 rounded-lg"
        onclick="readNovel(${n.id})">
        <img src="${n.cover}" class="w-12 h-16 object-cover rounded flex-shrink-0 mr-3" alt=""
          onerror="this.style.display='none'">
        <div class="flex-1 min-w-0">
          <p class="font-medium truncate">${n.title}</p>
          <p class="text-sm text-gray-400">${n.category}</p>
          <p class="text-xs text-gray-400">
            <i class="fa fa-clock-o mr-1"></i>上次阅读：${n.last_read_at || ''}
          </p>
        </div>
        <span class="text-primary text-sm hover:underline flex-shrink-0">
          继续阅读 <i class="fa fa-arrow-right ml-1"></i>
        </span>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = '<div class="text-center py-12 text-red-400">加载失败：' + err.message + '</div>';
  }
}

// ================================================================
//  上传小说
// ================================================================
document.getElementById('uploadForm').addEventListener('submit', async e => {
  e.preventDefault();

  const user = getCurrentUser();
  if (!user) {
    showToast('请先登录再上传小说', 'error');
    openModal('loginModal');
    return;
  }

  const title = document.getElementById('novelTitle').value;
  const category = document.getElementById('novelCategory').value;
  const cover = document.getElementById('novelCover').value;
  const content = document.getElementById('novelContent').value;

  try {
    await api('/novels', {
      method: 'POST',
      body: JSON.stringify({ title, category, cover, content })
    });

    document.getElementById('uploadForm').reset();
    showToast('小说《' + title + '》上传成功！', 'success');
    showPage('home');
    loadNovels();
  } catch (err) {
    showToast('上传失败：' + err.message, 'error');
  }
});

// ================================================================
//  Enter 键提交评论
// ================================================================
document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && e.target.id && e.target.id.startsWith('comment-input-')) {
    const parts = e.target.id.split('-');
    const novelId = parseInt(parts[2]);
    const paraId = parseInt(parts[3]);
    postComment(novelId, paraId);
  }
});

// ================================================================
//  事件绑定
// ================================================================
function bindEvents() {
  // Logo - 返回首页
  document.getElementById('logoLink').addEventListener('click', e => {
    e.preventDefault();
    showPage('home');
  });

  // 分类筛选
  document.getElementById('categoryFilter').addEventListener('change', loadNovels);

  // 返回按钮
  document.getElementById('goBackBtn').addEventListener('click', goBack);

  // 排行榜切换
  document.getElementById('rankWeeklyBtn').addEventListener('click', () => switchRanking('weekly'));
  document.getElementById('rankAllBtn').addEventListener('click', () => switchRanking('all'));

  // 关闭模态框
  document.getElementById('closeLoginBtn').addEventListener('click', () => closeModal('loginModal'));
  document.getElementById('closeRegisterBtn').addEventListener('click', () => closeModal('registerModal'));

  // 切换登录/注册
  document.getElementById('switchToRegister').addEventListener('click', e => {
    e.preventDefault();
    switchAuthModal('register');
  });
  document.getElementById('switchToLogin').addEventListener('click', e => {
    e.preventDefault();
    switchAuthModal('login');
  });
}

// ================================================================
//  初始化
// ================================================================
async function init() {
  bindEvents();
  updateUserUI();
  await Promise.all([
    loadNovels(),
    loadRanking(),
    loadRecommend()
  ]);
}

window.onload = init;
