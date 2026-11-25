# -*- coding: utf-8 -*-
"""
模块5：主动陪伴 —— 拉取式主动消息
==================================
Streamlit 是"用户打开页面才运行"的模式，服务器没法在后台主动推送。
所以这里做的是"拉取式"：用户一打开页面，脚本检查是否该主动说点什么，
命中触发器且不在冷却期，就生成一条主动消息显示出来。

四类触发器：
    ① 承诺兑现：AI 答应过的事到点了
    ② 久别重逢：好几天没聊，主动打招呼
    ③ 时段问候：早上好 / 这么晚了还不睡
    ④ 情绪关心：记得你上次情绪低落，问问近况

两道闸门（防止骚扰）：
    闸门A：静音开关，用户随时能关
    闸门B：冷却时间，刚主动过就不再打扰
"""

import os
import json
from datetime import datetime

STATE_FILE = "proactive/proactive_state.json"
TIME_FMT = "%Y-%m-%d %H:%M:%S"

DEFAULT_STATE = {
    "muted": False,              # 闸门A：用户是否静音
    "last_proactive_at": "",     # 上次主动消息时间（闸门B：冷却用）
    "last_interaction": "",      # 上次真实聊天时间（判断久别重逢）
    "promises": []               # 承诺列表：[{"text":..., "due":..., "done":bool}]
}

# 冷却时长（小时）：主动过一次后，这段时间内不再主动
COOLDOWN_HOURS = 6
# 久别重逢门槛（小时）：超过这个时长没聊，就算"好久不见"
REUNION_HOURS = 48


def _ensure_file():
    """确保文件夹和 json 存在。注意：直接写文件，不调 save_state，避免递归"""
    if not os.path.exists("proactive"):
        os.mkdir("proactive")
    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_STATE, f, ensure_ascii=False, indent=2)


def load_state():
    """读取状态，用默认值打底再覆盖，兼容字段缺失的老文件"""
    _ensure_file()
    state = DEFAULT_STATE.copy()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state.update(json.load(f))
    except Exception:
        pass
    return state


def save_state(state):
    """写回状态文件"""
    _ensure_file()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def set_muted(muted):
    """开关静音。返回当前静音状态"""
    state = load_state()
    state["muted"] = bool(muted)
    save_state(state)
    return state["muted"]


def record_interaction():
    """用户真实发了一条消息时调用，刷新'上次聊天时间'"""
    state = load_state()
    state["last_interaction"] = datetime.now().strftime(TIME_FMT)
    save_state(state)


def add_promise(text, hours_later):
    """
    记一条承诺：hours_later 小时后到期。
    比如 AI 说"明天提醒你交材料"，就记一条 24 小时后的承诺。
    """
    text = text.strip()
    if not text:
        return False
    from datetime import timedelta
    due = (datetime.now() + timedelta(hours=float(hours_later))).strftime(TIME_FMT)
    state = load_state()
    state["promises"].append({"text": text, "due": due, "done": False})
    save_state(state)
    return True


def _hours_since(time_str):
    """距离某个时间点过了多少小时；时间为空或格式坏了返回 None"""
    if not time_str:
        return None
    try:
        delta = datetime.now() - datetime.strptime(time_str, TIME_FMT)
        return delta.total_seconds() / 3600
    except Exception:
        return None


def check_trigger():
    """
    检查是否该主动发消息。返回 None 表示不发；否则返回一个触发信息字典：
    {"kind": "承诺/重逢/时段/关心", "hint": "给大模型的具体提示"}
    两道闸门（静音、冷却）在这里统一拦截。
    """
    state = load_state()

    # 闸门A：用户静音了，一律不发
    if state["muted"]:
        return None

    # 闸门B：冷却期内不发（刚主动过就别再打扰）
    hours_since_proactive = _hours_since(state["last_proactive_at"])
    if hours_since_proactive is not None and hours_since_proactive < COOLDOWN_HOURS:
        return None

    now = datetime.now()

    # 触发器①：有没有到期的承诺
    for p in state["promises"]:
        if p.get("done"):
            continue
        try:
            due_time = datetime.strptime(p["due"], TIME_FMT)
            if now >= due_time:
                return {"kind": "承诺兑现", "hint": f"你之前答应过用户：{p['text']}。现在到时间了，自然地提一下。"}
        except Exception:
            continue

    # 触发器②：久别重逢
    hours_away = _hours_since(state["last_interaction"])
    if hours_away is not None and hours_away >= REUNION_HOURS:
        return {"kind": "久别重逢", "hint": f"用户已经 {int(hours_away)} 小时没来找你了，自然地打个招呼，别太刻意。"}

    # 触发器③：时段问候（只在整点附近命中一次，避免每刷屏都发）
    hour = now.hour
    if hour == 7:
        return {"kind": "时段问候", "hint": "现在是早上，跟用户说声早，关心一下今天的状态。"}
    if hour >= 22 or hour < 1:
        return {"kind": "时段问候", "hint": "现在很晚了，温和地提醒用户注意休息，不要说教。"}

    # 触发器④：情绪关心——读 emotion 模块的状态，上次心情低落就问候
    try:
        import emotion
        emo = emotion.load_state()
        if emo.get("pleasure", 0) < -0.3:
            return {"kind": "情绪关心", "hint": "你记得用户上次心情不太好，自然地问问他现在怎么样了。"}
    except Exception:
        pass

    return None


def mark_proactive(trigger_kind):
    """
    发过主动消息后调用：记下时间（启动冷却），并把兑现过的承诺标记完成。
    """
    state = load_state()
    state["last_proactive_at"] = datetime.now().strftime(TIME_FMT)
    if trigger_kind == "承诺兑现":
        now = datetime.now()
        for p in state["promises"]:
            if not p.get("done"):
                try:
                    if now >= datetime.strptime(p["due"], TIME_FMT):
                        p["done"] = True
                except Exception:
                    pass
    save_state(state)


# 生成主动消息时给大模型的提示词模板
PROACTIVE_PROMPT = """你现在是 {name}（{identity}），性格：{nature}。
此刻用户刚打开页面，由你主动发一条消息开场。

触发原因：{kind}
具体要求：{hint}

你记得的关于用户的事：
{memories}

你此刻的心情：{mood}

要求：
1. 只输出一条你要发给用户的消息，像微信聊天一样简短自然（1-2句）
2. 不要有任何场景描述、动作描写、括号旁白
3. 不要解释"我为什么发这条消息"，直接像真的惦记他一样开口
4. 匹配用户的语言，可以用一两个 emoji
5. 如果记忆里有相关的事，可以自然带一句，显得你真的记得"""
