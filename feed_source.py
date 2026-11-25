# -*- coding: utf-8 -*-
"""
粉丝陪伴 · 真实数据源抓取（模块11）
====================================

把"手动喂动态"升级成"真的从网上抓"。这是数据源模块的最后一环。

设计要点（为什么这么做）：
  · 零新依赖：用 Python 标准库 urllib + xml.etree，不装 feedparser/bs4，
    保证 clone 下来就能跑，开源项目最怕装一堆库。
  · 同时支持 RSS 2.0 和 Atom：两种 XML 命名空间不一样，都要处理。
  · 合规：只抓公开 RSS/Atom 源；带 User-Agent；超时控制；遵守抓取频率；
    不碰需要登录/绕过反爬的内容。RSS 本身就是网站主动公开的订阅协议。
  · 异常隔离：单个源挂了不影响其他源，返回错误信息而不是抛异常崩掉页面。
  · 去重：用 guid/link 做唯一键，重复抓不会重复入库。

内置源说明：
  这里的偶像都是原创虚构角色，没有真实官方账号。内置的是几个"真实公开"
  的科技/资讯 RSS 源作为演示——用来验证抓取链路是通的。
  将来接某个 IP 的官方动态，只需在配置里加那个官方源的 URL。

对外函数：
  SOURCES            内置演示源 + 自定义源的注册表
  add_source / remove_source / list_sources  管理源
  fetch_source(url)  抓一个源，返回条目列表
  fetch_all(keys=None) 抓多个源，返回(条目, 错误列表)
  sync_to_news(items, idol_key) 把抓到的条目写进 news_feed（去重）
"""

import os
import re
import json
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

SOURCES_FILE = "fandom_data/feed_sources.json"
CACHE_FILE = "fandom_data/feed_cache.json"
TIMEOUT = 12                      # 单次请求超时秒数，防止卡死页面
MAX_ITEMS_PER_SOURCE = 8          # 每个源最多取几条，避免刷屏
FETCH_COOLDOWN_MIN = 10           # 同一源两次抓取最小间隔（分钟），控制频率
USER_AGENT = "Mozilla/5.0 (compatible; FandomDemo/1.0; +https://github.com/)"


# ===== 内置演示源（真实公开 RSS/Atom，仅用于验证抓取链路）=====
# 注意：这些是公开资讯源，不是虚构偶像的"官方账号"——只是拿来证明抓取是通的。
BUILTIN_SOURCES = [
    {"key": "sspai", "name": "少数派", "url": "https://sspai.com/feed",
     "type": "rss", "note": "科技生活资讯 · 稳定"},
    {"key": "solidot", "name": "Solidot", "url": "https://www.solidot.org/index.rss",
     "type": "rss", "note": "科技新闻速递 · 稳定"},
    {"key": "ruanyifeng", "name": "阮一峰的网络日志", "url": "https://www.ruanyifeng.com/blog/atom.xml",
     "type": "atom", "note": "Atom 格式演示 · 偶尔超时属正常网络波动"},
]


def _ensure_dir():
    if not os.path.exists("fandom_data"):
        os.makedirs("fandom_data", exist_ok=True)


# ===== 源配置管理 =====

def list_sources():
    """返回全部源：内置源 + 用户自定义源"""
    _ensure_dir()
    custom = []
    if os.path.exists(SOURCES_FILE):
        try:
            with open(SOURCES_FILE, "r", encoding="utf-8") as f:
                custom = json.load(f)
        except Exception:
            custom = []
    return BUILTIN_SOURCES + custom


def get_source(key):
    for s in list_sources():
        if s["key"] == key:
            return s
    return None


def add_source(key, name, url, feed_type="auto", note=""):
    """新增一个自定义源。feed_type: rss/atom/auto"""
    _ensure_dir()
    custom = []
    if os.path.exists(SOURCES_FILE):
        try:
            with open(SOURCES_FILE, "r", encoding="utf-8") as f:
                custom = json.load(f)
        except Exception:
            custom = []
    # 用 key 去重：同名就覆盖
    custom = [s for s in custom if s["key"] != key]
    custom.append({"key": key, "name": name.strip(), "url": url.strip(),
                   "type": feed_type, "note": note.strip()})
    with open(SOURCES_FILE, "w", encoding="utf-8") as f:
        json.dump(custom, f, ensure_ascii=False, indent=2)
    return True


def remove_source(key):
    """只能删自定义源，内置源删不掉"""
    if not os.path.exists(SOURCES_FILE):
        return False
    try:
        with open(SOURCES_FILE, "r", encoding="utf-8") as f:
            custom = json.load(f)
        before = len(custom)
        custom = [s for s in custom if s["key"] != key]
        if len(custom) < before:
            with open(SOURCES_FILE, "w", encoding="utf-8") as f:
                json.dump(custom, f, ensure_ascii=False, indent=2)
            return True
    except Exception:
        pass
    return False


# ===== 抓取频率控制（缓存上次抓取时间）=====

def _load_cache():
    _ensure_dir()
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_cache(cache):
    _ensure_dir()
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def can_fetch(key, force=False):
    """距离上次抓取是否超过冷却时间；force=True 跳过检查"""
    if force:
        return True, ""
    cache = _load_cache()
    last = cache.get(key, "")
    if not last:
        return True, ""
    try:
        elapsed = (datetime.now() - datetime.strptime(last, "%Y-%m-%d %H:%M:%S")).total_seconds() / 60
        if elapsed < FETCH_COOLDOWN_MIN:
            return False, f"距离上次抓取才 {int(elapsed)} 分钟（建议间隔 {FETCH_COOLDOWN_MIN} 分钟）"
    except Exception:
        pass
    return True, ""


def _mark_fetched(key):
    cache = _load_cache()
    cache[key] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _save_cache(cache)


# ===== XML 解析（同时支持 RSS 2.0 和 Atom）=====

# 命名空间：Atom 用 {http://www.w3.org/2005/Atom}，RSS 没有
_ATOM = "{http://www.w3.org/2005/Atom}"


def _text(el, *paths):
    """按多个候选路径找元素文本，找到第一个非空的"""
    for path in paths:
        node = el.find(path)
        if node is not None and node.text and node.text.strip():
            return node.text.strip()
    return ""


def _strip_html(text):
    """去掉 HTML 标签，只留纯文字（RSS 的 description 常带 <p> 等标签）"""
    text = re.sub(r"<[^>]+>", "", text or "")
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", text).strip()


def parse_feed(xml_bytes, feed_type="auto"):
    """
    解析 RSS/Atom XML，返回条目列表：
      [{"guid", "title", "content", "link", "published", ...}]
    feed_type='auto' 时自动判断（看根元素是不是 feed → Atom，否则 RSS）。
    """
    root = ET.fromstring(xml_bytes)
    tag = root.tag.replace(_ATOM, "")

    if tag == "feed" or feed_type == "atom":
        entries = root.findall(f"{_ATOM}entry")
        parsed = []
        for e in entries:
            link_node = e.find(f"{_ATOM}link")
            link = link_node.get("href", "") if link_node is not None else ""
            parsed.append({
                "guid": _text(e, f"{_ATOM}id") or link,
                "title": _text(e, f"{_ATOM}title"),
                "content": _strip_html(_text(e, f"{_ATOM}summary", f"{_ATOM}content")),
                "link": link,
                "published": _text(e, f"{_ATOM}updated", f"{_ATOM}published"),
            })
        return parsed[:MAX_ITEMS_PER_SOURCE]

    # RSS 2.0
    channel = root.find("channel")
    if channel is None:
        return []
    parsed = []
    for item in channel.findall("item"):
        content = _text(item, "description", "{http://purl.org/rss/1.0/modules/content/}encoded")
        parsed.append({
            "guid": _text(item, "guid") or _text(item, "link") or _text(item, "title"),
            "title": _text(item, "title"),
            "content": _strip_html(content),
            "link": _text(item, "link"),
            "published": _text(item, "pubDate"),
        })
    return parsed[:MAX_ITEMS_PER_SOURCE]


def fetch_source(source, force=False):
    """
    抓一个源。返回 (条目列表, 错误信息)。
    错误信息为空字符串表示成功；失败时条目为空、error 有说明，不抛异常。
    """
    ok, reason = can_fetch(source["key"], force=force)
    if not ok:
        return [], reason
    try:
        req = urllib.request.Request(source["url"], headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            xml_bytes = resp.read()
        items = parse_feed(xml_bytes, source.get("type", "auto"))
        _mark_fetched(source["key"])
        return items, ""
    except Exception as e:
        return [], f"{type(e).__name__}: {str(e)[:120]}"


def fetch_all(keys=None, force=False):
    """抓多个源。返回 (全部条目, [(源名, 错误), ...])"""
    sources = list_sources()
    if keys:
        sources = [s for s in sources if s["key"] in keys]
    all_items, errors = [], []
    for s in sources:
        items, err = fetch_source(s, force=force)
        if err:
            errors.append((s["name"], err))
        else:
            for it in items:
                it["source_name"] = s["name"]
                it["source_key"] = s["key"]
            all_items.extend(items)
    return all_items, errors


# ===== 同步到 news_feed（关键：去重）=====

def sync_to_news(items, idol_key):
    """
    把抓到的条目写成 news_feed 动态。
    去重逻辑：news_feed 里若已存在相同 guid（存在 title/source 组合里），就跳过。
    返回新增条数。
    """
    import news_feed
    added = 0
    existing = news_feed.load_news(idol_key)
    # 用 (标题, 来源) 做去重键——guid 没存进 news_feed，用这两个字段组合更稳
    seen = {(n.get("title", ""), n.get("source", "")) for n in existing}

    for it in items:
        title = it.get("title", "").strip()
        if not title:
            continue
        source_name = it.get("source_name", "RSS")
        if (title, source_name) in seen:
            continue
        # 抓到的条目默认当"官方动态 update"，content 截断到 500 字避免太长
        news_feed.add_news(
            idol_key=idol_key,
            title=title,
            content=(it.get("content", "") or "")[:500],
            news_type="update",
            source=source_name,
            official_url=it.get("link", ""),
        )
        seen.add((title, source_name))
        added += 1
    return added
