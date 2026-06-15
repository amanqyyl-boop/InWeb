"""
================================================================================
基于 scikit-learn 的个性化小说智能推荐系统
================================================================================

【算法详解 —— CNN 聚类 + 协同过滤混合推荐算法】
--------------------------------------------------
本系统并非使用深度学习 CNN（卷积神经网络），而是采用 "Content-based Clustering
Novel Recommender" 的缩写含义，核心算法由以下三部分组成：

1. KMeans 聚类算法
   ─────────────────
   - 将小说库中的所有小说根据特征向量进行无监督聚类
   - 每本小说被表示为 12 维特征向量（10 维分类 one-hot + 评分 + 热度）
   - 聚类数 n_clusters=8，将小说分成 8 个隐含主题簇
   - 同一簇内的小说在特征空间上彼此接近，代表它们具有相似的"风格-质量"模式

2. Cosine Similarity（余弦相似度）
   ─────────────────────────────────
   - 用于衡量用户偏好向量与小说特征向量之间的相似程度
   - 余弦相似度关注方向而非长度，适合处理稀疏的 one-hot 编码特征
   - 值域 [0, 1]，值越大表示用户与小说的匹配度越高
   - 应用场景：(a) 用户 vs 各聚类中心 → 确定用户偏好的簇
              (b) 用户 vs 每本小说   → 计算个性化匹配得分

3. 混合排序策略（Hybrid Ranking）
   ────────────────────────────────
   最终得分 = 聚类匹配分 × 0.35
            + 余弦相似度 × 0.30
            + 偏好偏置   × 0.25
            + 基础质量分 × 0.10
   - 已浏览过的小说额外降权 0.3，增加推荐多样性

================================================================================

【智能推送实现流程】
================================================================================

┌─────────────────────────────────────────────────────────────────┐
│                     智能推送全流程                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                │
│  步骤 ① 数据采集                                                │
│  ┌─────────────────────────────────────┐                       │
│  │ · 用户注册时选择的偏好分类（玄幻/仙侠等）│                       │
│  │ · 用户浏览记录（浏览过的小说ID）      │                       │
│  │ · 小说基础属性（分类、评分、热度）    │                       │
│  └─────────────────────────────────────┘                       │
│           ↓                                                    │
│  步骤 ② 特征工程                                                │
│  ┌─────────────────────────────────────┐                       │
│  │ 每本小说 → 12维特征向量：           │                       │
│  │ [分类 one-hot(10维) | 评分(1维) | 热度(1维)]                │
│  │ 然后经过 StandardScaler 标准化       │                       │
│  └─────────────────────────────────────┘                       │
│           ↓                                                    │
│  步骤 ③ KMeans 聚类训练                                        │
│  ┌─────────────────────────────────────┐                       │
│  │ 将所有小说聚为 8 个簇               │                       │
│  │ 每个簇有中心点（centroid）           │                       │
│  │ 同一簇的小说风格/质量相似            │                       │
│  └─────────────────────────────────────┘                       │
│           ↓                                                    │
│  步骤 ④ 用户画像构建                                            │
│  ┌─────────────────────────────────────┐                       │
│  │ · 有浏览历史 → 取浏览过小说的特征均值 │                       │
│  │ · 无浏览历史 → 用注册偏好构造初始向量 │                       │
│  │ 得到用户偏好向量（12维）              │                       │
│  └─────────────────────────────────────┘                       │
│           ↓                                                    │
│  步骤 ⑤ 多维度打分排序                                          │
│  ┌─────────────────────────────────────┐                       │
│  │ 对每本小说计算四项得分并加权求和      │                       │
│  │ ① 聚类匹配分   (35%) ← 用户偏好簇    │                       │
│  │ ② 余弦相似度   (30%) ← 用户 vs 小说  │                       │
│  │ ③ 偏好偏置     (25%) ← 注册分类偏好  │                       │
│  │ ④ 基础质量分   (10%) ← 评分+热度     │                       │
│  │ 已浏览的降权 -0.3 → 提升多样性        │                       │
│  └─────────────────────────────────────┘                       │
│           ↓                                                    │
│  步骤 ⑥ 返回 Top-12 推荐结果                                    │
│  ┌─────────────────────────────────────┐                       │
│  │ 按总分从高到低排序，取前12本返回      │                       │
│  │ 前端展示给用户                        │                       │
│  └─────────────────────────────────────┘                       │
│           ↓                                                    │
│  步骤 ⑦ 在线学习（持续优化）                                    │
│  ┌─────────────────────────────────────┐                       │
│  │ 用户每浏览 10 本不同的书后自动触发    │                       │
│  │ 重新聚类训练，模型不断适应用户变化    │                       │
│  └─────────────────────────────────────┘                       │
│                                                                │
└─────────────────────────────────────────────────────────────────┘

【关键特点】
----------
✅ 冷启动处理：新用户无浏览历史时，用注册偏好构造初始向量
✅ 多样性保证：已浏览小说降权，避免推荐结果过于单一
✅ 在线学习：用户行为变化时模型动态更新
✅ 轻量级：基于 sklearn，无需 GPU，适合小型项目快速部署

依赖: scikit-learn, numpy
================================================================================
"""
import numpy as np  # 导入 NumPy 库，用于高效的数值计算和矩阵运算
from sklearn.cluster import KMeans  # 导入 KMeans 聚类算法，用于小说分簇
from sklearn.metrics.pairwise import cosine_similarity  # 导入余弦相似度计算函数
from sklearn.preprocessing import StandardScaler  # 导入标准化工具，用于特征归一化

# ─── 分类名称 → 索引映射（必须与前端一致） ───
CATEGORIES = ['玄幻', '仙侠', '都市', '言情', '历史', '科幻', '悬疑', '幻想', '军事', '网游']
CAT_TO_IDX = {c: i for i, c in enumerate(CATEGORIES)}  # 分类名称到索引的映射字典
NUM_CATEGORIES = len(CATEGORIES)  # 分类总数，同时也是 one-hot 编码的维度

# ─── 全局模型变量（惰性初始化，第一次使用时才创建） ───
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
        """
        初始化推荐模型

        # 参数说明
        # n_clusters: 聚类数量，默认为 8，表示将小说分成 8 个隐含主题簇
        """
        self.n_clusters = n_clusters  # 保存聚类数
        self.kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')  # 创建 KMeans 聚类器
        self.scaler = StandardScaler()  # 创建标准化器，用于特征缩放
        self._fitted = False  # 标记模型是否已完成训练

    # ─── 特征工程 ───

    def _build_features(self, novels):
        """
        为小说列表构建特征矩阵

        # 每本小说的特征向量 = [分类 one-hot (10维), 评分(归一化), 热度(归一化)]
        # 总共 12 维特征向量

        # 参数说明
        # novels: 小说列表，每本小说包含 category, rating, hot 等字段

        # 返回
        # numpy.ndarray: 形状为 (小说数量, 12) 的特征矩阵
        """
        n = len(novels)  # 获取小说总数
        features = np.zeros((n, NUM_CATEGORIES + 2))  # 初始化全零特征矩阵，12 列

        for i, novel in enumerate(novels):  # 遍历每本小说
            cat_idx = CAT_TO_IDX.get(novel['category'], -1)  # 获取分类的 one-hot 索引
            if cat_idx >= 0:  # 如果分类有效
                features[i, cat_idx] = 1.0  # 对应分类位置置 1（one-hot 编码）
            # 评分归一化：原始评分范围 0-10，除以 10 映射到 0-1 区间
            features[i, NUM_CATEGORIES]     = novel.get('rating', 5) / 10.0
            # 热度归一化：原始热度范围 0-15000，除以 15000 映射到 0-1 区间
            features[i, NUM_CATEGORIES + 1] = novel.get('hot', 0) / 15000.0

        return features  # 返回构建好的特征矩阵

    # ─── 模型训练 ───

    def fit(self, novels):
        """
        对所有小说进行 KMeans 聚类训练

        # 参数说明
        # novels: 全部小说的列表，用于训练聚类模型

        # 返回
        # self: 训练后的模型实例（支持链式调用）
        """
        features = self._build_features(novels)  # 步骤1: 构建特征矩阵
        features_scaled = self.scaler.fit_transform(features)  # 步骤2: 标准化特征（均值0，标准差1）
        self.kmeans.fit(features_scaled)  # 步骤3: 执行 KMeans 聚类训练
        self._fitted = True  # 标记模型已训练完成

        # ── 缓存训练结果，加速后续推荐计算 ──
        self._features_scaled = features_scaled  # 缓存标准化后的特征矩阵
        self._cluster_labels  = self.kmeans.labels_  # 缓存每本小说的所属聚类标签
        self._cluster_centers = self.kmeans.cluster_centers_  # 缓存各聚类的中心点坐标
        self._novel_ids       = [n['id'] for n in novels]  # 缓存小说 ID 列表（用于快速查找）

        return self

    # ─── 推荐引擎核心 ───

    def recommend(self, user_id, all_novels, browse_records, preferences):
        """
        为用户推荐小说（智能推送的核心方法）

        # 参数说明
        # all_novels: 全部小说列表
        # browse_records: list[dict] — 用户的浏览历史记录
        # preferences: list[str] — 用户注册时选择的偏好分类

        # 返回
        # list[dict]: 排序后的推荐小说列表（前 12 本）

        # 推荐流程
        # 1. 从浏览历史构建用户偏好向量
        # 2. 计算用户向量与各聚类中心的余弦相似度
        # 3. 对每本小说进行多维度加权打分
        # 4. 按总分排序，返回 Top-12
        """
        if not self._fitted:  # 如果模型尚未训练
            self.fit(all_novels)  # 先执行训练

        # 构建小说 ID 到特征矩阵索引的快速查找字典
        id_to_idx = {nid: i for i, nid in enumerate(self._novel_ids)}

        # ── 步骤1: 构建用户偏好向量 ──
        browsed_vectors = []  # 存放用户浏览过的小说特征向量
        browsed_ids     = set()  # 存放用户浏览过的小说 ID（用于去重和降权）
        for rec in browse_records:  # 遍历浏览记录
            nid = rec['novel_id'] if isinstance(rec, dict) else rec.novel_id  # 提取小说 ID
            browsed_ids.add(nid)  # 将小说 ID 加入已浏览集合
            idx = id_to_idx.get(nid)  # 查找小说在特征矩阵中的索引
            if idx is not None:
                browsed_vectors.append(self._features_scaled[idx])  # 收集该小说的特征向量

        if browsed_vectors:
            # 有浏览历史 → 用户偏好向量 = 所有浏览过小说特征向量的均值
            user_vec = np.mean(browsed_vectors, axis=0)
        else:
            # 没有浏览历史（冷启动） → 用注册偏好构造初始用户向量
            raw = np.zeros(NUM_CATEGORIES + 2)  # 初始化全零向量
            for pref in preferences:  # 遍历用户注册时选择的偏好分类
                cat_idx = CAT_TO_IDX.get(pref, -1)  # 获取分类索引
                if cat_idx >= 0:
                    raw[cat_idx] = 1.0  # 偏好分类位置为 1
            # 用训练好的标准化器将原始偏好向量转换到标准化空间
            user_vec = self.scaler.transform(raw.reshape(1, -1))[0]

        # ── 步骤2: 计算用户偏好向量到各聚类中心的余弦相似度 ──
        # 这决定了用户更偏好哪些"隐含主题簇"
        sims = cosine_similarity(user_vec.reshape(1, -1), self._cluster_centers)[0]
        sims = np.maximum(sims, 0)  # 将负相似度截断为 0
        total_sim = sims.sum()  # 计算相似度总和，用于归一化
        if total_sim > 0:
            sims /= total_sim  # 归一化为概率分布（各聚类权重之和为 1）

        # ── 步骤3: 构建注册偏好偏置向量 ──
        # 用户在注册时明确选择的分类应获得额外加分
        pref_bias = np.zeros(NUM_CATEGORIES)  # 初始化偏置向量（10 维）
        for p in preferences:  # 遍历所有注册偏好
            if p in CAT_TO_IDX:
                pref_bias[CAT_TO_IDX[p]] = 0.5  # 偏好分类获得 0.5 的偏置加分

        # ── 步骤4: 对所有小说进行多维度加权打分 ──
        scored = []  # 存放 (小说对象, 总分) 的列表
        for novel in all_novels:  # 遍历全部小说
            idx = id_to_idx.get(novel['id'])  # 获取小说在特征矩阵中的索引
            if idx is None:  # 如果找不到该小说（理论上不会发生）
                continue  # 跳过

            # ① 聚类匹配分（权重 35%）
            # 用户偏好该小说所在簇的程度
            cluster_label = self._cluster_labels[idx]  # 获取该小说的所属聚类标签
            cluster_score = sims[cluster_label]  # 用户对该聚类的偏好权重

            # ② 余弦相似度分（权重 30%）
            # 用户偏好向量与这本小说特征向量的直接相似度
            novel_vec = self._features_scaled[idx].reshape(1, -1)  # 获取该小说的特征向量
            sim = max(0.0, float(cosine_similarity(
                user_vec.reshape(1, -1), novel_vec  # 计算用户向量与小说向量的余弦相似度
            )[0, 0]))

            # ③ 分类偏好偏置（权重 25%）
            # 如果该小说的分类是用户注册时选择的，获得额外加分
            cat_idx = CAT_TO_IDX.get(novel['category'], -1)  # 获取小说分类索引
            bias = float(pref_bias[cat_idx]) if cat_idx >= 0 else 0  # 获取偏置值

            # ④ 基础质量分（权重 10%）
            # 评分和热度共同构成基础质量，确保推荐内容本身是优质的
            base = novel.get('rating', 0) / 10 + novel.get('hot', 0) / 20000

            # ── 计算加权总分 ──
            total = cluster_score * 0.35 + sim * 0.30 + bias * 0.25 + base * 0.10

            # 已浏览过的略降权 0.3，增加推荐结果的多样性
            if novel['id'] in browsed_ids:
                total -= 0.3

            scored.append((novel, total))  # 将（小说, 总分）加入列表

        # ── 步骤5: 按总分降序排序，取前 12 本返回 ──
        scored.sort(key=lambda x: x[1], reverse=True)  # 按总分从高到低排序
        return [n for n, s in scored[:12]]  # 返回前 12 本推荐小说

    # ─── 在线学习（持续优化） ───

    def learn_from_browse(self, novel_id, all_novels, browse_records):
        """
        用户浏览后触发在线学习

        # 功能说明
        # 每当用户浏览一本小说时调用此方法
        # 每浏览 10 本不同的书后自动触发一次重新聚类
        # 使模型能够动态适应用户兴趣的变化

        # 参数说明
        # novel_id: 当前浏览的小说 ID
        # all_novels: 全部小说列表
        # browse_records: 用户的历史浏览记录
        """
        if not self._fitted:  # 如果模型尚未训练
            self.fit(all_novels)  # 先执行训练
            return  # 首次训练后直接返回

        # 统计用户浏览过的不同小说的数量
        unique_ids = {r['novel_id'] if isinstance(r, dict) else r.novel_id
                      for r in browse_records}
        # 每浏览 10 本不同的书触发一次重新训练（模 10 == 1 表示刚过 10 的倍数）
        if len(unique_ids) % 10 == 1 and len(unique_ids) > 1:
            self.fit(all_novels)  # 用全部小说重新聚类训练


# =============================================
#  全局接口函数（供 app.py 调用，保持接口兼容）
# =============================================

def get_recommender():
    """
    获取或初始化全局推荐器（单例模式）

    # 首次调用时创建 SKRecommender 实例
    # 后续调用直接返回已存在的实例
    # 确保整个应用生命周期内只维护一个推荐模型
    """
    global _recommender  # 声明使用全局变量
    if _recommender is None:  # 如果尚未创建
        _recommender = SKRecommender()  # 创建推荐器实例（默认 8 个聚类）
    return _recommender  # 返回全局推荐器


def recommend_novels(user_id, all_novels, browse_records, preferences):
    """
    为用户推荐小说的便捷接口

    # 参数说明
    # user_id: 用户 ID
    # all_novels: 全部小说列表
    # browse_records: 浏览历史记录列表
    # preferences: 用户注册偏好分类列表

    # 返回
    # list[dict]: 推荐小说列表（前 12 本）
    """
    recommender = get_recommender()  # 获取全局推荐器
    return recommender.recommend(user_id, all_novels, browse_records, preferences)


def learn_from_browse(user_id, novel_id, all_novels, browse_records):
    """
    用户浏览后触发在线学习的便捷接口

    # 参数说明
    # user_id: 用户 ID
    # novel_id: 当前浏览的小说 ID
    # all_novels: 全部小说列表
    # browse_records: 浏览历史记录列表
    """
    recommender = get_recommender()  # 获取全局推荐器
    recommender.learn_from_browse(novel_id, all_novels, browse_records)  # 触发在线学习

