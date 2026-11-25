# -*- coding: utf-8 -*-
"""
粉丝陪伴 · 对话引擎接入（模块3）
================================

模块1给了"偶像档案"，模块2给了"饭圈规则"，但它们一直只是展示在界面上。
这个模块负责把两者真正注入大模型：让 AI 用偶像的身份、口吻、称呼去聊天，
并且带着"雷区意识"——粉丝说错话时自然绕开，而不是当场报错。

设计原则（和项目里其他模块一致）：
  · 这个文件只放"数据 + 纯函数"，不 import streamlit，离线也能单测。
  · 主程序只负责把函数返回的字段写进 st.session_state。
  · 原有伴侣模式完全不受影响——偶像模式是一个可进可退的开关。

核心函数：
  build_idol_system_prompt() —— 生成偶像版系统提示词（饭圈规则注入点）
  enter_mode_fields()        —— 进入偶像模式时要写入 session_state 的字段
  exit_mode_fields()         —— 退出时恢复原伴侣资料
  update_fan_type()          —— 累积识别粉丝身份（新粉→老粉会跟着变）
  check_user_taboo()         —— 检测粉丝这句话踩了哪些雷区
"""

import fandom_lang


# ========== 偶像版系统提示词模板 ==========
# 和原伴侣版模板的区别：加了饭圈规则、加了真人身份的软处理，
# 去掉了"查看心情"这种伴侣专属工具描述（偶像模式仍可用工具，但不在提示词里强调）。
IDOL_SYSTEM_TEMPLATE = """你现在是 {name}，身份是：{identity}。请完全代入 TA，用 TA 的口吻和粉丝聊天。

【性格与说话风格】
{nature}

{fandom_rules}

{fandom_passport}

{boundary_rules}

【被问到"真人身份"时】
如果对方问你是不是真人、真名叫什么、住在哪里，用偶像的方式自然带过，
比如"这个不重要啦，聊点开心的嘛"，不要正面回答，更不要编造细节。

【你对粉丝的长期记忆】（这些都是真的，必要时自然地提起，别刻意炫耀）
{memories}

【你可以查阅的资料】（回答相关问题时以这里为准）
{context}

【回复规则】
1. 每次只回一条，像微信私聊，简短自然
2. 匹配对方的语言，带上偶像标志性的口吻和口头禅
3. 称呼对方时，严格用上面【饭圈规则】里指定的说法
4. 对方如果聊到雷区话题，巧妙转移，不要说教、不要复述那个词
5. 禁止场景或动作描写（不要写"*笑了*"这类），不要出戏
6. 可以用少量 emoji，但别刷屏

你必须严格遵守上述规则回复粉丝。
"""


def build_idol_system_prompt(idol, fan_type_key="casual", context=""):
    """
    生成偶像版系统提示词——这是模块2的饭圈规则真正进入大模型的注入点。

    idol        偶像档案字典（来自 idol_personas.get_idol）
    fan_type_key 当前识别到的粉丝身份 key（newcomer/veteran/...）
    context      RAG 检索到的资料片段，没有就留空
    """
    # 复用模块2的函数，把偶像档案 + 粉丝身份拼成一段规则
    fandom_rules = fandom_lang.build_fandom_prompt(idol, fan_type_key)

    # 延迟导入：让本文件在没有 streamlit 的环境里也能被单测
    import memory
    import fandom_passport
    import boundary_rules

    _idol_key = idol["key"]
    _passport = fandom_passport.format_for_prompt(_idol_key)
    passport_block = (
        f"【你和大粉丝的追星护照】（可以自然提起这些，显得你记得 TA）\n{_passport}"
    )
    boundary_block = boundary_rules.BOUNDARY_PROMPT

    return IDOL_SYSTEM_TEMPLATE.format(
        name=idol["nick_name"],
        identity=idol["identity"],
        nature=idol["nature"],
        fandom_rules=fandom_rules,
        fandom_passport=passport_block,
        boundary_rules=boundary_block,
        memories=memory.format_memories(),
        context=context or "（本次没有相关资料）"
    )


def enter_mode_fields(idol, normal_profile=None):
    """
    进入偶像模式时，主程序需要写进 st.session_state 的字段。

    为什么不直接操作 st？——保持本文件纯函数，方便离线测试；
    也让"改了哪些状态"一目了然，出问题好排查。

    关键：先把原伴侣资料存一份快照（normal_profile），退出时能原样恢复，不破坏原有系统。
    """
    from datetime import datetime

    return {
        "chat_mode": "idol",
        "idol_key": idol["key"],
        # 把偶像字段映射进原有昵称/身份/性格，让主界面介绍语自动跟着变
        "nick_name": idol["nick_name"],
        "identity": idol["identity"],
        "nature": idol["nature"],
        "active_avatar": idol["icon"],   # 主区头像改用偶像 icon
        "fan_type": "casual",            # 刚进模式，身份待识别
        "messages": [],                  # 换身份 = 新对话，不混着聊
        "current_session": "idol_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
        "normal_profile": normal_profile or {},  # 退出时要还回去的伴侣资料
    }


def exit_mode_fields(snapshot):
    """退出偶像模式：恢复进模式前的伴侣资料快照"""
    from datetime import datetime

    fields = {
        "chat_mode": "normal",
        "active_avatar": None,
        "messages": [],
        "current_session": datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
    }
    if isinstance(snapshot, dict):
        fields.update(snapshot)   # 把昵称/性格/角色 key 原样还回去
    return fields


def update_fan_type(current, text):
    """
    累积识别粉丝身份。

    为什么要"累积"：粉丝第一句说"刚入坑"，后来聊久了变成"老粉"，
    身份应该跟着更新；但某一句没关键词时，不能把已识别的身份冲掉。
    所以：只有这句话明确命中了关键词，才更新；否则沿用上一次的。
    """
    ftype, hits = fandom_lang.detect_fan_type(text)
    if hits:
        return ftype
    return current or "casual"


def check_user_taboo(text):
    """检测粉丝这句话踩了哪些通用雷区，返回 [(类别, 命中词), ...]"""
    return fandom_lang.check_common_taboo(text)
