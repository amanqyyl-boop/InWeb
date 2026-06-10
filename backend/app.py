import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///novels.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    preferences = db.Column(db.String(200), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BrowseRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    novel_id = db.Column(db.String(20), nullable=False)
    browsed_at = db.Column(db.DateTime, default=datetime.utcnow)

NOVELS = [
    {"id":"n1","title":"青云志","author":"萧鼎·仿","category":"玄幻","rating":9.2,"hot":9850,"desc":"天地不仁，以万物为刍狗。","cover":"☁️","chapters":["序章·青云山下","第一章 草庙村","第二章 七脉会武","第三章 噬魂之谜","第四章 竹林夜话","第五章 魔教来袭","第六章 天书现世","第七章 正邪之战","第八章 诛仙剑阵","第九章 凡尘飞升"]},
    {"id":"n2","title":"星辰变","author":"番茄·仿","category":"玄幻","rating":9.0,"hot":8720,"desc":"星球破碎，少年秦羽得星辰传承。","cover":"🌌","chapters":["第一章 海底洞穴","第二章 星辰之力","第三章 九剑秘境","第四章 紫玄星","第五章 万妖谷","第六章 星辰大海","第七章 神界争锋","第八章 鸿蒙之始"]},
    {"id":"n3","title":"仙路烟尘","author":"管平潮·仿","category":"仙侠","rating":8.8,"hot":6340,"desc":"一曲仙乐动九州，少年陈歌以琴入道。","cover":"🎋","chapters":["引子 琴音初动","第一章 江南烟雨","第二章 青城论道","第三章 魔琴之乱","第四章 九天玄音","第五章 红尘劫","第六章 仙凡之隔"]},
    {"id":"n4","title":"繁华都市","author":"都市夜归人","category":"都市","rating":8.5,"hot":7210,"desc":"从乡村走出的少年，在大都市中逆袭。","cover":"🏙️","chapters":["第一章 初入魔都","第二章 妙手回春","第三章 商海沉浮","第四章 红颜知己","第五章 暗流涌动","第六章 巅峰对决","第七章 繁华落幕"]},
    {"id":"n5","title":"春风十里不如你","author":"花间醉","category":"言情","rating":9.1,"hot":11800,"desc":"一段跨越十年的暗恋与守护。","cover":"🌸","chapters":["第一章 初见","第二章 同桌的你","第三章 毕业季","第四章 北上广","第五章 重逢","第六章 告白","第七章 余生"]},
    {"id":"n6","title":"大秦帝国","author":"孙皓晖·仿","category":"历史","rating":9.3,"hot":5500,"desc":"大秦从边陲小国到一统天下。","cover":"🏯","chapters":["第一章 河西狼烟","第二章 商鞅变法","第三章 合纵连横","第四章 长平之战","第五章 帝王之路","第六章 天下一统"]},
    {"id":"n7","title":"深空彼岸","author":"辰东·仿","category":"科幻","rating":8.9,"hot":6890,"desc":"星际时代，少年王煊觉醒超凡之力。","cover":"🚀","chapters":["第一章 宇宙漂流","第二章 新星纪元","第三章 超凡觉醒","第四章 星海争霸","第五章 深渊来客","第六章 彼岸之光"]},
    {"id":"n8","title":"午夜凶铃","author":"铃木光司·仿","category":"悬疑","rating":8.7,"hot":4320,"desc":"一卷神秘的录像带，七天之谜。","cover":"🔔","chapters":["第一章 录像带","第二章 七日之约","第三章 死亡预言","第四章 井中谜团","第五章 诅咒真相","第六章 轮回"]},
    {"id":"n9","title":"斗罗大陆","author":"唐家三少·仿","category":"玄幻","rating":9.0,"hot":15200,"desc":"唐门外门弟子唐三穿越斗罗大陆。","cover":"⚔️","chapters":["第一章 穿越","第二章 武魂觉醒","第三章 史莱克学院","第四章 魂师大赛","第五章 海神岛","第六章 双神战","第七章 成神之路"]},
    {"id":"n10","title":"凡人修仙传","author":"忘语·仿","category":"仙侠","rating":8.6,"hot":7800,"desc":"平凡少年韩立踏上修仙界。","cover":"🌿","chapters":["第一章 七玄门","第二章 血色试炼","第三章 筑基之路","第四章 灵界风云","第五章 大乘之战","第六章 飞升灵界"]},
    {"id":"n11","title":"傲慢与偏见","author":"简·奥斯汀·仿","category":"言情","rating":9.4,"hot":3200,"desc":"英国乡村的优雅爱情。","cover":"💃","chapters":["第一章 尼日斐庄园","第二章 舞会","第三章 傲慢","第四章 偏见","第五章 柯林斯先生","第六章 达西先生的信","第七章 彭伯利","第八章 终成眷属"]},
    {"id":"n12","title":"三体","author":"刘慈欣·仿","category":"科幻","rating":9.6,"hot":9200,"desc":"人类文明与三体文明的首次接触。","cover":"🌍","chapters":["第一章 科学边界","第二章 三体游戏","第三章 红岸基地","第四章 三体文明","第五章 面壁者","第六章 黑暗森林","第七章 死神永生"]}
]

def get_novel_by_id(novel_id):
    for n in NOVELS:
        if n['id'] == novel_id:
            return n
    return None

def parse_preferences(pref_str):
    return [p.strip() for p in pref_str.split(',') if p.strip()] if pref_str else []

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    preferences = data.get('preferences', [])
    if not username or len(username) < 2:
        return jsonify({'error': '用户名至少2个字符'}), 400
    if not password or len(password) < 3:
        return jsonify({'error': '密码至少3个字符'}), 400
    if len(preferences) < 2:
        return jsonify({'error': '请至少选择2个偏好类型'}), 400
    existing = User.query.filter_by(username=username).first()
    if existing:
        return jsonify({'error': '用户已存在'}), 400
    user = User(username=username, password=password, preferences=','.join(preferences))
    db.session.add(user)
    db.session.commit()
    return jsonify({'id': user.id, 'username': user.username, 'preferences': preferences}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    user = User.query.filter_by(username=username).first()
    if not user or user.password != password:
        return jsonify({'error': '用户名或密码错误'}), 401
    return jsonify({'id': user.id, 'username': user.username, 'preferences': parse_preferences(user.preferences)})

@app.route('/api/novels', methods=['GET'])
def get_novels():
    category = request.args.get('category', 'all')
    sort_by = request.args.get('sort', 'hot')
    novels = NOVELS[:]
    if category != 'all':
        novels = [n for n in novels if n['category'] == category]
    if sort_by == 'hot':
        novels.sort(key=lambda x: x['hot'], reverse=True)
    elif sort_by == 'rating':
        novels.sort(key=lambda x: x['rating'], reverse=True)
    elif sort_by == 'new':
        novels.sort(key=lambda x: x['id'], reverse=True)
    return jsonify(novels)

@app.route('/api/novels/<novel_id>', methods=['GET'])
def get_novel_detail(novel_id):
    novel = get_novel_by_id(novel_id)
    if not novel:
        return jsonify({'error': '小说不存在'}), 404
    return jsonify(novel)

@app.route('/api/browse', methods=['POST'])
def record_browse():
    data = request.get_json()
    user_id = data.get('user_id')
    novel_id = data.get('novel_id')
    if not user_id or not novel_id:
        return jsonify({'error': '缺少参数'}), 400
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    record = BrowseRecord(user_id=user_id, novel_id=novel_id)
    db.session.add(record)
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/history/<int:user_id>', methods=['GET'])
def get_history(user_id):
    records = BrowseRecord.query.filter_by(user_id=user_id).order_by(BrowseRecord.browsed_at.desc()).limit(20).all()
    novel_ids = list(set([r.novel_id for r in records]))
    novels = []
    for nid in novel_ids:
        n = get_novel_by_id(nid)
        if n:
            novels.append(n)
    return jsonify(novels)

@app.route('/api/recommend/<int:user_id>', methods=['GET'])
def recommend(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    preferences = parse_preferences(user.preferences)
    records = BrowseRecord.query.filter_by(user_id=user_id).all()
    history_ids = set(r.novel_id for r in records)
    history_novels = [get_novel_by_id(nid) for nid in history_ids if get_novel_by_id(nid)]
    scored = []
    for novel in NOVELS:
        score = 0
        if novel['category'] in preferences:
            score += 10
        if any(h and h['category'] == novel['category'] and h['id'] != novel['id'] for h in history_novels):
            score += 5
        if novel['id'] in history_ids:
            score += 2
        score += novel['rating'] / 3
        score += novel['hot'] / 5000 * 0.5
        scored.append((novel, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return jsonify([n for n, s in scored[:8]])

@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    return jsonify({'id': user.id, 'username': user.username, 'preferences': parse_preferences(user.preferences)})

@app.route('/api/user/<int:user_id>/preferences', methods=['PUT'])
def update_preferences(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    data = request.get_json()
    preferences = data.get('preferences', [])
    if len(preferences) < 2:
        return jsonify({'error': '至少选择2个偏好'}), 400
    user.preferences = ','.join(preferences)
    db.session.commit()
    return jsonify({'preferences': preferences})

with app.app_context():
    db.create_all()
    if not User.query.first():
        demo = User(username='demo', password='123', preferences='玄幻,仙侠')
        db.session.add(demo)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)