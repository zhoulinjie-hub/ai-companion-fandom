# -*- coding: utf-8 -*-
"""
互动特效模块：
============
让粉丝陪伴"有反应"——发爱心下爱心雨、应援撒花、点赞计数器。

为什么单独成文件：
  · 特效是纯前端 CSS 动画，和业务逻辑无关，分开好维护
  · 用 session_state 存"待播放的特效"，按钮触发、页面顶部消费一次，
    这样无论侧边栏还是聊天区触发，动画都统一在页面顶层播放

技术要点（Streamlit 的特殊性）：
  · Streamlit 每次交互都会把整个脚本从上往下重跑一遍
  · CSS 动画要"重新播放"，必须让 DOM 元素带一个全新的 key/id
  · 所以每次触发生成一个 nonce，HTML 里带上它 → React 认为是新元素 → 动画重播

对外接口：
  request(st, kind)     请求播放一个特效（爱心雨/撒花/烟花/比心）
  consume(st)           在页面顶部调用，播放并清除请求（只播一次）
  render_like_bar(st)   互动按钮条：发爱心 / 应援撒花 / 点赞
  like_state()          读取点赞数等状态
"""

import random

# ===== 特效类型 → 配置 =====
EFFECTS = {
    "heart":  {"chars": ["❤️", "💕", "💗", "💖", "💘", "💝"], "count": 26, "label": "爱心雨"},
    "confetti":{"chars": ["🎉", "🎊", "✨", "🌟", "💫", "🎈"], "count": 30, "label": "应援撒花"},
    "firework":{"chars": ["✨", "💥", "🌟", "💫", "🔥"], "count": 22, "label": "烟花"},
    "clap":   {"chars": ["👏", "🙌", "💪", "🔥", "⭐"], "count": 18, "label": "打call"},
}

STATE_KEY = "fx_request"
LIKES_KEY = "fx_likes"


def request(st, kind):
    """请求播放一个特效。存进 session_state，等页面顶部 consume 播放。"""
    if kind not in EFFECTS:
        return
    # nonce 保证每次都是"新"动画，能重复播放
    st.session_state[STATE_KEY] = {"kind": kind, "nonce": random.randint(1, 10 ** 9)}


def _build_effect_html(kind, nonce):
    """生成一个自播放、自清理的全屏特效 HTML"""
    cfg = EFFECTS[kind]
    pieces = []
    for i in range(cfg["count"]):
        ch = random.choice(cfg["chars"])
        left = random.uniform(0, 100)
        delay = random.uniform(0, 1.6)
        duration = random.uniform(2.6, 4.6)
        size = random.randint(18, 38)
        drift = random.randint(-60, 60)
        pieces.append(
            f'<span class="fx-p{ nonce }" style="left:{left:.1f}%;font-size:{size}px;'
            f'animation-delay:{delay:.2f}s;animation-duration:{duration:.2f}s;'
            f'--drift:{drift}px">{ch}</span>'
        )
    body = "".join(pieces)
    # 动画结束后把整层移除，避免遮住页面
    return f"""
<div class="fx-layer-{nonce}">
<style>
.fx-layer-{nonce} {{ position:fixed; inset:0; z-index:9999; pointer-events:none; overflow:hidden; }}
.fx-p{nonce} {{ position:absolute; top:-12%; opacity:0;
  animation-name:fxfall-{nonce}; animation-timing-function:linear; animation-fill-mode:forwards; }}
@keyframes fxfall-{nonce} {{
  0% {{ transform:translateY(0) translateX(0) rotate(0deg); opacity:0; }}
  8% {{ opacity:1; }}
  100% {{ transform:translateY(115vh) translateX(var(--drift)) rotate(420deg); opacity:0; }}
}}
</style>
{body}
</div>
<script>
// 动画播完后移除节点，防止 DOM 堆积
setTimeout(function(){{
  var el = document.querySelector('.fx-layer-{nonce}');
  if (el) el.remove();
}}, 5200);
</script>
"""


def consume(st):
    """
    页面顶部调用：如果有待播放特效就播放（并消费掉）。
    放在页面最前面，保证特效浮层盖在所有内容之上。
    """
    req = st.session_state.pop(STATE_KEY, None)
    if not req:
        return
    import streamlit as _st
    html = _build_effect_html(req["kind"], req["nonce"])
    _st.markdown(html, unsafe_allow_html=True)


def render_like_bar(st, compact=False, scope="bar"):
    """
    互动按钮条：发爱心 / 应援撒花 / 打call + 点赞计数。
    触发的特效由页面顶部的 consume() 统一播放。

    scope 用来区分"同一页面里出现多条应援栏"的场景：
    进入偶像模式后，侧边栏和主聊天区会各显示一条，若 key 相同 Streamlit
    会报 DuplicateElementKey。给每条传不同 scope（如 side / main）即可。
    """
    likes = st.session_state.get(LIKES_KEY, 0)
    cols = st.columns(4 if not compact else 2)

    with cols[0]:
        if st.button("💗 发爱心", width="stretch", key=f"fx_love_{scope}"):
            request(st, "heart")
            st.session_state[LIKES_KEY] = likes + 1
            st.toast("爱心雨来啦 💕")
    with cols[1]:
        if st.button("🎊 应援", width="stretch", key=f"fx_cheer_{scope}"):
            request(st, "confetti")
    if not compact:
        with cols[2]:
            if st.button("🔥 打call", width="stretch", key=f"fx_clap_{scope}"):
                request(st, "clap")
        with cols[3]:
            if st.button("✨ 烟花", width="stretch", key=f"fx_firework_{scope}"):
                request(st, "firework")
        st.caption(f"累计应援 **{likes}** 次 · 你的每一次心动都算数")


def like_state():
    """返回当前点赞数（供界面其它地方显示）"""
    return {"likes": 0}  # 实际数量存在 st.session_state，此函数仅作接口占位
