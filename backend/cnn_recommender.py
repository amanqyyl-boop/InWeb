"""
基于 scikit-learn 的个性化小说推荐系统
=======================================
算法:
  1. KMeans 聚类 — 将所有小说按特征分簇
  2. Cosine Similarity — 计算用户偏好向量与小说的相似度
  3. 混合排序 — 聚类匹配 + 相似度 + 偏好偏置 + 基础质量

依赖: scikit-learn, numpy
"""
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

# 分类名称 → 索引（必须与前端一致）
CATEGORIES = ['玄幻', '仙侠', '都市', '言情', '历史', '科幻', '悬疑', '幻想', '军事', '网游']
CAT_TO_IDX = {c: i for i, c in enumerate(CATEGORIES)}
NUM_CATEGORIES = len(CATEGORIES)

# ─── 全局模型（惰性初始化） ───
_recommender = None


class SKRecommender:
    """
    scikit-learn 推荐模型

    使用 KMeans 聚类 + Cosine Similarity 实现混合推荐。

    特征工程（每本小说 12 维特征向量）：
      - 分类 one-hot 编码 (10维)
      - 评分归一化 (1维)
      - 热度归一化 (1维)

    推荐策略：
      1. 从浏览历史构建用户偏好向量
      2. 用 Cosine Similarity 找到用户最偏好的聚类
      3. 在偏好聚类中按相似度排序
      4. 融合注册偏好和基础质量分
    """

    def __init__(self, n_clusters=8):
        self.n_clusters = n_clusters
        self.kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
        self.scaler = StandardScaler()
        self._fitted = False

    # ─── 特征工程 ───

    def _build_features(self, novels):
        """
        为小说列表构建特征矩阵
        每本小说的特征向量 = [分类 one-hot (10维), 评分(归一化), 热度(归一化)]
        总共 12 维
        """
        n = len(novels)
        features = np.zeros((n, NUM_CATEGORIES + 2))

        for i, novel in enumerate(novels):
            cat_idx = CAT_TO_IDX.get(novel['category'], -1)
            if cat_idx >= 0:
                features[i, cat_idx] = 1.0
            features[i, NUM_CATEGORIES]     = novel.get('rating', 5) / 10.0
            features[i, NUM_CATEGORIES + 1] = novel.get('hot', 0) / 15000.0

        return features

    # ─── 训练 ───

    def fit(self, novels):
        """对所有小说进行 KMeans 聚类训练"""
        features = self._build_features(novels)
        features_scaled = self.scaler.fit_transform(features)
        self.kmeans.fit(features_scaled)
        self._fitted = True

        # 缓存结果
        self._features_scaled = features_scaled
        self._cluster_labels  = self.kmeans.labels_
        self._cluster_centers = self.kmeans.cluster_centers_
        self._novel_ids       = [n['id'] for n in novels]

        return self

    # ─── 推荐 ───

    def recommend(self, user_id, all_novels, browse_records, preferences):
        """
        为用户推荐小说

        参数:
          all_novels: 全部小说列表
          browse_records: list[dict] — 浏览记录
          preferences: list[str] — 注册时选的偏好分类

        返回:
          排序后的小说列表（前 12 本）
        """
        if not self._fitted:
            self.fit(all_novels)

        id_to_idx = {nid: i for i, nid in enumerate(self._novel_ids)}

        # ── 1. 构建用户偏好向量 ──
        browsed_vectors = []
        browsed_ids     = set()
        for rec in browse_records:
            nid = rec['novel_id'] if isinstance(rec, dict) else rec.novel_id
            browsed_ids.add(nid)
            idx = id_to_idx.get(nid)
            if idx is not None:
                browsed_vectors.append(self._features_scaled[idx])

        if browsed_vectors:
            user_vec = np.mean(browsed_vectors, axis=0)
        else:
            # 没有浏览历史 → 用注册偏好构造初始向量
            raw = np.zeros(NUM_CATEGORIES + 2)
            for pref in preferences:
                cat_idx = CAT_TO_IDX.get(pref, -1)
                if cat_idx >= 0:
                    raw[cat_idx] = 1.0
            user_vec = self.scaler.transform(raw.reshape(1, -1))[0]

        # ── 2. 聚类偏好权重：用户向量到各聚类中心的 Cosine 相似度 ──
        sims = cosine_similarity(user_vec.reshape(1, -1), self._cluster_centers)[0]
        sims = np.maximum(sims, 0)
        total_sim = sims.sum()
        if total_sim > 0:
            sims /= total_sim

        # ── 3. 注册偏好偏置 ──
        pref_bias = np.zeros(NUM_CATEGORIES)
        for p in preferences:
            if p in CAT_TO_IDX:
                pref_bias[CAT_TO_IDX[p]] = 0.5

        # ── 4. 对所有小说打分 ──
        scored = []
        for novel in all_novels:
            idx = id_to_idx.get(novel['id'])
            if idx is None:
                continue

            # 聚类匹配分
            cluster_label = self._cluster_labels[idx]
            cluster_score = sims[cluster_label]

            # Cosine 相似度（用户 vs 这本小说）
            novel_vec = self._features_scaled[idx].reshape(1, -1)
            sim = max(0.0, float(cosine_similarity(
                user_vec.reshape(1, -1), novel_vec
            )[0, 0]))

            # 分类偏好偏置
            cat_idx = CAT_TO_IDX.get(novel['category'], -1)
            bias = float(pref_bias[cat_idx]) if cat_idx >= 0 else 0

            # 基础质量
            base = novel.get('rating', 0) / 10 + novel.get('hot', 0) / 20000

            # 总分
            total = cluster_score * 0.35 + sim * 0.30 + bias * 0.25 + base * 0.10

            # 已浏览的略降权
            if novel['id'] in browsed_ids:
                total -= 0.3

            scored.append((novel, total))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [n for n, s in scored[:12]]

    # ─── 在线学习 ───

    def learn_from_browse(self, novel_id, all_novels, browse_records):
        """
        用户浏览后触发在线学习：
        每浏览 10 本不同的书后重新聚类一次
        """
        if not self._fitted:
            self.fit(all_novels)
            return

        unique_ids = {r['novel_id'] if isinstance(r, dict) else r.novel_id
                      for r in browse_records}
        if len(unique_ids) % 10 == 1 and len(unique_ids) > 1:
            self.fit(all_novels)


# =============================================
#  全局接口（保持与 app.py 兼容）
# =============================================

def get_recommender():
    """获取或初始化全局推荐器"""
    global _recommender
    if _recommender is None:
        _recommender = SKRecommender()
    return _recommender


def recommend_novels(user_id, all_novels, browse_records, preferences):
    """为用户推荐小说"""
    recommender = get_recommender()
    return recommender.recommend(user_id, all_novels, browse_records, preferences)


def learn_from_browse(user_id, novel_id, all_novels, browse_records):
    """用户浏览后触发在线学习"""
    recommender = get_recommender()
    recommender.learn_from_browse(novel_id, all_novels, browse_records)

