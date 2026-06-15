# ==============================================================================
# 导入系统库
# ==============================================================================
import os      # 操作系统接口，用于文件和路径操作
import re      # 正则表达式，用于解析小说文本中的章节标题
import json    # JSON 编解码，用于读写评论和投票数据
import random  # 随机工具，用于随机推荐
import time    # 时间工具，用于生成时间戳
import threading  # 线程锁，用于保证文件操作的线程安全

# ==============================================================================
# 导入第三方库
# ==============================================================================
from flask import Flask, request, jsonify, send_from_directory  # Flask Web 框架
from flask_cors import CORS  # 跨域资源共享支持

# ==============================================================================
# 导入本地模块
# ==============================================================================
from cnn_recommender import recommend_novels, learn_from_browse  # 智能推荐引擎

# ==============================================================================
# Flask 应用初始化
# ==============================================================================
app = Flask(__name__, static_folder=None)  # 创建 Flask 应用实例，不自动挂载静态文件
CORS(app)  # 启用 CORS 跨域支持，允许前端跨域请求

# ─── 文件评论系统（基于 JSON 文件存储，无需数据库） ───
COMMENTS_DIR = None       # 评论存储目录，运行时初始化
COMMENTS_LOCK = threading.Lock()  # 评论文件操作线程锁，防止并发写入冲突

# ─── 评论系统内部函数 ───

def _init_comments_dir():
    """
    初始化评论存储目录

    # 在 backend/comments/ 目录下存储所有评论数据
    # 每个小说的评论存储在以小说 ID 命名的子目录中
    """
    global COMMENTS_DIR  # 声明使用全局变量
    if COMMENTS_DIR is None:  # 如果目录未初始化
        # 评论目录路径: backend/comments/
        COMMENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'comments')
        os.makedirs(COMMENTS_DIR, exist_ok=True)  # 创建目录（如果不存在）


def _next_cid():
    """
    生成下一个评论 ID（自增整数）

    # 从 _next_cid.txt 读取当前值，写入下一个值
    # 线程安全，使用 COMMENTS_LOCK 保护
    # 返回: 新的评论 ID（整数）
    """
    _init_comments_dir()  # 确保目录已初始化
    with COMMENTS_LOCK:  # 加锁，防止并发冲突
        p = os.path.join(COMMENTS_DIR, '_next_cid.txt')  # 计数器文件路径
        try:
            with open(p, 'r') as f:
                n = int(f.read().strip())  # 读取当前 ID 值
        except:
            n = 1  # 如果文件不存在或格式错误，从 1 开始
        with open(p, 'w') as f:
            f.write(str(n + 1))  # 写入下一个 ID 值
    return n  # 返回本次分配的 ID


def _comment_file(nid, ci, pi=-1):
    """
    获取评论文件的存储路径

    # 参数说明
    # nid: 小说 ID（如 f001）
    # ci: 章节索引
    # pi: 段落索引（-1 表示章节级评论）

    # 返回: 评论 JSON 文件的完整路径
    # 路径格式: backend/comments/{nid}/c{ci}_p{pi}.json
    """
    _init_comments_dir()  # 确保目录已初始化
    d = os.path.join(COMMENTS_DIR, nid)  # 小说专属评论目录
    os.makedirs(d, exist_ok=True)  # 创建小说评论目录
    return os.path.join(d, f'c{ci}_p{pi}.json')  # 返回评论文件路径


def _read_comments(nid, ci, pi=-1):
    """
    读取指定小说章节/段落的评论列表

    # 参数说明
    # nid: 小说 ID
    # ci: 章节索引
    # pi: 段落索引（-1 为章节级评论）

    # 返回: 评论列表（JSON 数组）
    """
    p = _comment_file(nid, ci, pi)  # 获取评论文件路径
    if not os.path.exists(p):  # 如果文件不存在
        return []  # 返回空列表
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return json.loads(f.read())  # 解析 JSON 并返回评论列表
    except:
        return []  # 解析失败则返回空列表


def _write_comments(nid, ci, pi, comments):
    """
    将评论列表写入文件（线程安全）

    # 参数说明
    # nid: 小说 ID
    # ci: 章节索引
    # pi: 段落索引
    # comments: 要保存的评论列表
    """
    with COMMENTS_LOCK:  # 加锁，防止并发写入冲突
        p = _comment_file(nid, ci, pi)  # 获取评论文件路径
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(comments, f, ensure_ascii=False, indent=2)  # 写入 JSON 文件


def _load_votes():
    """
    加载所有投票数据

    # 投票数据存储在 _votes.json 中
    # 格式: { "评论ID": {"up": [用户ID列表], "down": [用户ID列表]} }

    # 返回: 投票数据字典
    """
    _init_comments_dir()  # 确保目录已初始化
    p = os.path.join(COMMENTS_DIR, '_votes.json')  # 投票数据文件路径
    if not os.path.exists(p):  # 如果文件不存在
        return {}  # 返回空字典
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return json.loads(f.read())  # 解析 JSON 并返回投票数据
    except:
        return {}  # 解析失败则返回空字典


def _save_votes(votes):
    """
    保存投票数据到文件（线程安全）

    # 参数说明
    # votes: 投票数据字典
    """
    with COMMENTS_LOCK:  # 加锁，防止并发写入冲突
        _init_comments_dir()  # 确保目录已初始化
        p = os.path.join(COMMENTS_DIR, '_votes.json')  # 投票数据文件路径
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(votes, f, ensure_ascii=False, indent=2)  # 写入 JSON 文件


def _find_and_reply(comments, parent_id, reply):
    """
    在评论树中递归查找父评论并追加回复

    # 参数说明
    # comments: 评论列表（可能包含嵌套回复）
    # parent_id: 要回复的父评论 ID
    # reply: 回复内容字典

    # 返回: bool — 是否找到父评论并成功追加
    """
    for c in comments:  # 遍历当前级别的评论
        if c['id'] == parent_id:  # 找到父评论
            c.setdefault('replies', []).append(reply)  # 在父评论的 replies 中追加回复
            return True  # 返回成功
        # 如果当前评论有子回复，递归查找
        if 'replies' in c and _find_and_reply(c['replies'], parent_id, reply):
            return True  # 在子回复中找到并追加成功
    return False  # 未找到父评论


def _comment_to_dict(c):
    """
    将评论对象转换为包含投票统计的字典

    # 从 _votes.json 中读取该评论的点赞/点踩数据
    # 组装为前端可直接使用的格式

    # 参数说明
    # c: 原始评论字典

    # 返回: 包含投票计数的评论字典
    """
    votes = _load_votes()  # 加载所有投票数据
    cid = str(c['id'])  # 将评论 ID 转为字符串（JSON 键）
    uv = votes.get(cid, {})  # 获取该评论的投票数据
    up = uv.get('up', [])    # 获取点赞用户列表
    down = uv.get('down', [])  # 获取点踩用户列表
    return {
        'id': c['id'],               # 评论 ID
        'novel_id': c['novel_id'],   # 所属小说 ID
        'chapter_index': c['chapter_index'],      # 章节索引
        'paragraph_index': c['paragraph_index'],  # 段落索引
        'user_id': c['user_id'],     # 评论者用户 ID
        'username': c['username'],   # 评论者用户名
        'text': c['text'],           # 评论内容
        'parent_id': c.get('parent_id'),  # 父评论 ID（用于回复链）
        'created_at': c['created_at'],    # 创建时间戳
        'upvotes': len(up),          # 点赞数
        'downvotes': len(down),      # 点踩数
        'replies': [_comment_to_dict(r) for r in c.get('replies', [])]  # 递归处理回复
    }

# ==============================================================================
# 目录路径配置
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # backend/ 目录路径
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), 'frontend')  # frontend/ 前端目录
NOVEL_LIB_DIR = os.path.join(os.path.dirname(BASE_DIR), '小说库')     # 小说库根目录
ACCOUNTS_DIR = os.path.join(BASE_DIR, 'accounts')  # 用户账号存储目录
os.makedirs(ACCOUNTS_DIR, exist_ok=True)  # 确保账号目录存在
ID_COUNTER = os.path.join(ACCOUNTS_DIR, '_next_id.txt')  # 用户 ID 计数器文件

# ==============================================================================
# 分类映射表（连接文件系统目录名与前端显示名）
# ==============================================================================
# 文件系统中的文件夹名称 → 前端显示的分类名称
CATEGORY_MAP = {'玄幻类':'玄幻','仙侠类':'仙侠','都市类':'都市','历史类':'历史',
                '科幻类':'科幻','灵异类':'悬疑','幻想类':'幻想','军事类':'军事','网游类':'网游'}
# 每种分类对应的显示图标（Emoji）
CATEGORY_EMOJI = {'玄幻':'⚔️','仙侠':'🌿','都市':'🏙️','历史':'🏯',
                  '科幻':'🚀','悬疑':'🔔','幻想':'🐉','军事':'🪖','网游':'🎮'}
# 前端分类名称 → 文件夹名称（反向映射）
CATEGORY_FOLDER_MAP = {v:k for k,v in CATEGORY_MAP.items()}

# ==============================================================================
# 小说库扫描与数据解析
# ==============================================================================

def parse_info_txt(fp):
    """
    解析小说 info.txt 元数据文件

    # info.txt 格式（每行 键:值）:
    #   标题: 凡人修仙传
    #   作者: 忘语
    #   分类: 仙侠
    #   封面: 🌿

    # 参数说明
    # fp: info.txt 文件的完整路径

    # 返回: dict — 解析后的键值对字典
    """
    info = {}  # 初始化信息字典
    if os.path.exists(fp):  # 如果文件存在
        with open(fp, 'r', encoding='utf-8') as f:  # 以 UTF-8 编码打开
            for line in f:  # 逐行读取
                if ':' in line:  # 如果行中包含冒号分隔符
                    k, v = line.strip().split(':', 1)  # 按冒号分割为键和值
                    info[k.strip()] = v.strip()  # 去除首尾空格后存入字典
    return info  # 返回解析结果


def _extract_description(txt_path, author, category):
    """
    从小说正文中提取开头一段作为简介

    # 尝试多种编码（utf-8, gbk, utf-16）读取前 500 字符
    # 过滤标题行和过短行，取第一段有意义的文字

    # 参数说明
    # txt_path: 小说文本文件路径
    # author: 作者名（备用）
    # category: 分类名（备用）

    # 返回: str — 提取的简介文本
    """
    text = None  # 初始化文本变量
    # 尝试多种编码读取文件前 500 个字符
    for enc in ['utf-8', 'gbk', 'utf-16']:
        try:
            with open(txt_path, 'r', encoding=enc) as f:
                text = f.read(500)  # 读取前 500 字符
            break  # 成功读取则跳出循环
        except:
            continue  # 编码错误则尝试下一种
    if text is None:  # 所有编码都失败
        return f'《{os.path.basename(txt_path).replace(".txt","")}》·{category}类作品'
    # 按行分割，去除空行和首尾空格
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    # 过滤掉纯数字、太短的标题行（如 "第一章"）
    meaningful = [l for l in lines if len(l) > 6 and not l.startswith('第')]
    if meaningful:  # 如果有有意义的行
        snippet = meaningful[0][:120]  # 取第一段有意义文字的前 120 字符
        return snippet  # 返回简介
    # 如果没有找到合适的描述，用标题+分类作为备用
    return f'《{os.path.basename(txt_path).replace(".txt","")}》·{category}类作品'


def scan_novel_library():
    """
    扫描小说库目录，构建全部小说的元数据列表

    # 遍历 '小说库/' 下的每个分类文件夹
    # 再遍历每个分类下的每本小说文件夹
    # 解析 info.txt 和小说正文，构建结构化数据

    # 返回: list[dict] — 所有小说的元数据列表
    """
    novels = []  # 初始化小说列表
    idx = 0      # 小说编号计数器
    if not os.path.isdir(NOVEL_LIB_DIR):  # 如果小说库目录不存在
        return novels  # 返回空列表
    # 遍历小说库中的分类文件夹
    for fn in sorted(os.listdir(NOVEL_LIB_DIR)):
        fp = os.path.join(NOVEL_LIB_DIR, fn)  # 分类文件夹路径
        if not os.path.isdir(fp):  # 如果不是目录则跳过
            continue
        cat = CATEGORY_MAP.get(fn, fn.replace('类', ''))  # 文件夹名 → 分类名
        # 遍历该分类下的每本小说文件夹
        for nd in sorted(os.listdir(fp)):
            np = os.path.join(fp, nd)  # 小说文件夹路径
            if not os.path.isdir(np):  # 如果不是目录则跳过
                continue
            info = parse_info_txt(os.path.join(np, "info.txt"))  # 解析 info.txt
            title = info.get('标题', nd)    # 获取小说标题，没有则用文件夹名
            author = info.get('作者', '未知')  # 获取作者，没有则标记为"未知"
            emoji = info.get('封面', CATEGORY_EMOJI.get(cat, '📖'))  # 获取封面图标
            # 查找小说正文 txt 文件（排除 info.txt）
            txt = None
            for f2 in os.listdir(np):
                if f2.endswith('.txt') and f2 != 'info.txt':
                    txt = os.path.join(np, f2)  # 找到正文文件
                    break
            if not txt:  # 如果没有找到正文文件
                continue  # 跳过这本小说
            idx += 1  # 编号递增
            fs = os.path.getsize(txt)  # 获取文件大小（字节）
            # 从小说正文提取开头一小段作为简介
            desc = _extract_description(txt, author, cat)
            # 构建小说元数据字典
            novels.append({
                "id": f"f{idx:03d}",          # 小说 ID（如 f001）
                "title": title,                # 小说标题
                "author": author,              # 作者
                "category": cat,               # 分类
                "rating": round(min(9.5, 7.0 + (fs / 20000000) * 2.5), 1),  # 评分（基于文件大小估算）
                "hot": min(15000, 3000 + fs // 1000),  # 热度（基于文件大小估算）
                "desc": desc,                  # 简介
                "cover": emoji,                # 封面图标
                "filepath": txt,               # 文件路径（内部使用）
                "filesize": fs                 # 文件大小（内部使用）
            })
    return novels  # 返回完整的小说元数据列表

# ==============================================================================
# 全局小说数据
# ==============================================================================
ALL_NOVELS = scan_novel_library()  # 启动时扫描一次，构建全局小说列表


def get_novel_by_id(nid):
    """
    根据小说 ID 查找小说对象

    # 参数说明
    # nid: 小说 ID（如 "f001"）

    # 返回: dict or None — 找到返回小说元数据，否则返回 None
    """
    for n in ALL_NOVELS:  # 遍历全局小说列表
        if n['id'] == nid:  # 匹配 ID
            return n  # 返回找到的小说
    return None  # 未找到


def get_novel_filepath(novel):
    """
    获取小说文本文件的路径

    # 优先使用缓存的 filepath 字段
    # 如果文件不存在，则按分类+标题重新查找

    # 参数说明
    # novel: 小说元数据字典

    # 返回: str or None — 文件路径
    """
    if novel.get('filepath') and os.path.exists(novel['filepath']):  # 缓存路径有效
        return novel['filepath']  # 直接返回缓存路径
    # 缓存失效，重新按分类目录查找
    for fn, wc in CATEGORY_MAP.items():  # 遍历分类文件夹映射
        if wc == novel['category']:  # 匹配分类
            fp = os.path.join(NOVEL_LIB_DIR, fn)  # 分类文件夹路径
            if os.path.isdir(fp):  # 如果分类文件夹存在
                for f in os.listdir(fp):  # 遍历分类下的文件
                    if novel['title'] in f:  # 匹配标题
                        return os.path.join(fp, f)  # 返回匹配的文件路径
    return None  # 未找到


def read_novel_file(fp):
    """
    读取小说文本文件并解析为章节列表

    # 自动检测编码（utf-8 → gbk → utf-16）
    # 使用正则表达式匹配章节标题（如 "第一章"、"第001回"）
    # 每章截取前 300 行、最多 8000 字符

    # 参数说明
    # fp: 小说文件路径

    # 返回: list[dict] or None — 章节列表，每章包含 title 和 content
    """
    if not os.path.exists(fp):  # 文件不存在
        return None  # 返回 None
    text = None  # 初始化文本变量
    # 尝试多种编码读取文件
    for enc in ['utf-8', 'gbk', 'utf-16']:
        try:
            with open(fp, 'r', encoding=enc) as f:
                text = f.read()  # 读取全部文本
            break  # 成功则跳出
        except:
            continue  # 失败则尝试下一种编码
    if text is None:  # 所有编码都失败
        return None  # 返回 None
    # 正则表达式：匹配 "第X章"、"第X回"、"第X节" 等章节标题
    pat = re.compile(r'(第[一二三四五六七八九十百千零\d]+[章回节部卷])')
    parts = pat.split(text)  # 按章节标题分割文本
    chapters = []  # 初始化章节列表
    if len(parts) > 1:  # 如果成功识别到章节标题
        cur = "序章"  # 开头的非章节内容标记为"序章"
        for i, p in enumerate(parts):
            if re.match(r'第[^第]+$', p):  # 如果匹配到章节标题
                cur = p  # 更新当前章节名
            elif p.strip():  # 如果是正文内容
                ps = [x.strip() for x in p.split('\n') if x.strip()]  # 按行分割并去空
                chapters.append({
                    'title': cur,  # 章节标题
                    'content': '\n'.join(ps[:300])[:8000]  # 取前 300 行，截取 8000 字符
                })
                cur = "后续"  # 后续未匹配的内容标记为"后续"
    else:
        # 没有章节标题的情况：按每 80 行自动分章
        ps = [x.strip() for x in text.split('\n') if x.strip()]  # 按行分割
        for i in range(0, min(len(ps), 2000), 80):  # 每 80 行为一章
            chapters.append({
                'title': f'第{len(chapters) + 1}章',  # 自动生成章节名
                'content': '\n'.join(ps[i:i + 80][:300])[:8000]  # 取内容
            })
    return chapters if chapters else None  # 返回章节列表


# ==============================================================================
# 文件账号系统（基于 txt 文件存储，无需数据库）
# ==============================================================================

def _next_id():
    """
    生成下一个用户 ID（自增整数）

    # 从 accounts/_next_id.txt 读写
    # 返回: 新的用户 ID（整数）
    """
    try:
        with open(ID_COUNTER, 'r') as f:
            n = int(f.read().strip())  # 读取当前 ID
    except:
        n = 1  # 文件不存在则从 1 开始
    with open(ID_COUNTER, 'w') as f:
        f.write(str(n + 1))  # 写入下一个 ID
    return n  # 返回当前分配的 ID


def _read_user(uid):
    """
    读取用户信息

    # 用户信息存储在 accounts/{uid}/info.txt

    # 参数说明
    # uid: 用户 ID（整数）

    # 返回: dict or None — 用户信息字典
    """
    p = os.path.join(ACCOUNTS_DIR, str(uid), 'info.txt')  # 用户信息文件路径
    if not os.path.exists(p):  # 文件不存在
        return None  # 返回 None
    info = {}  # 初始化信息字典
    with open(p, 'r', encoding='utf-8') as f:  # 打开文件
        for line in f:  # 逐行读取
            if ':' in line:  # 包含冒号分隔符
                k, v = line.strip().split(':', 1)  # 分割键和值
                info[k.strip()] = v.strip()  # 存入字典
    return info  # 返回用户信息


def _write_user(uid, un, pw, pr):
    """
    写入用户信息

    # 在 accounts/{uid}/ 目录下创建 info.txt

    # 参数说明
    # uid: 用户 ID
    # un: 用户名
    # pw: 密码
    # pr: 偏好分类列表
    """
    d = os.path.join(ACCOUNTS_DIR, str(uid))  # 用户目录
    os.makedirs(d, exist_ok=True)  # 创建用户目录
    with open(os.path.join(d, 'info.txt'), 'w', encoding='utf-8') as f:  # 写入 info.txt
        f.write(f"用户名: {un}\n密码: {pw}\n偏好: {','.join(pr)}\n")


def _read_history(uid):
    """
    读取用户的浏览历史

    # 浏览历史存储在 accounts/{uid}/history.txt
    # 每行格式: 小说ID|时间戳

    # 参数说明
    # uid: 用户 ID

    # 返回: list[dict] — 浏览记录列表
    """
    p = os.path.join(ACCOUNTS_DIR, str(uid), 'history.txt')  # 历史文件路径
    if not os.path.exists(p):  # 文件不存在
        return []  # 返回空列表
    rs = []  # 初始化记录列表
    with open(p, 'r', encoding='utf-8') as f:  # 打开文件
        for line in f:  # 逐行读取
            line = line.strip()  # 去除首尾空格
            if line:  # 非空行
                parts = line.rsplit('|', 1)  # 按管道符分割
                rs.append({
                    'novel_id': parts[0],  # 小说 ID
                    'time': parts[1] if len(parts) > 1 else ''  # 浏览时间
                })
    return rs  # 返回浏览记录


def _write_history(uid, rs):
    """
    写入浏览历史到文件

    # 参数说明
    # uid: 用户 ID
    # rs: 浏览记录列表
    """
    d = os.path.join(ACCOUNTS_DIR, str(uid))  # 用户目录
    os.makedirs(d, exist_ok=True)  # 确保目录存在
    with open(os.path.join(d, 'history.txt'), 'w', encoding='utf-8') as f:  # 写入文件
        for r in rs:
            f.write(f"{r['novel_id']}|{r['time']}\n")  # 每行: 小说ID|时间戳


def _add_history(uid, nid):
    """
    添加一条浏览历史记录

    # 去重：如果该小说已存在历史中，先移除旧记录
    # 最新浏览的插入到最前面
    # 最多保留 50 条记录

    # 参数说明
    # uid: 用户 ID
    # nid: 小说 ID

    # 返回: list[dict] — 更新后的浏览记录
    """
    rs = _read_history(uid)  # 读取现有历史
    rs = [r for r in rs if r['novel_id'] != nid]  # 去重（移除旧记录）
    # 将新记录插入最前面
    rs.insert(0, {'novel_id': nid, 'time': str(int(__import__('time').time()))})
    _write_history(uid, rs[:50])  # 只保留最近 50 条
    return rs  # 返回更新后的记录


def _user_exists(un):
    """
    检查用户名是否已存在

    # 遍历 accounts/ 下所有数字命名的目录

    # 参数说明
    # un: 要检查的用户名

    # 返回: bool — 是否存在
    """
    for d in os.listdir(ACCOUNTS_DIR):  # 遍历账号目录
        if d == '_next_id.txt' or not d.isdigit():  # 跳过非用户目录
            continue
        info = _read_user(d)  # 读取该目录的用户信息
        if info and info.get('用户名') == un:  # 如果用户名匹配
            return True  # 已存在
    return False  # 不存在


def _find_user(un):
    """
    根据用户名查找用户

    # 遍历 accounts/ 下所有用户目录
    # 匹配用户名

    # 参数说明
    # un: 要查找的用户名

    # 返回: tuple (uid, info) or (None, None)
    """
    for d in os.listdir(ACCOUNTS_DIR):  # 遍历账号目录
        if d == '_next_id.txt' or not d.isdigit():  # 跳过非用户目录
            continue
        info = _read_user(d)  # 读取用户信息
        if info and info.get('用户名') == un:  # 用户名匹配
            return int(d), info  # 返回用户 ID 和信息
    return None, None  # 未找到

# ==============================================================================
# 前端静态文件服务
# ==============================================================================

@app.route('/')
def serve_index():
    """提供前端首页 index.html"""
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_frontend(filename):
    """
    提供前端静态文件（CSS, JS, 图片等）

    # 所有非 API 路径的请求都会到这里
    # 从 frontend/ 目录中查找对应文件
    """
    return send_from_directory(FRONTEND_DIR, filename)


# ==============================================================================
# 小说内容 API
# ==============================================================================

@app.route('/api/novels/<nid>/content/<int:ci>', methods=['GET'])
def get_chapter_content(nid, ci):
    """
    获取指定小说的某一章节内容

    # 参数说明
    # nid: 小说 ID（如 f001）
    # ci: 章节索引（从 0 开始）

    # 返回: JSON — 章节标题、正文、总章节数
    """
    novel = get_novel_by_id(nid)  # 查找小说
    if not novel:
        return jsonify({'error': '小说不存在'}), 404
    fp = get_novel_filepath(novel)  # 获取小说文件路径
    if not fp:
        return jsonify({'error': '暂无文本文件'}), 404
    chs = read_novel_file(fp)  # 解析章节列表
    if not chs or ci < 0 or ci >= len(chs):  # 章节索引越界
        return jsonify({'error': '章节不存在'}), 404
    ch = chs[ci]  # 获取指定章节
    return jsonify({
        'novel_id': nid,
        'chapter_index': ci,
        'chapter_title': ch['title'],
        'content': ch['content'],
        'total_chapters': len(chs)  # 总章节数
    })


@app.route('/api/novels/<nid>/file-info', methods=['GET'])
def get_novel_file_info(nid):
    """
    获取小说的文件信息

    # 返回文件是否存在、文件名、文件大小、总章节数
    # 前端用来判断是否需要显示"阅读"按钮
    """
    novel = get_novel_by_id(nid)  # 查找小说
    if not novel:
        return jsonify({'error': '小说不存在'}), 404
    fp = get_novel_filepath(novel)  # 获取文件路径
    if not fp or not os.path.exists(fp):
        return jsonify({'has_file': False})  # 文件不存在
    chs = read_novel_file(fp)  # 解析章节
    return jsonify({
        'has_file': True,
        'file_name': os.path.basename(fp),  # 文件名
        'file_size': os.path.getsize(fp),   # 文件大小（字节）
        'total_chapters': len(chs) if chs else 0  # 总章节数
    })

# ==============================================================================
# 用户账号 API
# ==============================================================================

@app.route('/api/register', methods=['POST'])
def register():
    """
    用户注册接口

    # 请求体格式 (JSON):
    #   { "username": "用户名", "password": "密码", "preferences": ["玄幻", "仙侠"] }

    # 校验规则:
    #   - 用户名至少 2 个字符
    #   - 密码至少 3 个字符
    #   - 至少选择 2 个偏好分类
    #   - 用户名不能重复

    # 返回: 201 — 注册成功，返回用户信息
    """
    data = request.get_json()  # 解析 JSON 请求体
    un = data.get('username', '').strip()   # 用户名
    pw = data.get('password', '').strip()   # 密码
    pr = data.get('preferences', [])        # 偏好分类列表
    # 参数校验
    if not un or len(un) < 2:
        return jsonify({'error': '用户名至少2个字符'}), 400
    if not pw or len(pw) < 3:
        return jsonify({'error': '密码至少3个字符'}), 400
    if len(pr) < 2:
        return jsonify({'error': '请至少选择2个偏好类型'}), 400
    if _user_exists(un):  # 检查用户名是否已存在
        return jsonify({'error': '用户已存在'}), 400
    uid = _next_id()  # 分配新用户 ID
    _write_user(uid, un, pw, pr)  # 保存用户信息
    return jsonify({'id': uid, 'username': un, 'preferences': pr}), 201


@app.route('/api/login', methods=['POST'])
def login():
    """
    用户登录接口

    # 请求体格式 (JSON):
    #   { "username": "用户名", "password": "密码" }

    # 返回: 200 — 登录成功，返回用户信息和偏好
    """
    data = request.get_json()  # 解析 JSON 请求体
    un = data.get('username', '').strip()  # 用户名
    pw = data.get('password', '').strip()  # 密码
    uid, info = _find_user(un)  # 查找用户
    if not info or info.get('密码') != pw:  # 用户名或密码错误
        return jsonify({'error': '用户名或密码错误'}), 401
    pr = [p.strip() for p in info.get('偏好', '').split(',') if p.strip()]  # 解析偏好列表
    return jsonify({'id': uid, 'username': un, 'preferences': pr})


@app.route('/api/user/<int:uid>', methods=['GET'])
def get_user(uid):
    """
    获取用户信息

    # 参数说明
    # uid: 用户 ID（路径参数）

    # 返回: 200 — 用户信息（含偏好分类）
    """
    info = _read_user(uid)  # 读取用户信息
    if not info:  # 用户不存在
        return jsonify({'error': '用户不存在'}), 404
    pr = [p.strip() for p in info.get('偏好', '').split(',') if p.strip()]  # 解析偏好
    return jsonify({'id': uid, 'username': info.get('用户名', ''), 'preferences': pr})


@app.route('/api/user/<int:uid>/preferences', methods=['PUT'])
def update_preferences(uid):
    """
    更新用户的偏好分类

    # 请求体格式 (JSON):
    #   { "preferences": ["玄幻", "仙侠", "都市"] }

    # 参数说明
    # uid: 用户 ID

    # 返回: 200 — 更新后的偏好列表
    """
    info = _read_user(uid)  # 读取用户信息
    if not info:  # 用户不存在
        return jsonify({'error': '用户不存在'}), 404
    data = request.get_json()  # 解析请求体
    pr = data.get('preferences', [])  # 新的偏好列表
    if len(pr) < 2:  # 至少选 2 个
        return jsonify({'error': '至少选择2个偏好'}), 400
    _write_user(uid, info.get('用户名', ''), info.get('密码', ''), pr)  # 更新用户信息
    return jsonify({'preferences': pr})

# ==============================================================================
# 小说列表与详情 API
# ==============================================================================

@app.route('/api/novels', methods=['GET'])
def get_novels():
    """
    获取小说列表（支持分类筛选和排序）

    # 查询参数:
    #   category: 分类名称（默认 "all" 表示全部）
    #   sort: 排序方式 — hot(热度), rating(评分), new(最新)

    # 返回: JSON 数组 — 每本小说的元数据（排除内部字段）
    """
    cat = request.args.get('category', 'all')   # 分类筛选
    sort = request.args.get('sort', 'hot')       # 排序方式
    ns = ALL_NOVELS[:]  # 复制全局小说列表
    # 分类筛选
    if cat != 'all':
        ns = [n for n in ns if n['category'] == cat]
    # 排序
    if sort == 'hot':      # 按热度降序
        ns.sort(key=lambda x: x['hot'], reverse=True)
    elif sort == 'rating': # 按评分降序
        ns.sort(key=lambda x: x['rating'], reverse=True)
    elif sort == 'new':    # 按文件大小（≈内容量）降序
        ns.sort(key=lambda x: x.get('filesize', 0), reverse=True)
    # 排除内部字段（filepath, filesize）后返回
    return jsonify([{k: v for k, v in n.items() if k not in ('filepath', 'filesize')} for n in ns])


@app.route('/api/novels/<nid>', methods=['GET'])
def get_novel_detail(nid):
    """
    获取小说详情（含章节列表）

    # 参数说明
    # nid: 小说 ID（如 f001）

    # 返回: JSON — 小说元数据 + chapters 章节标题列表
    """
    novel = get_novel_by_id(nid)  # 查找小说
    if not novel:
        return jsonify({'error': '小说不存在'}), 404
    item = {k: v for k, v in novel.items() if k not in ('filepath', 'filesize')}  # 排除内部字段
    # 如果还没有章节列表，从文件解析
    if 'chapters' not in item or not item['chapters']:
        fp = get_novel_filepath(novel)  # 获取文件路径
        if fp:
            chs = read_novel_file(fp)  # 解析章节
            item['chapters'] = [c['title'] for c in chs] if chs else ['第一章']
        else:
            item['chapters'] = ['第一章']
    return jsonify(item)


# ==============================================================================
# 浏览记录与历史 API
# ==============================================================================

@app.route('/api/browse', methods=['POST'])
def record_browse():
    """
    记录用户浏览行为（同时触发智能推荐的在线学习）

    # 请求体格式 (JSON):
    #   { "user_id": 1, "novel_id": "f001" }

    # 业务流程:
    #   1. 添加浏览历史
    #   2. 触发推荐引擎的在线学习（learn_from_browse）
    #      每浏览 10 本不同的书，推荐模型自动重新聚类
    """
    data = request.get_json()
    uid = data.get('user_id')   # 用户 ID
    nid = data.get('novel_id')  # 小说 ID
    if not uid or not nid:  # 缺少参数
        return jsonify({'error': '缺少参数'}), 400
    if not _read_user(uid):  # 用户不存在
        return jsonify({'error': '用户不存在'}), 404
    rs = _add_history(uid, nid)  # 添加浏览历史
    try:
        learn_from_browse(uid, nid, ALL_NOVELS, rs)  # 触发在线学习
    except:
        pass  # 在线学习失败不影响浏览记录
    return jsonify({'status': 'ok'})


@app.route('/api/history/<int:uid>', methods=['GET'])
def get_history(uid):
    """
    获取用户的浏览历史

    # 参数说明
    # uid: 用户 ID

    # 返回: JSON 数组 — 去重后的历史小说列表（含浏览时间）
    """
    if not _read_user(uid):  # 用户不存在
        return jsonify({'error': '用户不存在'}), 404
    records = _read_history(uid)  # 读取历史记录
    seen = set()  # 用于去重
    novels = []   # 结果列表
    for r in records:
        if r['novel_id'] not in seen:  # 去重
            seen.add(r['novel_id'])
            n = get_novel_by_id(r['novel_id'])  # 获取小说信息
            if n:
                item = {k: v for k, v in n.items() if k not in ('filepath', 'filesize')}
                item['browse_time'] = r['time']  # 添加浏览时间
                novels.append(item)
    return jsonify(novels)


@app.route('/api/history/<int:uid>/delete', methods=['POST'])
def delete_history(uid):
    """
    删除单条浏览历史

    # 请求体格式 (JSON):
    #   { "novel_id": "f001" }
    """
    if not _read_user(uid):
        return jsonify({'error': '用户不存在'}), 404
    data = request.get_json()
    nid = data.get('novel_id', '')
    rs = [r for r in _read_history(uid) if r['novel_id'] != nid]  # 移除指定记录
    _write_history(uid, rs)
    return jsonify({'status': 'ok'})


@app.route('/api/history/<int:uid>/clear', methods=['POST'])
def clear_history(uid):
    """清空用户的全部浏览历史"""
    if not _read_user(uid):
        return jsonify({'error': '用户不存在'}), 404
    _write_history(uid, [])  # 写入空列表
    return jsonify({'status': 'ok'})


# ==============================================================================
# 智能推荐 API（核心功能）
# ==============================================================================

@app.route('/api/recommend/random', methods=['GET'])
def random_recommend():
    """
    随机推荐（用于未登录用户的首页展示）

    # 从全部小说中随机抽取 2 本
    # 返回: JSON 数组
    """
    selected = random.sample(ALL_NOVELS, min(2, len(ALL_NOVELS)))  # 随机抽样
    return jsonify([{k: v for k, v in n.items() if k not in ('filepath', 'filesize')} for n in selected])


@app.route('/api/recommend/<int:uid>', methods=['GET'])
def recommend(uid):
    """
    智能推荐（基于 CNN 聚类 + 协同过滤的个性化推送）

    # 参数说明
    # uid: 用户 ID

    # 业务流程:
    #   1. 读取用户信息和偏好分类
    #   2. 调用 cnn_recommender.recommend_novels()
    #   3. 返回个性化排序的 Top-12 推荐结果

    # 智能推送的完整流程请参见 cnn_recommender.py 头部文档
    """
    info = _read_user(uid)  # 读取用户信息
    if not info:
        return jsonify({'error': '用户不存在'}), 404
    # 解析偏好分类列表
    pr = [p.strip() for p in info.get('偏好', '').split(',') if p.strip()]
    # 调用推荐引擎进行智能推送
    rec = recommend_novels(uid, ALL_NOVELS, _read_history(uid), pr)
    # 排除内部字段后返回
    return jsonify([{k: v for k, v in n.items() if k not in ('filepath', 'filesize')} for n in rec])

# ==============================================================================
# 小说上传 API
# ==============================================================================

@app.route('/api/novels/upload', methods=['POST'])
def upload_novel():
    """
    上传小说（支持表单数据）

    # 请求格式 (multipart/form-data):
    #   title: 小说标题
    #   author: 作者
    #   category: 分类名称
    #   file: .txt 文件

    # 业务流程:
    #   1. 校验参数
    #   2. 在对应分类目录下创建小说文件夹
    #   3. 保存 txt 文件和 info.txt 元数据
    #   4. 如果上传失败，自动回滚删除已创建的目录
    """
    title = request.form.get('title', '').strip()       # 小说标题
    author = request.form.get('author', '').strip()     # 作者
    category = request.form.get('category', '').strip() # 分类
    file = request.files.get('file')                    # 上传的文件
    # ── 参数校验 ──
    if not title:
        return jsonify({'error': '请输入小说标题'}), 400
    if not author:
        return jsonify({'error': '请输入作者'}), 400
    if not category:
        return jsonify({'error': '请选择分类'}), 400
    if not file or not file.filename.endswith('.txt'):
        return jsonify({'error': '请上传txt文件'}), 400
    # ── 创建目录结构 ──
    fn = CATEGORY_FOLDER_MAP.get(category, category + '类')  # 分类文件夹名
    cd = os.path.join(NOVEL_LIB_DIR, fn)  # 分类目录
    os.makedirs(cd, exist_ok=True)
    nd = os.path.join(cd, title)  # 小说目录
    if os.path.exists(nd):  # 小说已存在
        return jsonify({'error': f'小说《{title}》已存在'}), 400
    os.makedirs(nd)  # 创建小说目录
    try:
        sf = f"{title}.txt"  # 保存文件名
        file.save(os.path.join(nd, sf))  # 保存上传的文件
        emoji = CATEGORY_EMOJI.get(category, '📖')  # 获取分类图标
        # 写入 info.txt 元数据
        with open(os.path.join(nd, "info.txt"), 'w', encoding='utf-8') as f:
            f.write(f"标题: {title}\n作者: {author}\n分类: {category}\n封面: {emoji}\n"
                    f"文件名: {sf}\n文件大小: {os.path.getsize(os.path.join(nd, sf))}\n")
        return jsonify({
            'success': True,
            'novel': {'title': title, 'author': author, 'category': category, 'cover': emoji}
        }), 201
    except Exception as e:
        # 上传失败时回滚：删除已创建的目录
        if os.path.exists(nd):
            import shutil
            shutil.rmtree(nd)
        return jsonify({'error': f'上传失败: {str(e)}'}), 500


# ==============================================================================
# 评论 API（基于 JSON 文件存储）
# ==============================================================================

@app.route('/api/comments/<nid>/<int:ci>', methods=['GET'])
def get_comments(nid, ci):
    """
    获取某章节或段落的评论列表

    # 参数说明
    # nid: 小说 ID
    # ci: 章节索引
    # pi: 段落索引（查询参数，-1 表示章节级评论）
    """
    pi = request.args.get('pi', '-1', type=int)  # 段落索引，默认 -1
    comments = _read_comments(nid, ci, pi)  # 读取评论
    return jsonify([_comment_to_dict(c) for c in comments])  # 转换为前端格式


@app.route('/api/comments', methods=['POST'])
def add_comment():
    """
    添加评论或回复

    # 请求体格式 (JSON):
    #   {
    #     "user_id": 1,
    #     "novel_id": "f001",
    #     "chapter_index": 0,
    #     "paragraph_index": -1,
    #     "text": "评论内容",
    #     "parent_id": null    # 如果为回复，填写父评论 ID
    #   }

    # parent_id 为空表示新评论，不为空表示回复已有评论
    """
    data = request.get_json()
    uid = data.get('user_id')
    # 校验登录状态
    if not uid or not _read_user(uid):
        return jsonify({'error': '请先登录'}), 401
    novel_id = data.get('novel_id')
    chapter_index = data.get('chapter_index', 0)
    paragraph_index = data.get('paragraph_index', -1)
    text = data.get('text', '').strip()
    parent_id = data.get('parent_id')
    if not novel_id or not text:  # 参数不完整
        return jsonify({'error': '参数不完整'}), 400
    user = _read_user(uid)  # 获取用户信息
    # 构造评论对象
    c = {
        'id': _next_cid(),                          # 评论 ID
        'novel_id': novel_id,                        # 所属小说
        'chapter_index': chapter_index,              # 章节索引
        'paragraph_index': paragraph_index,          # 段落索引
        'user_id': uid,                              # 用户 ID
        'username': user.get('用户名', '匿名'),       # 用户名
        'text': text,                                # 评论内容
        'parent_id': parent_id,                      # 父评论 ID
        'created_at': int(time.time()),              # 创建时间戳
        'replies': []                                # 回复列表
    }
    if parent_id:
        # 如果是回复：查找父评论并追加
        comments = _read_comments(novel_id, chapter_index, paragraph_index)
        if not _find_and_reply(comments, parent_id, c):  # 递归查找父评论
            return jsonify({'error': '父评论不存在'}), 404
        _write_comments(novel_id, chapter_index, paragraph_index, comments)
    else:
        # 如果是新评论：插入到列表头部
        comments = _read_comments(novel_id, chapter_index, paragraph_index)
        comments.insert(0, c)  # 最新评论在最前面
        _write_comments(novel_id, chapter_index, paragraph_index, comments)
    return jsonify(_comment_to_dict(c)), 201


@app.route('/api/comments/<int:cid>/vote', methods=['POST'])
def vote_comment(cid):
    """
    对评论进行点赞/点踩

    # 请求体格式 (JSON):
    #   { "user_id": 1, "vote": 1 }   # vote=1 点赞, vote=-1 点踩

    # 逻辑:
    #   - 如果已点赞再点点赞 → 取消点赞
    #   - 如果已点踩再点点踩 → 取消点踩
    #   - 如果已点赞再点点踩 → 取消点赞 + 点踩
    #   - 如果已点踩再点点赞 → 取消点踩 + 点赞
    #   - 无操作则新增投票

    # 返回: {"vote": 1|0|-1} — 当前用户的投票状态
    """
    data = request.get_json()
    uid = data.get('user_id')
    vote_type = data.get('vote', 1)  # 1=点赞, -1=点踩
    if not uid or not _read_user(uid):
        return jsonify({'error': '请先登录'}), 401
    votes = _load_votes()  # 加载所有投票数据
    cid_str = str(cid)
    uid_str = str(uid)
    if cid_str not in votes:  # 初始化该评论的投票记录
        votes[cid_str] = {'up': [], 'down': []}
    entry = votes[cid_str]
    # 处理当前用户已点赞的情况
    if uid_str in entry['up']:
        entry['up'].remove(uid_str)  # 取消点赞
        if vote_type == -1:  # 改为点踩
            entry['down'].append(uid_str)
            _save_votes(votes)
            return jsonify({'vote': -1})
        _save_votes(votes)
        return jsonify({'vote': 0})  # 取消投票
    # 处理当前用户已点踩的情况
    elif uid_str in entry['down']:
        entry['down'].remove(uid_str)  # 取消点踩
        if vote_type == 1:  # 改为点赞
            entry['up'].append(uid_str)
            _save_votes(votes)
            return jsonify({'vote': 1})
        _save_votes(votes)
        return jsonify({'vote': 0})  # 取消投票
    else:
        # 新增投票
        if vote_type == 1:
            entry['up'].append(uid_str)
        else:
            entry['down'].append(uid_str)
        _save_votes(votes)
        return jsonify({'vote': vote_type})


# ==============================================================================
# 应用启动
# ==============================================================================

# 创建默认演示账号（账号: demo, 密码: 123, 偏好: 玄幻/仙侠）
if not _user_exists('demo'):
    _write_user(_next_id(), 'demo', '123', ['玄幻', '仙侠'])

if __name__ == '__main__':
    """
    启动 Flask 开发服务器

    # debug=True: 开启调试模式，代码修改后自动重载
    # host='0.0.0.0': 监听所有网络接口（局域网可访问）
    # port=5000: 默认端口
    """
    app.run(debug=True, host='0.0.0.0', port=5000)
