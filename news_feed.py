# -*- coding: utf-8 -*-
"""
粉丝陪伴 · 动态抓取与口吻转译（模块4）
========================================

解决问题：粉丝想收到偶像的"私信"，但真正的官方动态是干巴巴的公告。
这个模块把"官方动态"改写成"偶像本人发的私信口吻"——这是让粉丝
感觉"加了本人联系方式"的关键一步。

第一版策略（先打通技术，不接真实爬虫）：
  · 动态数据先用"手动喂"的方式，内置几条示例，也能手动新增
  · sources（官方源）在档案库里已占位，将来接真爬虫时填这里
  · 核心验证的是"转译"这一步：公告 → 偶像口吻私信

数据和代码分开：动态存 JSON，加动态不用改主程序。
不做真实爬取的原因：① 各平台反爬 ② 版权 ③ 第一阶段先验证体验是否成立。
"""

import os
import json
from datetime import datetime

FEED_FILE = "fandom_data/news_feed.json"

# 动态类型：不同类型在前端显示不同图标
NEWS_TYPES = {
    "update": "📢 官方动态",
    "material": "🎴 物料",
    "schedule": "📅 行程",
    "ticket": "🎫 票务",
    "live": "🔴 直播",
}


def _ensure_file():
    """确保文件夹和 json 存在。直接写文件，不调 save，避免递归"""
    if not os.path.exists("fandom_data"):
        os.makedirs("fandom_data", exist_ok=True)
    if not os.path.exists(FEED_FILE):
        with open(FEED_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def load_news(idol_key=None):
    """读取动态列表；传 idol_key 就只返回该偶像的。按时间倒序。"""
    _ensure_file()
    try:
        with open(FEED_FILE, "r", encoding="utf-8") as f:
            items = json.load(f)
    except Exception:
        return []
    if idol_key:
        items = [n for n in items if n.get("idol_key") == idol_key]
    return sorted(items, key=lambda x: x.get("time", ""), reverse=True)


def save_news(items):
    """写回动态列表"""
    _ensure_file()
    with open(FEED_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def add_news(idol_key, title, content, news_type="update", source="官方", official_url="", time_str=None):
    """
    手动喂一条动态（真实接入爬虫后，爬虫也是调这个函数存进去）。
    返回这条动态的 id。
    """
    items = load_news()
    news_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(len(items) % 100)
    items.append({
        "id": news_id,
        "idol_key": idol_key,
        "type": news_type,
        "title": title,
        "content": content,
        "source": source,
        "official_url": official_url,
        "time": time_str or datetime.now().strftime("%Y-%m-%d %H:%M"),
        "rewritten": "",       # 改写后的私信口吻，改写过才有值
        "pushed": False,       # 是否已推送过，防止重复私信
    })
    save_news(items)
    return news_id


def delete_news(news_id):
    """按 id 删除一条动态"""
    items = load_news()
    before = len(items)
    items = [n for n in items if n.get("id") != news_id]
    if len(items) < before:
        save_news(items)
        return True
    return False


def mark_rewritten(news_id, text):
    """把改写结果存回动态，避免每次打开都重新调模型烧钱"""
    items = load_news()
    for n in items:
        if n.get("id") == news_id:
            n["rewritten"] = text
            break
    save_news(items)


def mark_pushed(news_id):
    """标记这条动态已推送过，防止重复私信骚扰粉丝"""
    items = load_news()
    for n in items:
        if n.get("id") == news_id:
            n["pushed"] = True
            break
    save_news(items)


def get_unpushed(idol_key):
    """取出某偶像还没推送过的动态，供主动私信模块用"""
    return [n for n in load_news(idol_key) if not n.get("pushed")]


# ===== 口吻转译：把官方公告改写成偶像私信 =====

REWRITE_PROMPT = """你是{name}（{identity}），说话风格：{nature}。

下面是一条关于你的官方动态。请把它改写成"你亲自发给粉丝的私信"。

原始动态：
【{type}】{title}
{source}：{content}

粉丝群体叫「{fandom_name}」，你平时叫粉丝"{idol_call}"。

要求：
1. 用第一人称，就像你自己在跟粉丝说话
2. 只输出私信正文，1-3句话，像微信一样自然
3. 保留原动态里的关键信息（时间、地点、事项），不许编造新事实
4. 带上你的说话风格，但不要场景/动作描写
5. 不要出现"据官方消息""据悉"这种第三人称措辞——你就是本人
6. 如果原动态是票务/行程，结尾自然带一句提醒粉丝留意
7. 不要提到任何雷区话题

现在只输出这条私信："""


def rewrite_to_dm(news, idol, client, model="deepseek-chat"):
    """
    把一条动态改写成偶像口吻的私信。
    news    动态字典
    idol    偶像档案字典
    client  OpenAI 客户端（由主程序传入，这里不自己创建，方便测试）
    返回改写后的文本；失败返回 None，绝不让主流程崩掉。
    """
    try:
        prompt = REWRITE_PROMPT.format(
            name=idol["nick_name"],
            identity=idol["identity"],
            nature=idol["nature"],
            type=NEWS_TYPES.get(news.get("type"), "动态"),
            title=news.get("title", ""),
            source=news.get("source", "官方"),
            content=news.get("content", ""),
            fandom_name=idol.get("fandom_name", ""),
            idol_call=idol.get("idol_call", "各位"),
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            temperature=0.8   # 转译要有点口吻发挥，但不能太飘
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print("动态转译失败（已忽略）:", e)
        return None


# ===== 内置的示例动态（原创角色的假数据，演示用）=====
# 用一个函数返回，避免污染真实数据；界面上点"载入示例动态"才写进去。
def demo_news_for(idol_key):
    """给某个偶像返回几条示例动态（原创虚构，演示用）"""
    demos = {
        "virtual_singer": [
            {"type": "schedule", "title": "新歌《星轨》定档",
             "content": "第三支单曲《星轨》将于本周六20:00全平台上线，敬请期待。",
             "source": "星遥official"},
            {"type": "material", "title": "练习室花絮公开",
             "content": "新歌练习室版视频今日发布，含一段未公开的即兴哼唱。",
             "source": "B站 星遥official"},
            {"type": "live", "title": "周六直播预告",
             "content": "本周六21:00将在B站开播，聊聊新歌背后的故事。",
             "source": "后援会公告"},
        ],
        "novel_hero": [
            {"type": "update", "title": "番外篇更新通知",
             "content": "作者宣布将在下月更新一篇关于沈砚的行旅番外。",
             "source": "作者微博"},
            {"type": "material", "title": "新版插画公开",
             "content": "典藏版第3册将附赠一张全新插画。",
             "source": "连载平台"},
        ],
        "vtuber": [
            {"type": "live", "title": "今晚临时加播",
             "content": "阿栗今晚22:00临时加播，玩新上的恐怖游戏。",
             "source": "B站 阿栗 动态"},
            {"type": "schedule", "title": "本周休息公告",
             "content": "本周三、周四休息，周五恢复直播。",
             "source": "粉丝群公告"},
        ],
    }
    return demos.get(idol_key, [])
