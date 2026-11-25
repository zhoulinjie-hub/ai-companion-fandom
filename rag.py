# -*- coding: utf-8 -*-
"""
模块6：RAG 知识库 —— 本地零依赖检索
======================================
让 AI 能读你的文档、基于资料回答，而不是只靠模型自带的知识瞎编。

为什么不用向量模型：
    实测 DeepSeek 不提供 embedding 接口；环境里也没装 chromadb/sentence-transformers。
    所以用纯 Python 手写一个 TF-IDF 检索器——零依赖、不联网、一定能跑通。
    面试时能讲清原理，比"调了个库"更有含金量。

流程：文档 -> 切块 -> 分词 -> 建 TF-IDF 索引 -> 提问时算相似度 -> 取最相关的几块塞进提示词
"""

import os
import re
import json
import math
from collections import Counter

INDEX_FILE = "rag/knowledge_index.json"

CHUNK_SIZE = 400       # 每块大约多少字
CHUNK_OVERLAP = 60     # 相邻块重叠多少字（避免一句话被切两半丢意思）
TOP_K = 3              # 每次检索取最相关的几块
MIN_SCORE = 0.15       # 相似度低于这个值就当没找到，别硬塞
# 说明：中文 n-gram 里"怎么""什么"这类常见字会带来约 0.1 的基础分，
# 实测相关问题约 0.37、无关问题约 0.11，取 0.15 能干净分开（阈值是调出来的，不是拍脑袋）


# ===== 第一步：切块 =====
def split_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """把长文档切成小块。重叠一点，避免边界处的句子被切断。"""
    text = re.sub(r"[ \t]+", " ", text.replace("\x00", ""))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


# ===== 第二步：中文分词 =====
def tokenize(text):
    """
    把文字切成词。没有 jieba 分词库，用 n-gram 折中：
    - 连续的英文字母/数字当成一个词
    - 中文按"单字 + 相邻两字"切（2-gram），比如"考研规划" -> 考/研/规/划/考研/研规/规划
    这样"考研"和"考研规划"能匹配上，效果够用且零依赖。
    """
    text = text.lower()
    tokens = []
    # 英文和数字整体提取
    for word in re.findall(r"[a-z0-9]+", text):
        tokens.append(word)
    # 中文按字符处理：单字 + 相邻双字
    chinese = re.findall(r"[\u4e00-\u9fff]+", text)
    for seg in chinese:
        for ch in seg:
            tokens.append(ch)
        for i in range(len(seg) - 1):
            tokens.append(seg[i:i + 2])
    return tokens


# ===== 第三步：TF-IDF 向量化 =====
def compute_idf(doc_tokens_list):
    """计算每个词在所有文档块里的逆文档频率IDF。越罕见的词越有价值。"""
    n = len(doc_tokens_list)
    df = Counter()
    for tokens in doc_tokens_list:
        for token in set(tokens):
            df[token] += 1
    return {token: math.log((n + 1) / (freq + 1)) + 1 for token, freq in df.items()}


def vectorize(tokens, idf):
    """把一段文字的词列表变成 TF-IDF 向量（字典：词 -> 权重）"""
    tf = Counter(tokens)
    vec = {}
    for token, count in tf.items():
        # TF：词在当前块出现的频率（取对数压一压，避免长文霸榜）
        weight = (1 + math.log(count)) * idf.get(token, 0)
        if weight > 0:
            vec[token] = weight
    return vec


def cosine_similarity(vec_a, vec_b):
    """余弦相似度：两个向量方向越接近，值越接近1，表示两段文字越相关"""
    if not vec_a or not vec_b:
        return 0.0
    # 只在两边都出现的词上计算（交集），效率更高
    common = set(vec_a) & set(vec_b)
    dot = sum(vec_a[t] * vec_b[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


# ===== 索引的读写 =====
def _ensure_file():
    """确保索引文件存在。注意：直接写，不调 save_index，避免递归（模块4的教训）"""
    if not os.path.exists("rag"):
        os.mkdir("rag")
    if not os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump({"documents": {}, "chunks": []}, f, ensure_ascii=False, indent=2)


def load_index():
    _ensure_file()
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"documents": {}, "chunks": []}


def save_index(index):
    _ensure_file()
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def add_document(filename, text):
    """
    添加一个文档到知识库：切块 -> 分词 -> 建索引。
    返回 (块数, 错误信息)；错误信息为空表示成功。
    """
    chunks = split_text(text)
    if not chunks:
        return 0, "文档内容为空"
    index = load_index()

    # 给每块编号、记来源
    start_id = len(index["chunks"])
    token_lists = []
    for offset, chunk in enumerate(chunks):
        chunk_id = start_id + offset
        tokens = tokenize(chunk)
        token_lists.append(tokens)
        index["chunks"].append({
            "id": chunk_id,
            "source": filename,
            "text": chunk,
            "tokens": tokens
        })

    # 重新计算整个索引的 IDF（因为加了新词）
    idf = compute_idf([c["tokens"] for c in index["chunks"]])
    for c in index["chunks"]:
        c["vector"] = vectorize(c["tokens"], idf)

    index["documents"][filename] = len(chunks)
    save_index(index)
    return len(chunks), ""


def delete_document(filename):
    """删除一个文档及其所有块，然后重建 IDF"""
    index = load_index()
    if filename not in index["documents"]:
        return False
    index["chunks"] = [c for c in index["chunks"] if c["source"] != filename]
    del index["documents"][filename]
    # 剩余块的 id 重新编号，保持连续
    for i, c in enumerate(index["chunks"]):
        c["id"] = i
    # 重建向量（IDF 变了，所有向量都要重算）
    idf = compute_idf([c["tokens"] for c in index["chunks"]])
    for c in index["chunks"]:
        c["vector"] = vectorize(c["tokens"], idf)
    save_index(index)
    return True


def clear_all():
    """清空整个知识库"""
    save_index({"documents": {}, "chunks": []})


def search(query, top_k=TOP_K):
    """
    检索：把问题转成向量，和所有块算相似度，返回最相关的几块。
    返回 [(相似度, 来源, 文本), ...]
    """
    index = load_index()
    if not index["chunks"]:
        return []
    # 用索引已有的 IDF 给问题向量化（IDF 存在时重建比较费，这里从向量反推近似）
    query_tokens = tokenize(query)
    # 用每个词的常见度近似算 IDF：从已有块的 tokens 统计
    idf = compute_idf([c["tokens"] for c in index["chunks"]])
    query_vec = vectorize(query_tokens, idf)

    scored = []
    for c in index["chunks"]:
        score = cosine_similarity(query_vec, c.get("vector", {}))
        if score >= MIN_SCORE:
            scored.append((score, c["source"], c["text"]))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


def format_context(results):
    """把检索结果拼成一段文字，用来塞进系统提示词"""
    if not results:
        return ""
    parts = []
    for i, (score, source, text) in enumerate(results, 1):
        parts.append(f"【资料{i}｜来自 {source}｜相关度 {score:.2f}】\n{text}")
    return "\n\n".join(parts)
