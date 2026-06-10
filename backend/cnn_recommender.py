"""
基于 1D CNN 的个性化小说推荐系统
=================================
架构: Embedding → Conv1D → ReLU → GlobalMaxPool → Dense → Tanh
输入: 用户浏览历史中的小说分类序号序列
输出: 每个分类的偏好得分 [-1, 1]

不依赖任何深度学习框架，纯 numpy 实现。
"""
import numpy as np
from collections import Counter

# 分类名称 → 索引（必须与前端一致）
CATEGORIES = ['玄幻', '仙侠', '都市', '言情', '历史', '科幻', '悬疑', '幻想', '军事', '网游']
CAT_TO_IDX = {c: i for i, c in enumerate(CATEGORIES)}
NUM_CATEGORIES = len(CATEGORIES)


class CNNRecommender:
    """
    1D CNN 推荐模型

    超参数说明:
      embed_dim: 每个分类的嵌入向量维度（越大表达越丰富）
      num_filters: 卷积核数量（越多捕捉的模式越多样）
      kernel_size: 卷积窗口大小（看连续几个分类的关系）
      seq_len: 输入序列固定长度（超过截断，不足补零）
    """

    def __init__(self, embed_dim=8, num_filters=12, kernel_size=3, seq_len=20):
        self.embed_dim = embed_dim
        self.num_filters = num_filters
        self.kernel_size = kernel_size
        self.seq_len = seq_len
        self.num_categories = NUM_CATEGORIES

        # 固定随机种子保证可复现
        np.random.seed(42)

        # ---- 可训练参数 ----
        # Embedding 矩阵: (num_categories, embed_dim)
        # 使用预训练语义初始化：相似分类的embedding更接近
        self.W_emb = self._init_embedding()

        # Conv1D 卷积核: (kernel_size, embed_dim, num_filters)
        self.W_conv = np.random.randn(self.kernel_size, self.embed_dim, self.num_filters) * 0.05
        self.b_conv = np.zeros(self.num_filters)

        # Dense 输出层: (num_filters, num_categories)
        self.W_fc = np.random.randn(self.num_filters, self.num_categories) * 0.05
        self.b_fc = np.zeros(self.num_categories)

    def _init_embedding(self):
        """
        语义化初始化 Embedding：
        相似分类的向量夹角更小，让CNN一开始就能识别出
        "玄幻→仙侠"、"科幻→网游" 这类关联关系
        """
        emb = np.random.randn(self.num_categories, self.embed_dim) * 0.1

        # 定义分类相似度对 (同类群组)
        groups = [
            ['玄幻', '仙侠', '幻想'],   # 东方幻想类
            ['都市', '言情'],           # 现代情感类
            ['历史', '军事'],           # 历史军事类
            ['科幻', '网游'],           # 科技幻想类
            ['悬疑'],                   # 悬疑独一类
        ]
        for group in groups:
            indices = [CAT_TO_IDX[c] for c in group if c in CAT_TO_IDX]
            if len(indices) > 1:
                # 组内向量平均化（让它们更接近）
                avg = np.mean([emb[i] for i in indices], axis=0)
                for i in indices:
                    emb[i] = 0.7 * emb[i] + 0.3 * avg

        return emb

    # ─────────── 前向传播 ───────────

    def _embed(self, seq):
        """Embedding 查找: (batch, seq_len) → (batch, seq_len, embed_dim)"""
        return self.W_emb[seq]

    def _conv1d(self, x):
        """
        1D 卷积 (宽卷积, 无填充)
        x: (batch, seq_len, embed_dim)
        返回: (batch, seq_len - kernel_size + 1, num_filters)
        """
        batch, seq_len, emb_dim = x.shape
        k = self.kernel_size
        out_len = seq_len - k + 1
        out = np.zeros((batch, out_len, self.num_filters))
        for i in range(out_len):
            # 窗口切片: (batch, k, emb_dim)
            window = x[:, i:i + k, :]  # (batch, k, emb_dim)
            # 与卷积核逐元素乘再求和: (batch, k, emb_dim) * (k, emb_dim, filters)
            # → (batch, filters)
            out[:, i, :] = np.sum(
                window[:, :, :, np.newaxis] * self.W_conv[np.newaxis, :, :, :],
                axis=(1, 2)
            )
        return out + self.b_conv

    def _global_max_pool(self, x):
        """全局最大池化: (batch, time, filters) → (batch, filters)"""
        return np.max(x, axis=1)

    def forward(self, cat_seqs):
        """
        前向传播计算偏好得分

        参数:
          cat_seqs: list[list[int]] — 每个用户的分类历史序列
        返回:
          np.ndarray shape (batch, num_categories) — [-1, 1] 偏好分
        """
        batch = len(cat_seqs)

        # 1. 填充/截断到固定长度
        padded = np.zeros((batch, self.seq_len), dtype=np.int64)
        for i, seq in enumerate(cat_seqs):
            seq_arr = np.array(seq[-self.seq_len:], dtype=np.int64)
            if len(seq_arr) > self.seq_len:
                seq_arr = seq_arr[-self.seq_len:]
            padded[i, -len(seq_arr):] = seq_arr

        # 2. Embedding
        emb = self._embed(padded)  # (batch, seq_len, embed_dim)

        # 3. Conv1D + ReLU
        conv = self._conv1d(emb)  # (batch, out_len, filters)
        conv = np.maximum(conv, 0)  # ReLU

        # 4. Global Max Pooling
        pooled = self._global_max_pool(conv)  # (batch, filters)

        # 5. Dense + Tanh
        scores = pooled @ self.W_fc + self.b_fc  # (batch, categories)
        return np.tanh(scores)  # [-1, 1]

    # ─────────── 在线学习 ───────────

    def online_update(self, cat_seqs, target_categories_list, lr=0.01):
        """
        在线增量学习：用用户的最新行为微调模型

        参数:
          cat_seqs: list[list[int]] — 用户历史分类序列
          target_categories_list: list[list[int]] — 用户正反馈的分类
          lr: 学习率
        """
        # 前向传播获取当前预测
        pred = self.forward(cat_seqs)  # (batch, num_categories)

        for b in range(len(cat_seqs)):
            # 构建目标: 浏览过的分类 → +1，没浏览过的 → 当前预测值（不变）
            target = pred[b].copy()
            for cat_idx in target_categories_list[b]:
                if 0 <= cat_idx < self.num_categories:
                    target[cat_idx] = 1.0

            # 误差 = 目标 - 预测
            error = target - pred[b]  # (num_categories,)

            # 更新 Dense 层
            seq = np.array(cat_seqs[b][-self.seq_len:], dtype=np.int64)
            padded = np.zeros(self.seq_len, dtype=np.int64)
            padded[-min(len(seq), self.seq_len):] = seq[-self.seq_len:]

            # 重新计算池化层输出（用于反向传播）
            emb = self._embed(padded[np.newaxis, :])  # (1, seq_len, embed_dim)
            conv = self._conv1d(emb)
            conv = np.maximum(conv, 0)
            pooled = self._global_max_pool(conv)  # (1, filters)

            # Dense 梯度: dL/dW_fc = pooled^T @ error
            grad_W = pooled.T @ error[np.newaxis, :]  # (filters, categories)
            grad_b = error  # (categories,)
            self.W_fc += lr * grad_W
            self.b_fc += lr * grad_b

    # ─────────── 工具方法 ───────────

    def category_name_to_idx(self, name):
        """分类名称 → 索引"""
        return CAT_TO_IDX.get(name, 0)

    def get_all_category_scores(self, cat_seq):
        """给定用户历史，计算所有分类的偏好分"""
        scores = self.forward([cat_seq])[0]
        return {CATEGORIES[i]: float(round(scores[i], 4)) for i in range(self.num_categories)}


# =============================================
#  全局单例
# =============================================
_recommender = None


def get_recommender():
    """获取或初始化全局 CNN 推荐器"""
    global _recommender
    if _recommender is None:
        _recommender = CNNRecommender()
    return _recommender


def recommend_novels(user_id, all_novels, browse_records, preferences):
    """
    使用 CNN 为用户推荐小说

    参数:
      user_id: 用户 ID
      all_novels: 全部小说列表
      browse_records: list[dict] — 每个记录含 novel_id 键
      preferences: 用户注册时选择的偏好分类列表

    返回:
      排序后的小说列表（前 12 本）
    """
    recommender = get_recommender()

    def get_nid(rec):
        return rec['novel_id'] if isinstance(rec, dict) else rec.novel_id

    # 构建用户浏览历史 → 分类索引序列
    history_cats = []
    for rec in browse_records:
        novel = next((n for n in all_novels if n['id'] == get_nid(rec)), None)
        if novel and novel['category'] in CAT_TO_IDX:
            history_cats.append(CAT_TO_IDX[novel['category']])

    if not history_cats:
        for pref in preferences:
            if pref in CAT_TO_IDX:
                history_cats.extend([CAT_TO_IDX[pref]] * 5)
    else:
        for rec in browse_records:
            novel = next((n for n in all_novels if n['id'] == get_nid(rec)), None)
            if novel and novel['category'] in CAT_TO_IDX:
                recommender.online_update(
                    [history_cats],
                    [[CAT_TO_IDX[novel['category']]]],
                    lr=0.02
                )

    cat_scores = recommender.forward([history_cats])[0] if history_cats else np.zeros(NUM_CATEGORIES)

    pref_bias = np.zeros(NUM_CATEGORIES)
    for p in preferences:
        if p in CAT_TO_IDX:
            pref_bias[CAT_TO_IDX[p]] = 0.5

    browsed_ids = {get_nid(r) for r in browse_records}
    scored = []
    for novel in all_novels:
        cat_idx = CAT_TO_IDX.get(novel['category'], -1)
        if cat_idx < 0:
            continue
        cnn_score = float(cat_scores[cat_idx])
        bias = float(pref_bias[cat_idx])
        base = novel.get('rating', 0) / 10 + novel.get('hot', 0) / 20000
        total = cnn_score * 0.6 + bias * 0.25 + base * 0.15
        if novel['id'] in browsed_ids:
            total -= 0.5
        scored.append((novel, total))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [n for n, s in scored[:12]]


# ─────────── 在线学习触发 ───────────
def learn_from_browse(user_id, novel_id, all_novels, browse_records):
    """
    用户浏览后触发在线学习，更新 CNN 权重
    """
    recommender = get_recommender()

    def get_nid(rec):
        return rec['novel_id'] if isinstance(rec, dict) else rec.novel_id

    history_cats = []
    for rec in browse_records:
        novel = next((n for n in all_novels if n['id'] == get_nid(rec)), None)
        if novel and novel['category'] in CAT_TO_IDX:
            history_cats.append(CAT_TO_IDX[novel['category']])

    current_novel = next((n for n in all_novels if n['id'] == novel_id), None)
    if not current_novel or current_novel['category'] not in CAT_TO_IDX:
        return

    target_cat = CAT_TO_IDX[current_novel['category']]

    if history_cats:
        recommender.online_update(
            [history_cats],
            [[target_cat]],
            lr=0.02
        )
