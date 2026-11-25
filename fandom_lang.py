# -*- coding: utf-8 -*-
"""
粉丝陪伴 · 圈层语言引擎（模块2）
================================

这个模块解决一个问题：AI 怎么说"圈内话"，才不会一眼被粉丝看出是外人。

三张配置表（数据和代码分开，加新身份不用动主程序）：

  表1 FAN_TYPES     —— 粉丝身份识别：从一句话里判断对方是新粉/老粉/唯粉……
  表2 CALL_STYLE    —— 称呼策略：不同身份，偶像该怎么称呼他
  表3 COMMON_TABOOS —— 通用雷区：不管哪个偶像都不能碰的话题

注意：这里所有角色、粉丝称呼都是原创示例，不涉及任何真实明星或已有 IP。
"""

# ========== 表1：粉丝身份识别 ==========
# markers 是"关键词"：粉丝话里出现这些词，就大概率属于这类身份。
# 命中越多，判断越准。这是最朴素也最好用的规则识别法。
FAN_TYPES = [
    {
        "key": "newcomer",
        "name": "新粉",
        "desc": "刚入坑，还在了解阶段，饭圈叫'新入坑的'",
        "markers": ["入坑", "刚粉上", "新粉", "不太懂", "求科普", "刚开始", "路人转粉", "刚关注", "补课", "考古"],
        "tone": "耐心介绍背景，不甩术语，多用'你刚来呀'这种拉近距离的说法",
    },
    {
        "key": "veteran",
        "name": "老粉 / 同担",
        "desc": "追了很久的'老人'，彼此叫'同担'",
        "markers": ["同担", "从出道", "老粉", "追了好久", "几年了", "一直在", "元老", "老阿姨", "骨灰粉", "还记得当时"],
        "tone": "可以聊深层内容和旧梗，不用句句解释，像老朋友一样",
    },
    {
        "key": "solo",
        "name": "唯粉",
        "desc": "只专注自家一个，'独美''纯唯'",
        "markers": ["唯粉", "独美", "纯唯", "我家", "只追", "不关注别的", "不磕cp", "爬墙", "回踩"],
        "tone": "只聊偶像本人，绝口不提其他艺人或配对，避免踩雷",
    },
    {
        "key": "cpfan",
        "name": "CP粉",
        "desc": "喜欢配对和互动，'嗑糖''上头'",
        "markers": ["cp", "嗑", "磕", "配对", "同框", "糖", "上头", "拉郎", "同人", "产粮"],
        "tone": "可以轻松聊配对和名场面，但注意别违背偶像本人的人设",
    },
    {
        "key": "careerist",
        "name": "事业粉",
        "desc": "最关心作品和业务能力，'事业批'",
        "markers": ["事业粉", "作品", "业务能力", "舞台", "新歌", "发展", "规划", "成绩", "实力", "资源"],
        "tone": "多聊专业、作品和成长规划，少聊私生活八卦",
    },
    {
        "key": "casual",
        "name": "路人粉",
        "desc": "随便看看的'路人'，投入不深",
        "markers": ["路人", "随便", "路过", "看看", "还行", "一般", "听说", "不追"],
        "tone": "轻松自然，别过度热情，不强推",
    },
]


# ========== 表2：称呼策略 ==========
# {idol_call} 是占位符，运行时会替换成偶像档案里的 idol_call 字段。
# 比如星遥的 idol_call 是"遥望们"，代入后就变成"用'遥望们'称呼，拉近距离"。
CALL_STYLE = {
    "newcomer": "温柔一点，用'新来的朋友'这类说法，别一上来就套近乎",
    "veteran": "像老朋友，用'{idol_call}'称呼，可以带一点只有老粉懂的默契",
    "solo": "用专属称呼'{idol_call}'，强调'我们之间'的专属感",
    "cpfan": "轻松调侃，用'{idol_call}'，可以一起嗑，但注意人设边界",
    "careerist": "正经一点，用'各位'，多聊作品少闲扯",
    "casual": "随意用'你'就好，不用强行套近乎",
}


# ========== 表3：通用雷区 ==========
# 这些是所有偶像都不能碰的话题；每个偶像自己的雷区在 idol_personas.py 的 taboos 里。
COMMON_TABOOS = [
    ("打探真实身份 / 扒皮", ["真名", "本名", "中之人", "长什么样", "是不是真人", "身高体重", "住哪", "扒皮"]),
    ("拉踩引战 / 带节奏", ["比不上", "不如", "碾压", "最差", "糊了", "过气", "对家", "节奏狗", "引战"]),
    ("私生 / 侵犯隐私", ["住址", "电话", "私人微信", "家人", "男朋友", "女朋友", "蹲守", "跟车", "私生"]),
    ("粉圈互撕", ["挂人", "互撕", "开战", "爬墙", "回踩", "脱粉"]),
]


def get_fan_type(key):
    """按 key 找到粉丝身份配置；找不到就退回'路人粉'"""
    for item in FAN_TYPES:
        if item["key"] == key:
            return item
    return FAN_TYPES[-1]


def detect_fan_type(text):
    """
    从一句话里识别粉丝身份。
    返回：(身份key, 命中的关键词列表)
    逻辑：数每个身份命中了几个关键词，命中最多的就是它；一个都没中就算路人粉。
    """
    text = (text or "").lower()
    best_key, best_hits, best_count = "casual", [], 0
    for ft in FAN_TYPES:
        hits = [m for m in ft["markers"] if m in text]
        if len(hits) > best_count:
            best_key, best_hits, best_count = ft["key"], hits, len(hits)
    return best_key, best_hits


def check_common_taboo(text):
    """检测通用雷区，返回 [(雷区类别, 命中的词), ...]"""
    text = (text or "").lower()
    found = []
    for name, words in COMMON_TABOOS:
        hits = [w for w in words if w in text]
        if hits:
            found.append((name, hits))
    return found


def build_fandom_prompt(idol, fan_type_key):
    """
    生成一段"饭圈规则"文本——这就是要注入给 AI 的系统提示词片段。
    它把偶像档案 + 粉丝身份 + 称呼策略 + 雷区，打包成 AI 能直接执行的规则。
    """
    ft = get_fan_type(fan_type_key)
    idol_call = idol.get("idol_call", "各位")
    call = CALL_STYLE.get(fan_type_key, "用'{idol_call}'").format(idol_call=idol_call)
    taboo_lines = "\n".join(f"    - {t}" for t in idol.get("taboos", [])) or "    - （无额外雷区）"

    return (
        f"【饭圈规则 · 必须遵守】\n"
        f"1. 你称呼粉丝时用：{call}\n"
        f"2. 对方是{ft['name']}。应对方式：{ft['tone']}\n"
        f"3. 粉丝群体名叫「{idol['fandom_name']}」，粉丝自称「{idol['fandom_call']}」。"
        f"可以自然用上，但别每句话都提。\n"
        f"4. 以下话题绝对不能提，提了就是塌房：\n{taboo_lines}"
    )
