# -*- coding: utf-8 -*-
"""
模块4：情感状态 —— PAD 情绪三维 + 双关系数值
============================================
让 AI 有"心情"，和用户的关系会随互动慢慢变化，而且用户看得见。

情绪模型：PAD（心理学经典模型）
    P 愉悦度 Pleasure : -1(不开心) ~ +1(开心)
    A 唤醒度 Arousal  : -1(平静)   ~ +1(激动)
    D 支配度 Dominance: -1(被动)   ~ +1(主动)

关系模型：两条独立的线
    好感度 affinity : 短期情绪，久不聊会衰减
    亲密度 intimacy : 长期积累，只增不减

数据单独存 emotion/emotion_state.json，跟记忆一样跨会话持久。
"""

import os
import json
from datetime import datetime

STATE_FILE = "emotion/emotion_state.json"

# 初始状态：中性情绪 + 中等好感 + 零亲密
DEFAULT_STATE = {
    "pleasure": 0.0,
    "arousal": 0.0,
    "dominance": 0.0,
    "affinity": 50,
    "intimacy": 0,
    "last_interaction": ""   # 上次互动时间，用来算好感度衰减
}


def _ensure_file():
    """确保 emotion 文件夹和 json 文件存在"""
    if not os.path.exists("emotion"):
        os.mkdir("emotion")
    if not os.path.exists(STATE_FILE):
        # 注意：这里直接写文件，不能调用 save_state()
        # 因为 save_state() 也会调 _ensure_file()，互相调用会无限递归
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_STATE, f, ensure_ascii=False, indent=2)


def load_state():
    """
    读取情绪状态。用 DEFAULT_STATE 打底再覆盖文件内容，
    这样以后新增字段，老文件也不会缺字段报错（向后兼容）。
    """
    _ensure_file()
    state = DEFAULT_STATE.copy()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state.update(json.load(f))
    except Exception:
        pass
    return state


def save_state(state):
    """把情绪状态写回 json 文件"""
    _ensure_file()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _clamp(value, low, high):
    """把数值卡在 [low, high] 区间里，防止情绪/关系数值跑出界"""
    return max(low, min(high, value))


def apply_delta(delta):
    """
    根据一轮对话的"情绪增量"更新状态。
    delta 形如 {"pleasure": 0.3, "affinity": 2, ...}，缺的字段按 0 处理。
    返回更新后的完整状态。
    """
    state = load_state()

    # P 三维：累加增量后卡在 -1 ~ 1
    for key in ("pleasure", "arousal", "dominance"):
        state[key] = round(_clamp(state[key] + float(delta.get(key, 0)), -1, 1), 3)

    # 好感度：0 ~ 100
    state["affinity"] = int(_clamp(state["affinity"] + int(delta.get("affinity", 0)), 0, 100))
    # 亲密度：只增不减——负增量直接忽略（这是它和好感度的本质区别）
    intimacy_gain = max(0, int(delta.get("intimacy", 0)))
    state["intimacy"] = int(_clamp(state["intimacy"] + intimacy_gain, 0, 100))

    # 记录这次互动时间，供好感度衰减用
    state["last_interaction"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_state(state)
    return state


def decay_affinity_if_needed():
    """
    好感度随时间衰减：每隔一天 -2，最低降到 0。
    亲密度不受影响——真实关系里，熟悉感不会因为你几天没联系就消失。
    返回是否发生了衰减。
    """
    state = load_state()
    last = state.get("last_interaction", "")
    if not last:
        return False
    try:
        days = (datetime.now() - datetime.strptime(last, "%Y-%m-%d %H:%M:%S")).days
    except Exception:
        return False
    if days <= 0:
        return False
    old = state["affinity"]
    state["affinity"] = int(_clamp(old - 2 * days, 0, 100))
    save_state(state)
    return state["affinity"] != old


def describe_mood(state=None):
    """把三个数字翻译成一句人话，方便界面显示和塞进提示词"""
    state = state or load_state()
    p, a, d = state["pleasure"], state["arousal"], state["dominance"]

    p_txt = "开心愉悦" if p > 0.3 else ("有点低落" if p < -0.3 else "情绪平稳")
    a_txt = "比较兴奋" if a > 0.3 else ("安静慵懒" if a < -0.3 else "状态平和")
    d_txt = "主动热情" if d > 0.3 else ("略显被动" if d < -0.3 else "不卑不亢")
    return f"{p_txt}、{a_txt}、{d_txt}"


def format_for_prompt(state=None):
    """把情绪和关系状态拼成一段文字，注入系统提示词让 AI 有分寸地回应"""
    state = state or load_state()
    return (
        f"当前心情：{describe_mood(state)}\n"
        f"对用户的态度：好感度 {state['affinity']}/100，亲密度 {state['intimacy']}/100。\n"
        f"请根据心情和关系亲疏调整语气：关系越亲密越可以放松亲近，"
        f"好感度低时保持礼貌距离，低落时语气放缓。不要直接报出这些分数。"
    )


def render_radar_html(state=None):
    """
    生成 PAD 三维雷达图的 HTML（纯 SVG，不依赖任何第三方图表库）。
    三个轴：P 愉悦度（正上）、A 唤醒度（右下）、D 支配度（左下）。
    数值 -1~1 映射到半径 0~R，画成三角形雷达图。
    返回完整 HTML 片段，用 st.components.v1.html() 渲染即可。
    """
    import math
    state = state or load_state()
    cx, cy, R = 150, 118, 88

    def point(angle_deg, value):
        """把某个轴上的值换成 SVG 坐标，value 范围 -1~1"""
        radius = (value + 1) / 2 * R          # -1->0, +1->R
        rad = math.radians(angle_deg)
        return cx + radius * math.cos(rad), cy + radius * math.sin(rad)

    axes = [("P", "愉悦", -90), ("A", "唤醒", 30), ("D", "支配", 150)]
    vals = [state["pleasure"], state["arousal"], state["dominance"]]

    # 三层网格三角形：0.33 / 0.66 / 1.0
    grid = ""
    for level in (0.33, 0.66, 1.0):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in
                       (point(a, -1 + 2 * level) for _, _, a in axes))
        grid += (f'<polygon points="{pts}" fill="none" stroke="#d8d8d8" '
                 f'stroke-width="1"/>')

    # 三条轴线 + 轴标签
    lines = ""
    for short, name, angle in axes:
        x, y = point(angle, 1)
        lx, ly = point(angle, 1.35)
        lines += (f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" '
                  f'stroke="#bbb" stroke-width="1"/>')
        lines += (f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" '
                  f'dominant-baseline="middle" font-size="13" fill="#444">'
                  f'{short} {name}</text>')

    # 数据多边形：把三个当前值连起来
    data_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in
                        (point(a, v) for (_, _, a), v in zip(axes, vals)))
    dots = ""
    for (_, _, angle), v in zip(axes, vals):
        x, y = point(angle, v)
        dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#e0245e"/>'

    svg = f'''<svg viewBox="0 0 300 236" width="100%" height="100%"
    xmlns="http://www.w3.org/2000/svg">
{grid}{lines}
<polygon points="{data_pts}" fill="rgba(224,36,94,0.22)" stroke="#e0245e" stroke-width="2"/>
{dots}
<text x="150" y="232" text-anchor="middle" font-size="12" fill="#888">
心情：{describe_mood(state)}</text>
</svg>'''
    return f'<div style="font-family:sans-serif">{svg}</div>'


# 让大模型评估"这一轮对话让 AI 的情绪/关系发生了多大变化"的提示词
EVALUATE_PROMPT = """你是情感分析器。请判断下面这轮对话会让"AI 对用户的情绪和关系"产生怎样的变化。

打分规则：
- pleasure（愉悦度变化）：用户的话让 AI 开心为正、难过/冒犯为负，范围 -0.5 ~ 0.5
- arousal（唤醒度变化）：让用户/话题兴奋为正、平淡为负，范围 -0.5 ~ 0.5
- dominance（支配度变化）：用户尊重/认可 AI 为正、压制/贬低为负，范围 -0.5 ~ 0.5
- affinity（好感度变化）：友好的正数，冷漠冒犯的负数，范围 -10 ~ 10
- intimacy（亲密度变化）：只有用户分享秘密、心事、Personal 深层信息时才给 1~5，普通聊天给 0。不能是负数。

用户：{user}
AI：{assistant}

只返回 JSON 对象，不要任何解释，格式：
{{"pleasure": 0, "arousal": 0, "dominance": 0, "affinity": 0, "intimacy": 0}}"""
