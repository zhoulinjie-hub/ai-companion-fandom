# -*- coding: utf-8 -*-
"""
粉丝陪伴 · 差异化前端设计（模块10）
====================================

这是让产品"一眼区别于其他 AI 聊天工具"的关键：一套专属视觉语言。

为什么需要独立的前端模块：
  · 原有 AI 伴侣是通用聊天界面，粉丝陪伴需要"追星感"——像进了偶像的私信
  · 竞品（星野/猫箱/Bubble）都是通用聊天壳，没有"追星护照/票务卡/动态转私信"的可视化
  · 把这些做成专属组件，就是产品的差异化打点

设计原则：
  · 纯 CSS + HTML，不依赖额外前端库（Streamlit 原生可控）
  · 所有颜色/字体集中在 THEME 字典，改主题只改一处
  · 每个组件是一个函数，返回 HTML 字符串，主程序 st.markdown 渲染

组件清单：
  inject_theme()         注入全局 CSS（只在粉丝模式调用）
  hero_card(idol, days)  偶像主页头图卡（头像/身份/粉丝名/入坑天数）
  chat_bubble(role,text,avatar) 私信气泡（偶像左/粉丝右，像微信）
  news_card(news, rewritten)   动态卡（原文+改写私信对照）
  ticket_card(ticket)    票务卡（倒计时+官方链接+只提醒不交易）
  passport_timeline(passport)  追星护照时间轴
  fan_badge(fan_type)    粉丝身份徽章
  ai_disclosure_bar()    AI 身份标识条（合规）
"""

# ===== 主题配置：改这里就能换整套配色 =====
THEME = {
    "primary": "#a855f7",     # 主色：梦幻紫
    "primary2": "#ec4899",    # 辅色：樱花粉
    "accent": "#22d3ee",      # 点缀：青蓝
    "bg_card": "#1e1b2e",      # 卡片背景（深色）
    "bg_card2": "#2a2540",    # 卡片背景2
    "text": "#f3f0ff",        # 主文字
    "text_dim": "#b8aecd",    # 次要文字
    "danger": "#ef4444",      # 警示红
    "success": "#34d399",     # 成功绿
    "warn": "#fbbf24",        # 提醒黄
}


def inject_theme():
    """注入粉丝陪伴专属 CSS。只在进入偶像模式时调用，不影响普通伴侣界面。"""
    t = THEME
    css = f"""
    <style>
    .fm-wrap {{ font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif; color: {t['text']}; }}
    .fm-hero {{
        background: linear-gradient(135deg, {t['primary']} 0%, {t['primary2']} 55%, {t['accent']} 140%);
        border-radius: 18px; padding: 20px 22px; margin: 8px 0 14px 0;
        box-shadow: 0 8px 28px rgba(168,85,247,.28); position: relative; overflow: hidden;
    }}
    .fm-hero::after {{
        content: ''; position: absolute; right: -30px; top: -50px; width: 160px; height: 160px;
        background: rgba(255,255,255,.12); border-radius: 50%;
    }}
    .fm-hero-name {{ font-size: 26px; font-weight: 800; letter-spacing: 1px; }}
    .fm-hero-id {{ font-size: 13px; opacity: .92; margin-top: 4px; }}
    .fm-hero-tags {{ margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap; }}
    .fm-tag {{
        background: rgba(255,255,255,.2); border: 1px solid rgba(255,255,255,.3);
        padding: 3px 12px; border-radius: 999px; font-size: 12px; backdrop-filter: blur(4px);
    }}
    .fm-days {{ font-size: 13px; font-weight: 700; }}
    .fm-bubble-row {{ display: flex; margin: 10px 0; align-items: flex-end; }}
    .fm-bubble-row.idol {{ justify-content: flex-start; }}
    .fm-bubble-row.fan {{ justify-content: flex-end; }}
    .fm-avatar {{
        width: 38px; height: 38px; border-radius: 50%; display: flex; align-items: center;
        justify-content: center; font-size: 20px; margin: 0 8px; flex-shrink: 0;
        background: linear-gradient(135deg, {t['primary']}, {t['primary2']});
        object-fit: cover; border: 2px solid rgba(255,255,255,.18);
    }}
    .fm-avatar.fan {{ background: linear-gradient(135deg, {t['accent']}, #6366f1); }}
    .fm-avatar-img {{ border-radius: 50%; object-fit: cover; vertical-align: middle; }}
    .fm-bubble {{
        max-width: 72%; padding: 10px 14px; font-size: 14px; line-height: 1.6;
        border-radius: 16px; word-break: break-word;
    }}
    .fm-bubble.idol {{ background: {t['bg_card2']}; color: {t['text']}; border-bottom-left-radius: 4px; }}
    .fm-bubble.fan {{ background: linear-gradient(135deg, {t['primary']}, {t['primary2']});
        color: #fff; border-bottom-right-radius: 4px; }}
    .fm-bubble-name {{ font-size: 11px; color: {t['text_dim']}; margin-bottom: 3px; }}
    .fm-card {{
        background: {t['bg_card']}; border: 1px solid rgba(168,85,247,.25);
        border-radius: 14px; padding: 14px 16px; margin: 10px 0;
    }}
    .fm-card-head {{ font-weight: 700; font-size: 15px; margin-bottom: 8px; display: flex; gap: 8px; align-items: center; }}
    .fm-original {{ color: {t['text_dim']}; font-size: 12.5px; border-left: 3px solid {t['text_dim']};
        padding-left: 10px; margin: 8px 0; }}
    .fm-dm {{
        background: linear-gradient(135deg, rgba(168,85,247,.18), rgba(236,72,153,.12));
        border: 1px solid rgba(168,85,247,.35); border-radius: 10px;
        padding: 10px 12px; font-size: 14px; margin-top: 8px;
    }}
    .fm-dm-label {{ font-size: 11px; color: {t['accent']}; font-weight: 700; margin-bottom: 4px; }}
    .fm-ticket {{
        background: linear-gradient(135deg, {t['bg_card2']}, {t['bg_card']});
        border: 1px solid rgba(251,191,36,.35); border-radius: 14px; padding: 14px 16px; margin: 10px 0;
    }}
    .fm-countdown {{ font-size: 22px; font-weight: 800; color: {t['warn']}; }}
    .fm-safe-note {{ font-size: 11px; color: {t['text_dim']}; margin-top: 8px; }}
    .fm-badge {{
        display: inline-block; padding: 3px 12px; border-radius: 999px; font-size: 12px; font-weight: 700;
        background: linear-gradient(135deg, {t['primary']}, {t['accent']}); color: #fff;
    }}
    .fm-disclosure {{
        background: linear-gradient(135deg, rgba(168,85,247,.14), rgba(236,72,153,.12));
        color: #6d28d9; border: 1px solid rgba(168,85,247,.28);
        font-size: 12px; font-weight: 600;
        text-align: center; padding: 8px 12px; border-radius: 8px; margin: 8px 0 16px;
    }}
    .fm-tl {{ border-left: 2px solid {t['primary']}; padding-left: 16px; margin-left: 8px; }}
    .fm-tl-item {{ position: relative; margin-bottom: 14px; font-size: 13px; }}
    .fm-tl-item::before {{
        content: ''; position: absolute; left: -22px; top: 4px; width: 10px; height: 10px;
        border-radius: 50%; background: {t['accent']}; box-shadow: 0 0 0 3px rgba(34,211,238,.2);
    }}
    .fm-tl-date {{ color: {t['accent']}; font-size: 11px; font-weight: 700; }}
    </style>
    """
    # 必须用 st.markdown 而非 components.html：后者在 iframe 里，CSS 隔离，影响不到主页面
    import streamlit as st
    st.markdown(css, unsafe_allow_html=True)


def hero_card(idol, days=None):
    """偶像主页头图卡"""
    t = THEME
    # 注意：这里必须保证每个标签独占一行且无"空白行+缩进闭合标签"，
    # 否则 st.markdown(unsafe_allow_html=True) 会把缩进的 </div> 误判成 markdown 代码块显示为字面文本。
    days_text = f'💜 一起走过 {days} 天' if (isinstance(days, int) and days >= 0) else '💜 欢迎回家'
    return (
        f'<div class="fm-wrap">'
        f'<div class="fm-hero">'
        f'<div class="fm-hero-name">{idol["icon"]} {idol["nick_name"]}</div>'
        f'<div class="fm-hero-id">{idol["identity"]}</div>'
        f'<div class="fm-hero-tags">'
        f'<span class="fm-tag">🏷️ {idol["fandom_name"]}</span>'
        f'<span class="fm-tag">👥 自称「{idol["fandom_call"]}」</span>'
        f'<span class="fm-tag fm-days">{days_text}</span>'
        f'</div></div></div>'
    )


def _render_inline(text):
    """
    气泡里的轻量行内渲染：先转义保证安全，再还原几个常用格式。
    st.markdown 不解析 HTML 标签内部的 markdown，所以 **加粗** 得自己转。
    顺序很关键：先转义（防 <script> 注入），再做替换，替换产物才是真的 HTML。
    """
    import html as _html
    import re
    s = _html.escape(str(text))
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)   # **加粗**
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)            # `代码`
    s = s.replace("\n", "<br/>")                               # 换行
    return s


def chat_bubble(role, text, avatar="🌟", name=""):
    """
    私信气泡：assistant 左、user 右。
    avatar 支持两种：emoji 字符，或 avatar.py 生成的 data URI 图片。
    图片头像走 <img>，emoji 头像走文字，自动识别。
    文本支持 **加粗**、`代码`、换行；其余 HTML 一律转义，保证安全。
    """
    import html
    is_idol = role == "assistant"
    cls = "idol" if is_idol else "fan"
    name_html = f'<div class="fm-bubble-name">{html.escape(str(name))}</div>' if name else ''
    av_cls = "" if is_idol else "fan"
    # 判断头像是图片 data URI 还是 emoji 字符
    if isinstance(avatar, str) and avatar.startswith("data:image"):
        av_html = f'<img class="fm-avatar {av_cls}" src="{avatar}" alt="头像"/>'
    else:
        av_html = f'<div class="fm-avatar {av_cls}">{avatar}</div>'
    safe_text = _render_inline(text)
    return f"""
    <div class="fm-wrap">
      <div class="fm-bubble-row {cls}">
        {av_html}
        <div class="fm-bubble {cls}">{name_html}{safe_text}</div>
      </div>
    </div>"""


def inject_global_style():
    """
    全局视觉优化（普通模式 + 偶像模式都调用）：
    统一圆角、柔和阴影、整洁的标题与按钮，让页面一眼区别于默认 Streamlit。
    只做"美化"，不改任何控件行为。
    """
    import streamlit as st
    css = """
    <style>
    .block-container { padding-top: 1.6rem; padding-bottom: 3rem; }
    [data-testid="stChatMessage"] { border-radius: 14px; }
    .stButton > button { border-radius: 10px; transition: all .18s ease; }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,.12); }
    h1 { letter-spacing: 1px; }
    [data-testid="stSidebar"] .stButton > button { font-size: 13px; }
    hr { border: 0; border-top: 1px solid rgba(150,150,180,.2); margin: 1rem 0; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def brand_header(title, subtitle, accent="#a855f7"):
    """顶部品牌标题条：渐变文字 + 副标题，作为产品差异化视觉"""
    return f"""
    <div class="fm-wrap" style="padding:14px 20px;border-radius:16px;
         background:linear-gradient(100deg,{accent}22,transparent);margin-bottom:10px;">
      <div style="font-size:24px;font-weight:800;letter-spacing:1px;
           background:linear-gradient(90deg,{accent},#ec4899);
           -webkit-background-clip:text;-webkit-text-fill-color:transparent;">{title}</div>
      <div style="font-size:12px;color:#b8aecd;margin-top:4px;">{subtitle}</div>
    </div>"""


def news_card(news, rewritten=""):
    """动态卡：原文 + 改写私信对照"""
    import html
    type_label = news_feed_type(news.get("type"))
    title = html.escape(news.get("title", ""))
    content = html.escape(news.get("content", ""))
    source = html.escape(news.get("source", "官方"))
    dm_html = ''
    if rewritten:
        dm_html = f"""
        <div class="fm-dm">
          <div class="fm-dm-label">💬 TA 发给你的私信</div>
          {html.escape(rewritten)}
        </div>"""
    else:
        dm_html = '<div class="fm-safe-note">（还没转成私信，点下方按钮让 TA 用口吻告诉你）</div>'
    return f"""
    <div class="fm-wrap">
      <div class="fm-card">
        <div class="fm-card-head">{type_label} {title}</div>
        <div class="fm-original">📰 {source}：{content}</div>
        {dm_html}
      </div>
    </div>"""


def news_feed_type(t):
    """把类型 key 转成中文标签（放这里避免循环 import）"""
    return {
        "update": "📢 官方动态", "material": "🎴 物料", "schedule": "📅 行程",
        "ticket": "🎫 票务", "live": "🔴 直播",
    }.get(t, "📢 动态")


def ticket_card(ticket):
    """票务卡：倒计时 + 官方链接 + 只提醒不交易"""
    import html
    import ticket_cards as tc
    status = tc.status_of(ticket)
    title = html.escape(ticket.get("title", ""))
    note = html.escape(ticket.get("note", ""))
    sale = ticket.get("sale_time", "待公布")
    url = ticket.get("official_url", "")
    link = ''
    if url:
        link = f'<a href="{html.escape(url)}" target="_blank" style="color:#22d3ee;font-size:12px;">🔗 前往官方页面 ↗</a>'
    return f"""
    <div class="fm-wrap">
      <div class="fm-ticket">
        <div class="fm-card-head">🎫 {title}</div>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:13px;color:#b8aecd;">开售时间：{sale}</span>
          <span class="fm-countdown">{status}</span>
        </div>
        <div class="fm-safe-note">{note}</div>
        {link}
        <div class="fm-safe-note">🛡️ 仅作提醒，本工具不售票、不收款 · 价格与余票以官方为准</div>
      </div>
    </div>"""


def passport_timeline(passport):
    """追星护照时间轴"""
    import html
    items = []
    if passport.get("join_date"):
        items.append(f'<div class="fm-tl-item"><div class="fm-tl-date">{passport["join_date"]}</div>正式入坑，成为家人</div>')
    for c in passport.get("concerts", []):
        when = c.get("date", "")
        city = c.get("city", "")
        who = c.get("name", "")
        items.append(f'<div class="fm-tl-item"><div class="fm-tl-date">{when}</div>看了「{html.escape(who)}」{("· " + html.escape(city)) if city else ""}</div>')
    for m in passport.get("merch", []):
        items.append(f'<div class="fm-tl-item"><div class="fm-tl-date">{m.get("date", "")}</div>收藏了「{html.escape(m.get("name", ""))}」</div>')
    for n in passport.get("notes", []):
        items.append(f'<div class="fm-tl-item">{html.escape(n)}</div>')
    if not items:
        return '<div class="fm-wrap"><div class="fm-card">护照还是空的，去左边填填入坑时间吧 💜</div></div>'
    return f'<div class="fm-wrap"><div class="fm-tl">{"".join(items)}</div></div>'


def fan_badge(fan_type_key):
    """粉丝身份徽章"""
    import fandom_lang as fl
    name = fl.get_fan_type(fan_type_key)["name"]
    return f'<div class="fm-wrap"><span class="fm-badge">🎖️ {name}</span></div>'


def ai_disclosure_bar():
    """AI 身份标识条（合规必备）"""
    import boundary_rules as br
    return f'<div class="fm-wrap"><div class="fm-disclosure">{br.AI_DISCLOSURE}</div></div>'
