# -*- coding: utf-8 -*-
"""
角色专属头像系统
================

给每个角色（伴侣库 8 个 + 偶像库 3 个）配一张"一眼能分清"的头像。

为什么不用真实图片：
  · 项目要开源、非商用，放真人照片有肖像权风险
  · 用 SVG 画头像 = 零外部文件、零版权风险、clone 下来就能跑
  · 每个头像由"配色 + 图形 + 光环"三部分随机组合，辨识度高

技术方案：
  · 纯 SVG 字符串 → base64 → data URI
  · Streamlit 的 avatar 参数和 HTML <img> 都能直接用 data URI
  · 不依赖任何第三方库

对外接口：
  avatar_for(key)         按角色 key 拿 data URI（主程序 st.chat_message avatar 用）
  avatar_img(key, size)   拿一个 <img> HTML 标签（自定义气泡里用）
  role_avatar(role, ...)  根据消息 role 智能取头像（assistant→当前角色，user→粉丝）
"""

import base64

# ===== 头像设计表：每个角色 = 主色 + 辅色 + 中心图形 + 光环符号 =====
# 图形用 emoji，光环是一圈小装饰；配色走"冷暖 + 明暗"错开，保证一眼能区分
AVATAR_STYLES = {
    # ---- 原有伴侣库 8 个角色 ----
    "partner":       {"c1": "#ff9a9e", "c2": "#fecfef", "glyph": "💕", "halo": "#ff6b81", "shape": "circle"},
    "parents_away":  {"c1": "#f6d365", "c2": "#fda085", "glyph": "🏠", "halo": "#f59e0b", "shape": "circle"},
    "caring_child":  {"c1": "#a18cd1", "c2": "#fbc2eb", "glyph": "📞", "halo": "#8b5cf6", "shape": "circle"},
    "close_friend":  {"c1": "#43e97b", "c2": "#38f9d7", "glyph": "🍻", "halo": "#10b981", "shape": "circle"},
    "k12_teacher":   {"c1": "#4facfe", "c2": "#00f2fe", "glyph": "📚", "halo": "#0ea5e9", "shape": "circle"},
    "kaoyan_mentor": {"c1": "#667eea", "c2": "#764ba2", "glyph": "🎓", "halo": "#6366f1", "shape": "circle"},
    "gongkao_mentor":{"c1": "#a1c4fd", "c2": "#c2e9fb", "glyph": "🏛️", "halo": "#3b82f6", "shape": "circle"},
    "career_mentor": {"c1": "#f093fb", "c2": "#f5576c", "glyph": "💼", "halo": "#ec4899", "shape": "circle"},
    # ---- 粉丝陪伴 3 个偶像 ----
    "virtual_singer":{"c1": "#c471ed", "c2": "#f64f59", "glyph": "🎤", "halo": "#e879f9", "shape": "star", "ring": "#f0abfc"},
    "novel_hero":    {"c1": "#30cfd0", "c2": "#330867", "glyph": "📖", "halo": "#22d3ee", "shape": "diamond", "ring": "#67e8f9"},
    "vtuber":        {"c1": "#f7971e", "c2": "#ffd200", "glyph": "🎮", "halo": "#fbbf24", "shape": "hex", "ring": "#fde68a"},
}

# 兜底头像：找不到 key 时用（绝不让界面因为缺头像而崩）
FALLBACK = {"c1": "#a855f7", "c2": "#ec4899", "glyph": "🌟", "halo": "#c084fc", "shape": "circle"}

# 粉丝（用户自己）的头像
FAN_STYLE = {"c1": "#22d3ee", "c2": "#6366f1", "glyph": "🙋", "halo": "#38bdf8", "shape": "circle"}


def _shape_path(shape):
    """根据形状返回 SVG 里画头像底板的元素"""
    if shape == "circle":
        return '<circle cx="50" cy="50" r="46" fill="url(#g)" stroke="{halo}" stroke-width="3"/>'
    if shape == "diamond":
        return '<rect x="12" y="12" width="76" height="76" rx="14" transform="rotate(45 50 50)" fill="url(#g)" stroke="{halo}" stroke-width="3"/>'
    if shape == "hex":
        return '<polygon points="50,4 90,27 90,73 50,96 10,73 10,27" fill="url(#g)" stroke="{halo}" stroke-width="3"/>'
    if shape == "star":
        return ('<polygon points="50,3 61,35 95,35 67,55 78,88 50,68 22,88 33,55 5,35 39,35" '
                'fill="url(#g)" stroke="{halo}" stroke-width="2"/>')
    return '<circle cx="50" cy="50" r="46" fill="url(#g)" stroke="{halo}" stroke-width="3"/>'


def _build_svg(style):
    """把一个样式字典变成 SVG 字符串"""
    shape = _shape_path(style.get("shape", "circle")).format(halo=style["halo"])
    # 偶像专属：外圈再加一层柔光环，更像"应援色"
    ring = ""
    if style.get("ring"):
        ring = f'<circle cx="50" cy="50" r="48" fill="none" stroke="{style["ring"]}" stroke-width="1.5" opacity="0.7"/>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="{style['c1']}"/><stop offset="100%" stop-color="{style['c2']}"/>
</linearGradient></defs>
{ring}
{shape}
<text x="50" y="50" font-size="42" text-anchor="middle" dominant-baseline="central">{style['glyph']}</text>
</svg>'''


def _to_data_uri(svg):
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def avatar_for(key):
    """按角色 key 返回头像 data URI。找不到就退回兜底头像。"""
    style = AVATAR_STYLES.get(key, FALLBACK)
    return _to_data_uri(_build_svg(style))


def fan_avatar():
    """粉丝（用户）自己的头像"""
    return _to_data_uri(_build_svg(FAN_STYLE))


def avatar_img(key, size=40, extra_class=""):
    """返回可直接塞进 st.markdown 的 <img> 标签"""
    return f'<img class="fm-avatar-img {extra_class}" src="{avatar_for(key)}" width="{size}" height="{size}" alt="头像"/>'


def role_avatar(role, persona_key, idol_key="", is_idol_mode=False):
    """
    根据消息角色智能取头像：
      assistant → 当前对话角色（偶像模式用偶像头像，普通模式用伴侣头像）
      user      → 粉丝头像
    """
    if role == "user":
        return fan_avatar()
    return avatar_for(idol_key) if is_idol_mode else avatar_for(persona_key)


def debug_all_avatars():
    """开发用：打印所有头像的 key 和 data URI 长度，确认都能生成"""
    for key in AVATAR_STYLES:
        uri = avatar_for(key)
        assert uri.startswith("data:image/svg+xml;base64,"), key
    return len(AVATAR_STYLES)
