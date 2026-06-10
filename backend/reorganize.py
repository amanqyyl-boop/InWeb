"""
扫描小说库：每本小说一个独立文件夹，从 novels.csv 和 txt内容提取作者生成 info.txt
"""
import os, csv, shutil, re

BASE = r"c:\Users\xzh18\Desktop\InWeb\小说库"
CSV_PATH = os.path.join(os.path.dirname(BASE), 'novels.csv')

CAT_EMOJI = {
    '玄幻类': '⚔️', '仙侠类': '🌿', '都市类': '🏙️', '历史类': '🏯',
    '科幻类': '🚀', '悬疑类': '🔔', '幻想类': '🐉', '军事类': '🪖', '网游类': '🎮', '灵异类': '🔔',
}

# 从 novels.csv 加载已知的作者/分类/封面数据
KNOWN_DATA = {}
if os.path.exists(CSV_PATH):
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            title = row.get('标题', '').strip()
            if title:
                KNOWN_DATA[title] = {
                    'author': row.get('作者', '').strip(),
                    'category': row.get('分类', '').strip(),
                    'cover': row.get('封面', '').strip(),
                }

def extract_author_from_text(filepath):
    """从txt小说内容中提取作者名"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            head = ''.join([f.readline() for _ in range(50)])
    except UnicodeDecodeError:
        try:
            with open(filepath, 'r', encoding='gbk') as f:
                head = ''.join([f.readline() for _ in range(50)])
        except:
            return "未知"

    patterns = [
        r'作者[：:]\s*(.+)',
        r'^作\s*者[：:](.+)$',
    ]
    for pat in patterns:
        m = re.search(pat, head)
        if m:
            name = m.group(1).strip().rstrip('）)').strip()
            if name and len(name) < 15:
                return name
    return "未知"

def clean_title(filename):
    name = filename.replace('.txt', '')
    for s in ['_TXT全本', '（精校版）', '(精校版)']:
        name = name.replace(s, '')
    return name.strip().strip('《').strip('》')

# 第一步：把零散的txt移到各自的子文件夹
for folder in sorted(os.listdir(BASE)):
    folder_path = os.path.join(BASE, folder)
    if not os.path.isdir(folder_path):
        continue
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isfile(item_path) and item.endswith('.txt'):
            title = clean_title(item)
            sub_dir = os.path.join(folder_path, title)
            os.makedirs(sub_dir, exist_ok=True)
            dst = os.path.join(sub_dir, item)
            if item_path != dst and not os.path.exists(dst):
                shutil.move(item_path, dst)
                print(f"  📦 移动: {folder}/{item} → {title}/")
        elif os.path.isfile(item_path) and item == 'info.json':
            os.remove(item_path)
            print(f"  🗑️  删除旧: {folder}/{item}")

# 第二步：为每个子文件夹生成/更新 info.txt
for folder in sorted(os.listdir(BASE)):
    folder_path = os.path.join(BASE, folder)
    if not os.path.isdir(folder_path):
        continue
    emoji = CAT_EMOJI.get(folder, '📖')
    category = folder.replace('类', '')
    for novel_dir in sorted(os.listdir(folder_path)):
        novel_path = os.path.join(folder_path, novel_dir)
        if not os.path.isdir(novel_path):
            continue
        txt_file = None
        for fname in os.listdir(novel_path):
            if fname.endswith('.txt') and fname != 'info.txt':
                txt_file = os.path.join(novel_path, fname)
                break
        if not txt_file:
            continue

        title = novel_dir
        filesize = os.path.getsize(txt_file)

        # ★ 优先级: novels.csv > txt内容提取 > 未知
        if title in KNOWN_DATA:
            author = KNOWN_DATA[title]['author']
            if KNOWN_DATA[title]['cover']:
                emoji = KNOWN_DATA[title]['cover']
            if KNOWN_DATA[title]['category']:
                category = KNOWN_DATA[title]['category']
        else:
            author = extract_author_from_text(txt_file)

        info_txt_path = os.path.join(novel_path, "info.txt")
        lines = [
            f"标题: {title}",
            f"作者: {author}",
            f"分类: {category}",
            f"封面: {emoji}",
            f"文件名: {os.path.basename(txt_file)}",
            f"文件大小: {filesize}",
        ]
        with open(info_txt_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        print(f"  📝 {folder}/{novel_dir}/info.txt (作者: {author})")

print("\n✅ 扫描完成！")
