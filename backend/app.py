import os, re, json, random
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from cnn_recommender import recommend_novels, learn_from_browse

app = Flask(__name__, static_folder=None)  # 不使用默认静态目录，手动配置
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), 'frontend')
NOVEL_LIB_DIR = os.path.join(os.path.dirname(BASE_DIR), '小说库')
ACCOUNTS_DIR = os.path.join(BASE_DIR, 'accounts')
os.makedirs(ACCOUNTS_DIR, exist_ok=True)
ID_COUNTER = os.path.join(ACCOUNTS_DIR, '_next_id.txt')

CATEGORY_MAP = {'玄幻类':'玄幻','仙侠类':'仙侠','都市类':'都市','历史类':'历史','科幻类':'科幻','灵异类':'悬疑','幻想类':'幻想','军事类':'军事','网游类':'网游'}
CATEGORY_EMOJI = {'玄幻':'⚔️','仙侠':'🌿','都市':'🏙️','历史':'🏯','科幻':'🚀','悬疑':'🔔','幻想':'🐉','军事':'🪖','网游':'🎮'}
CATEGORY_FOLDER_MAP = {v:k for k,v in CATEGORY_MAP.items()}

# ─── 扫描小说库 ───
def parse_info_txt(fp):
    info = {}
    if os.path.exists(fp):
        with open(fp, 'r', encoding='utf-8') as f:
            for line in f:
                if ':' in line:
                    k,v = line.strip().split(':',1)
                    info[k.strip()] = v.strip()
    return info

def _extract_description(txt_path, author, category):
    """从小说 txt 中提取开头一小段作为简介"""
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            text = f.read(500)
    except:
        try:
            with open(txt_path, 'r', encoding='gbk') as f:
                text = f.read(500)
        except:
            return f'《{os.path.basename(txt_path).replace(".txt","")}》·{category}类作品'
    # 去掉标题行和空行，取第一段有意义的文字
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    # 过滤掉纯数字、太短的标题行
    meaningful = [l for l in lines if len(l) > 6 and not l.startswith('第')]
    if meaningful:
        snippet = meaningful[0][:120]
        return snippet
    return f'《{os.path.basename(txt_path).replace(".txt","")}》·{category}类作品'

def scan_novel_library():
    novels = []; idx = 0
    if not os.path.isdir(NOVEL_LIB_DIR): return novels
    for fn in sorted(os.listdir(NOVEL_LIB_DIR)):
        fp = os.path.join(NOVEL_LIB_DIR, fn)
        if not os.path.isdir(fp): continue
        cat = CATEGORY_MAP.get(fn, fn.replace('类',''))
        for nd in sorted(os.listdir(fp)):
            np = os.path.join(fp, nd)
            if not os.path.isdir(np): continue
            info = parse_info_txt(os.path.join(np,"info.txt"))
            title = info.get('标题',nd)
            author = info.get('作者','未知')
            emoji = info.get('封面',CATEGORY_EMOJI.get(cat,'📖'))
            txt = None
            for f2 in os.listdir(np):
                if f2.endswith('.txt') and f2!='info.txt':
                    txt = os.path.join(np,f2); break
            if not txt: continue
            idx += 1
            fs = os.path.getsize(txt)
            # 从小说正文提取开头一小段作为简介
            desc = _extract_description(txt, author, cat)
            novels.append({"id":f"f{idx:03d}","title":title,"author":author,"category":cat,
                "rating":round(min(9.5,7.0+(fs/20000000)*2.5),1),"hot":min(15000,3000+fs//1000),
                "desc":desc,"cover":emoji,"filepath":txt,"filesize":fs})
    return novels

ALL_NOVELS = scan_novel_library()

def get_novel_by_id(nid):
    for n in ALL_NOVELS:
        if n['id']==nid: return n
    return None

def get_novel_filepath(novel):
    if novel.get('filepath') and os.path.exists(novel['filepath']):
        return novel['filepath']
    for fn,wc in CATEGORY_MAP.items():
        if wc==novel['category']:
            fp = os.path.join(NOVEL_LIB_DIR,fn)
            if os.path.isdir(fp):
                for f in os.listdir(fp):
                    if novel['title'] in f: return os.path.join(fp,f)
    return None

def read_novel_file(fp):
    if not os.path.exists(fp): return None
    try:
        with open(fp,'r',encoding='utf-8') as f: text=f.read()
    except:
        try:
            with open(fp,'r',encoding='gbk') as f: text=f.read()
        except: return None
    pat = re.compile(r'(第[一二三四五六七八九十百千零\d]+[章回节部])')
    parts = pat.split(text); chapters = []
    if len(parts)>1:
        cur="序章"
        for i,p in enumerate(parts):
            if re.match(r'第[^第]+$',p): cur=p
            elif p.strip():
                ps=[x.strip() for x in p.split('\n') if x.strip()]
                chapters.append({'title':cur,'content':'\n'.join(ps[:300])[:8000]})
                cur="后续"
    else:
        ps=[x.strip() for x in text.split('\n') if x.strip()]
        for i in range(0,min(len(ps),2000),80):
            chapters.append({'title':f'第{len(chapters)+1}章','content':'\n'.join(ps[i:i+80][:300])[:8000]})
    return chapters if chapters else None

# ─── 文件账号系统 ───
def _next_id():
    try:
        with open(ID_COUNTER,'r') as f: n=int(f.read().strip())
    except: n=1
    with open(ID_COUNTER,'w') as f: f.write(str(n+1))
    return n

def _read_user(uid):
    p=os.path.join(ACCOUNTS_DIR,str(uid),'info.txt')
    if not os.path.exists(p): return None
    info={}
    with open(p,'r',encoding='utf-8') as f:
        for line in f:
            if ':' in line: k,v=line.strip().split(':',1); info[k.strip()]=v.strip()
    return info

def _write_user(uid,un,pw,pr):
    d=os.path.join(ACCOUNTS_DIR,str(uid)); os.makedirs(d,exist_ok=True)
    with open(os.path.join(d,'info.txt'),'w',encoding='utf-8') as f:
        f.write(f"用户名: {un}\n密码: {pw}\n偏好: {','.join(pr)}\n")

def _read_history(uid):
    p=os.path.join(ACCOUNTS_DIR,str(uid),'history.txt')
    if not os.path.exists(p): return []
    rs=[]
    with open(p,'r',encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if line:
                parts=line.rsplit('|',1)
                rs.append({'novel_id':parts[0],'time':parts[1] if len(parts)>1 else ''})
    return rs

def _write_history(uid,rs):
    d=os.path.join(ACCOUNTS_DIR,str(uid)); os.makedirs(d,exist_ok=True)
    with open(os.path.join(d,'history.txt'),'w',encoding='utf-8') as f:
        for r in rs: f.write(f"{r['novel_id']}|{r['time']}\n")

def _add_history(uid,nid):
    rs=_read_history(uid)
    rs=[r for r in rs if r['novel_id']!=nid]
    rs.insert(0,{'novel_id':nid,'time':str(int(__import__('time').time()))})
    _write_history(uid,rs[:50]); return rs

def _user_exists(un):
    for d in os.listdir(ACCOUNTS_DIR):
        if d=='_next_id.txt' or not d.isdigit(): continue
        info=_read_user(d)
        if info and info.get('用户名')==un: return True
    return False

def _find_user(un):
    for d in os.listdir(ACCOUNTS_DIR):
        if d=='_next_id.txt' or not d.isdigit(): continue
        info=_read_user(d)
        if info and info.get('用户名')==un: return int(d),info
    return None,None

# ─── 前端静态文件服务 ───
@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_frontend(filename):
    return send_from_directory(FRONTEND_DIR, filename)

# ─── 内容API ───
@app.route('/api/novels/<nid>/content/<int:ci>',methods=['GET'])
def get_chapter_content(nid,ci):
    novel=get_novel_by_id(nid)
    if not novel: return jsonify({'error':'小说不存在'}),404
    fp=get_novel_filepath(novel)
    if not fp: return jsonify({'error':'暂无文本文件'}),404
    chs=read_novel_file(fp)
    if not chs or ci<0 or ci>=len(chs): return jsonify({'error':'章节不存在'}),404
    ch=chs[ci]
    return jsonify({'novel_id':nid,'chapter_index':ci,'chapter_title':ch['title'],'content':ch['content'],'total_chapters':len(chs)})

@app.route('/api/novels/<nid>/file-info',methods=['GET'])
def get_novel_file_info(nid):
    novel=get_novel_by_id(nid)
    if not novel: return jsonify({'error':'小说不存在'}),404
    fp=get_novel_filepath(novel)
    if not fp or not os.path.exists(fp): return jsonify({'has_file':False})
    chs=read_novel_file(fp)
    return jsonify({'has_file':True,'file_name':os.path.basename(fp),'file_size':os.path.getsize(fp),'total_chapters':len(chs) if chs else 0})

# ─── 账号API ───
@app.route('/api/register',methods=['POST'])
def register():
    data=request.get_json(); un=data.get('username','').strip(); pw=data.get('password','').strip(); pr=data.get('preferences',[])
    if not un or len(un)<2: return jsonify({'error':'用户名至少2个字符'}),400
    if not pw or len(pw)<3: return jsonify({'error':'密码至少3个字符'}),400
    if len(pr)<2: return jsonify({'error':'请至少选择2个偏好类型'}),400
    if _user_exists(un): return jsonify({'error':'用户已存在'}),400
    uid=_next_id(); _write_user(uid,un,pw,pr)
    return jsonify({'id':uid,'username':un,'preferences':pr}),201

@app.route('/api/login',methods=['POST'])
def login():
    data=request.get_json(); un=data.get('username','').strip(); pw=data.get('password','').strip()
    uid,info=_find_user(un)
    if not info or info.get('密码')!=pw: return jsonify({'error':'用户名或密码错误'}),401
    pr=[p.strip() for p in info.get('偏好','').split(',') if p.strip()]
    return jsonify({'id':uid,'username':un,'preferences':pr})

@app.route('/api/user/<int:uid>',methods=['GET'])
def get_user(uid):
    info=_read_user(uid)
    if not info: return jsonify({'error':'用户不存在'}),404
    pr=[p.strip() for p in info.get('偏好','').split(',') if p.strip()]
    return jsonify({'id':uid,'username':info.get('用户名',''),'preferences':pr})

@app.route('/api/user/<int:uid>/preferences',methods=['PUT'])
def update_preferences(uid):
    info=_read_user(uid)
    if not info: return jsonify({'error':'用户不存在'}),404
    data=request.get_json(); pr=data.get('preferences',[])
    if len(pr)<2: return jsonify({'error':'至少选择2个偏好'}),400
    _write_user(uid,info.get('用户名',''),info.get('密码',''),pr)
    return jsonify({'preferences':pr})

# ─── 小说查询API ───
@app.route('/api/novels',methods=['GET'])
def get_novels():
    cat=request.args.get('category','all'); sort=request.args.get('sort','hot')
    ns=ALL_NOVELS[:]
    if cat!='all': ns=[n for n in ns if n['category']==cat]
    if sort=='hot': ns.sort(key=lambda x:x['hot'],reverse=True)
    elif sort=='rating': ns.sort(key=lambda x:x['rating'],reverse=True)
    elif sort=='new': ns.sort(key=lambda x:x.get('filesize',0),reverse=True)
    return jsonify([{k:v for k,v in n.items() if k not in ('filepath','filesize')} for n in ns])

@app.route('/api/novels/<nid>',methods=['GET'])
def get_novel_detail(nid):
    novel=get_novel_by_id(nid)
    if not novel: return jsonify({'error':'小说不存在'}),404
    item={k:v for k,v in novel.items() if k not in ('filepath','filesize')}
    if 'chapters' not in item or not item['chapters']:
        fp=get_novel_filepath(novel)
        if fp:
            chs=read_novel_file(fp)
            item['chapters']=[c['title'] for c in chs] if chs else ['第一章']
        else: item['chapters']=['第一章']
    return jsonify(item)

# ─── 浏览&历史API ───
@app.route('/api/browse',methods=['POST'])
def record_browse():
    data=request.get_json(); uid=data.get('user_id'); nid=data.get('novel_id')
    if not uid or not nid: return jsonify({'error':'缺少参数'}),400
    if not _read_user(uid): return jsonify({'error':'用户不存在'}),404
    rs=_add_history(uid,nid)
    try: learn_from_browse(uid,nid,ALL_NOVELS,rs)
    except: pass
    return jsonify({'status':'ok'})

@app.route('/api/history/<int:uid>',methods=['GET'])
def get_history(uid):
    if not _read_user(uid): return jsonify({'error':'用户不存在'}),404
    records=_read_history(uid); seen=set(); novels=[]
    for r in records:
        if r['novel_id'] not in seen:
            seen.add(r['novel_id'])
            n=get_novel_by_id(r['novel_id'])
            if n:
                item={k:v for k,v in n.items() if k not in ('filepath','filesize')}
                item['browse_time']=r['time']; novels.append(item)
    return jsonify(novels)

@app.route('/api/history/<int:uid>/delete',methods=['POST'])
def delete_history(uid):
    if not _read_user(uid): return jsonify({'error':'用户不存在'}),404
    data=request.get_json(); nid=data.get('novel_id','')
    rs=[r for r in _read_history(uid) if r['novel_id']!=nid]
    _write_history(uid,rs)
    return jsonify({'status':'ok'})

@app.route('/api/history/<int:uid>/clear',methods=['POST'])
def clear_history(uid):
    if not _read_user(uid): return jsonify({'error':'用户不存在'}),404
    _write_history(uid,[])
    return jsonify({'status':'ok'})

# ─── 推荐API ───
@app.route('/api/recommend/random',methods=['GET'])
def random_recommend():
    selected=random.sample(ALL_NOVELS,min(2,len(ALL_NOVELS)))
    return jsonify([{k:v for k,v in n.items() if k not in ('filepath','filesize')} for n in selected])

@app.route('/api/recommend/<int:uid>',methods=['GET'])
def recommend(uid):
    info=_read_user(uid)
    if not info: return jsonify({'error':'用户不存在'}),404
    pr=[p.strip() for p in info.get('偏好','').split(',') if p.strip()]
    rec=recommend_novels(uid,ALL_NOVELS,_read_history(uid),pr)
    return jsonify([{k:v for k,v in n.items() if k not in ('filepath','filesize')} for n in rec])

# ─── 上传API ───
@app.route('/api/novels/upload',methods=['POST'])
def upload_novel():
    title=request.form.get('title','').strip(); author=request.form.get('author','').strip()
    category=request.form.get('category','').strip(); file=request.files.get('file')
    if not title: return jsonify({'error':'请输入小说标题'}),400
    if not author: return jsonify({'error':'请输入作者'}),400
    if not category: return jsonify({'error':'请选择分类'}),400
    if not file or not file.filename.endswith('.txt'): return jsonify({'error':'请上传txt文件'}),400
    fn=CATEGORY_FOLDER_MAP.get(category,category+'类')
    cd=os.path.join(NOVEL_LIB_DIR,fn); os.makedirs(cd,exist_ok=True)
    nd=os.path.join(cd,title)
    if os.path.exists(nd): return jsonify({'error':f'小说《{title}》已存在'}),400
    os.makedirs(nd)
    try:
        sf=f"{title}.txt"; file.save(os.path.join(nd,sf))
        emoji=CATEGORY_EMOJI.get(category,'📖')
        with open(os.path.join(nd,"info.txt"),'w',encoding='utf-8') as f:
            f.write(f"标题: {title}\n作者: {author}\n分类: {category}\n封面: {emoji}\n文件名: {sf}\n文件大小: {os.path.getsize(os.path.join(nd,sf))}\n")
        return jsonify({'success':True,'novel':{'title':title,'author':author,'category':category,'cover':emoji}}),201
    except Exception as e:
        if os.path.exists(nd): import shutil; shutil.rmtree(nd)
        return jsonify({'error':f'上传失败: {str(e)}'}),500

# ─── 启动 ───
if not _user_exists('demo'):
    _write_user(_next_id(),'demo','123',['玄幻','仙侠'])

if __name__=='__main__':
    app.run(debug=True,host='0.0.0.0',port=5000)
