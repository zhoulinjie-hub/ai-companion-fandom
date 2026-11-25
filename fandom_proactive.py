# -*- coding: utf-8 -*-
"""
粉丝陪伴 · 主动私信推送（模块8）
==================================

把偶像的"新动态 / 票务开售 / 粉丝生日 / 久别重逢"变成一条主动私信，
让粉丝感觉"是本人主动来找我聊"，而不是刷资讯。

沿用原有 proactive.py 的"拉取式"思路：
  Streamlit 没有后台推送，用户打开页面时才检查触发器。
  两道闸门：静音开关 + 冷却时间，防止骚扰。

和 proactive.py 独立分开：粉丝场景的触发条件和普通伴侣不同，
混在一起会让原来的主动陪伴逻辑变乱。
"""

import os
import json
from datetime import datetime

STATE_FILE = "fandom_data/fandom_proactive_state.json"
TIME_FMT = "%Y-%m-%d %H:%M:%S"

DEFAULT_STATE = {
    "muted": False,
    "last_proactive_at": "",
    "last_interaction": "",
    "pushed_news_ids": [],   # 已经推送过的动态 id，防重复
    "birthday": "",          # 粉丝生日 MM-DD
    "birthday_pushed_year": "",  # 今年生日已推过，防一年内重复
}

COOLDOWN_HOURS = 6
REUNION_HOURS = 72


def _ensure_file():
    if not os.path.exists("fandom_data"):
        os.makedirs("fandom_data", exist_ok=True)
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_STATE, f, ensure_ascii=False, indent=2)


def load_state():
    _ensure_file()
    state = DEFAULT_STATE.copy()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state.update(json.load(f))
    except Exception:
        pass
    return state


def save_state(state):
    _ensure_file()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def set_muted(muted):
    state = load_state()
    state["muted"] = bool(muted)
    save_state(state)
    return state["muted"]


def set_birthday(mm_dd):
    """设置粉丝生日，格式 MM-DD"""
    mm_dd = (mm_dd or "").strip()
    if mm_dd:
        try:
            datetime.strptime("2000-" + mm_dd, "%Y-%m-%d")
        except Exception:
            return False, "生日格式应为 MM-DD，比如 11-25"
    state = load_state()
    state["birthday"] = mm_dd
    save_state(state)
    return True, ""


def record_interaction():
    state = load_state()
    state["last_interaction"] = datetime.now().strftime(TIME_FMT)
    save_state(state)


def _hours_since(time_str):
    if not time_str:
        return None
    try:
        return (datetime.now() - datetime.strptime(time_str, TIME_FMT)).total_seconds() / 3600
    except Exception:
        return None


def check_trigger(idol_key, unpushed_news=None, tickets=None):
    """
    检查该不该主动发一条私信。
    返回 {"kind":..., "hint":..., "news":可选} 或 None。
    优先级：新动态 > 票务 > 生日 > 久别，一次只发一类，不刷屏。
    """
    state = load_state()
    if state["muted"]:
        return None
    hours_since = _hours_since(state["last_proactive_at"])
    if hours_since is not None and hours_since < COOLDOWN_HOURS:
        return None

    # ① 新动态：还没推送过的最新一条
    for news in (unpushed_news or []):
        if news.get("id") not in state["pushed_news_ids"]:
            return {
                "kind": "新动态",
                "hint": "有一条刚更新的动态，用你自己的口吻自然地告诉粉丝，别像发公告。",
                "news": news,
            }

    # ② 票务开售（3天内）
    for t in (tickets or []):
        sale = t.get("sale_time", "")
        if not sale:
            continue
        try:
            d = datetime.strptime(sale, "%Y-%m-%d %H:%M")
            days = (d - datetime.now()).days
            if 0 <= days <= 3:
                return {
                    "kind": "票务提醒",
                    "hint": f"{t['title']} 快开售了（{sale}），提醒粉丝去官方渠道看，别催促消费、别自己编链接。",
                }
        except Exception:
            continue

    # ③ 粉丝生日（一年一次）
    if state["birthday"]:
        today = datetime.now().strftime("%m-%d")
        year = str(datetime.now().year)
        if today == state["birthday"] and state["birthday_pushed_year"] != year:
            return {
                "kind": "生日祝福",
                "hint": "今天是粉丝的生日，真诚地祝一句，像朋友一样，别太煽情、别提消费。",
            }

    # ④ 久别重逢
    hours_away = _hours_since(state["last_interaction"])
    if hours_away is not None and hours_away >= REUNION_HOURS:
        return {
            "kind": "久别重逢",
            "hint": f"粉丝有 {int(hours_away)} 小时没来了，自然地打个招呼，带一点'好久不见'的感觉。",
        }

    return None


def mark_proactive(trigger):
    """发过后登记：冷却 + 记推送过的动态 id + 记生日年份"""
    state = load_state()
    state["last_proactive_at"] = datetime.now().strftime(TIME_FMT)
    if trigger.get("kind") == "新动态" and trigger.get("news"):
        nid = trigger["news"].get("id")
        if nid and nid not in state["pushed_news_ids"]:
            state["pushed_news_ids"].append(nid)
    if trigger.get("kind") == "生日祝福":
        state["birthday_pushed_year"] = str(datetime.now().year)
    save_state(state)


# 生成主动私信时给模型的提示词
PROACTIVE_DM_PROMPT = """你是{name}（{identity}），风格：{nature}。
此刻给粉丝发一条主动私信。

触发原因：{kind}
具体要求：{hint}

{rules}

粉丝群体叫「{fandom_name}」，你称呼粉丝"{idol_call}"。
{if_news}相关内容：{news_detail}{end_news}

要求：
1. 只输出私信正文，1-3句，像微信一样自然
2. 第一人称，像你本人主动发的，不要"据官方消息"
3. 不要场景/动作描写，不要解释为什么发这条
4. 信息以给出的内容为准，不许编造未公开的事
5. 严格遵守上面的分寸红线

现在只输出这条私信："""
