import numpy as np
from collections import Counter

CATEGORIES = ['玄幻','仙侠','都市','言情','历史','科幻','悬疑','幻想','军事','网游']
CAT_TO_IDX = {c:i for i,c in enumerate(CATEGORIES)}
NUM_CATEGORIES = len(CATEGORIES)

class CNNRecommender:
    def __init__(self, embed_dim=8, num_filters=12, kernel_size=3, seq_len=20):
        self.embed_dim=embed_dim; self.num_filters=num_filters
        self.kernel_size=kernel_size; self.seq_len=seq_len
        self.num_categories=NUM_CATEGORIES
        np.random.seed(42)
        self.W_emb=self._init_embedding()
        self.W_conv=np.random.randn(self.kernel_size,self.embed_dim,self.num_filters)*0.05
        self.b_conv=np.zeros(self.num_filters)
        self.W_fc=np.random.randn(self.num_filters,self.num_categories)*0.05
        self.b_fc=np.zeros(self.num_categories)

    def _init_embedding(self):
        emb=np.random.randn(self.num_categories,self.embed_dim)*0.1
        groups=[['玄幻','仙侠','幻想'],['都市','言情'],['历史','军事'],['科幻','网游'],['悬疑']]
        for g in groups:
            idxs=[CAT_TO_IDX[c] for c in g if c in CAT_TO_IDX]
            if len(idxs)>1:
                avg=np.mean([emb[i] for i in idxs],axis=0)
                for i in idxs: emb[i]=0.7*emb[i]+0.3*avg
        return emb

    def forward(self,cat_seqs):
        batch=len(cat_seqs)
        padded=np.zeros((batch,self.seq_len),dtype=np.int64)
        for i,seq in enumerate(cat_seqs):
            a=np.array(seq[-self.seq_len:],dtype=np.int64)
            padded[i,-len(a):]=a
        emb=self.W_emb[padded]
        out_len=emb.shape[1]-self.kernel_size+1
        conv=np.zeros((batch,out_len,self.num_filters))
        for j in range(out_len):
            conv[:,j,:]=np.sum(emb[:,j:j+self.kernel_size,:,:,np.newaxis]*self.W_conv[np.newaxis,:,:,:],axis=(1,2))
        conv=np.maximum(conv+self.b_conv,0)
        pooled=np.max(conv,axis=1)
        return np.tanh(pooled@self.W_fc+self.b_fc)

    def online_update(self,cat_seqs,targets,lr=0.01):
        pred=self.forward(cat_seqs)
        for b in range(len(cat_seqs)):
            target=pred[b].copy()
            for c in targets[b]:
                if 0<=c<self.num_categories: target[c]=1.0
            error=target-pred[b]
            a=np.array(cat_seqs[b][-self.seq_len:],dtype=np.int64)
            p=np.zeros(self.seq_len,dtype=np.int64)
            p[-min(len(a),self.seq_len):]=a[-self.seq_len:]
            emb=self.W_emb[p[np.newaxis,:]]
            ol=emb.shape[1]-self.kernel_size+1
            cv=np.zeros((1,ol,self.num_filters))
            for j in range(ol): cv[:,j,:]=np.sum(emb[:,j:j+self.kernel_size,:,:,np.newaxis]*self.W_conv[np.newaxis,:,:,:],axis=(1,2))
            cv=np.maximum(cv+self.b_conv,0)
            pl=np.max(cv,axis=1)
            self.W_fc+=lr*(pl.T@error[np.newaxis,:])
            self.b_fc+=lr*error

_recommender=None
def get_recommender():
    global _recommender
    if _recommender is None: _recommender=CNNRecommender()
    return _recommender

def recommend_novels(uid,all_novels,browse_records,preferences):
    rec=get_recommender()
    def nid(r): return r['novel_id'] if isinstance(r,dict) else r.novel_id
    hcats=[]
    for r in browse_records:
        n=next((x for x in all_novels if x['id']==nid(r)),None)
        if n and n['category'] in CAT_TO_IDX: hcats.append(CAT_TO_IDX[n['category']])
    if not hcats:
        for p in preferences:
            if p in CAT_TO_IDX: hcats.extend([CAT_TO_IDX[p]]*5)
    else:
        for r in browse_records:
            n=next((x for x in all_novels if x['id']==nid(r)),None)
            if n and n['category'] in CAT_TO_IDX:
                rec.online_update([hcats],[[CAT_TO_IDX[n['category']]]],lr=0.02)
    cs=rec.forward([hcats])[0] if hcats else np.zeros(NUM_CATEGORIES)
    pb=np.zeros(NUM_CATEGORIES)
    for p in preferences:
        if p in CAT_TO_IDX: pb[CAT_TO_IDX[p]]=0.5
    bids={nid(r) for r in browse_records}
    scored=[]
    for n in all_novels:
        ci=CAT_TO_IDX.get(n['category'],-1)
        if ci<0: continue
        total=float(cs[ci])*0.6+float(pb[ci])*0.25+(n.get('rating',0)/10+n.get('hot',0)/20000)*0.15
        if n['id'] in bids: total-=0.5
        scored.append((n,total))
    scored.sort(key=lambda x:x[1],reverse=True)
    return [x for x,s in scored[:12]]

def learn_from_browse(uid,nid,all_novels,browse_records):
    rec=get_recommender()
    def nid(r): return r['novel_id'] if isinstance(r,dict) else r.novel_id
    hcats=[]
    for r in browse_records:
        n=next((x for x in all_novels if x['id']==nid(r)),None)
        if n and n['category'] in CAT_TO_IDX: hcats.append(CAT_TO_IDX[n['category']])
    cn=next((x for x in all_novels if x['id']==nid),None)
    if not cn or cn['category'] not in CAT_TO_IDX: return
    tc=CAT_TO_IDX[cn['category']]
    if hcats: rec.online_update([hcats],[[tc]],lr=0.02)
