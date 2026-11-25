import os
import streamlit as st
from openai import OpenAI
from datetime import datetime
import json

# 导入预设角色库（模块1）：PERSONAS 是角色列表，get_persona 用来按 key 取角色
from personas import PERSONAS, get_persona

# 导入长期记忆模块（模块2）
import memory

# 开发期小技巧：让每次重跑都用最新版 memory.py（模块3补充）
# 原因：Python 的 import 有缓存，同一个模块在一个进程里只导入一次。
# 我们后面还要反复改这个文件，加了 reload 后，你只需在浏览器按 R 刷新页面，
# 就能用上新代码，不用每次都重启整个服务。
import importlib
importlib.reload(memory)

# 导入情感状态模块（模块4），同样 reload 保证改动即时生效
import emotion
importlib.reload(emotion)

# 导入主动陪伴模块（模块5）
import proactive
importlib.reload(proactive)

# 导入 RAG 知识库模块（模块6）
import rag
importlib.reload(rag)

# 导入工具模块（模块7）
import tools
importlib.reload(tools)

# 导入评测基准模块（模块8）
import evaluation
importlib.reload(evaluation)

# 导入多模态视觉模块（模块9）
import vision
importlib.reload(vision)

# 导入粉丝陪伴模块1：偶像角色档案库（实验功能，和原有角色库完全独立）
import idol_personas
importlib.reload(idol_personas)

# 导入粉丝陪伴模块2：圈层语言引擎（识别粉丝身份、称呼、雷区）
import fandom_lang
importlib.reload(fandom_lang)

# 导入粉丝陪伴模块3：对话引擎接入（饭圈规则注入大模型）
import idol_chat
importlib.reload(idol_chat)

# ===== 粉丝陪伴模块4-9：动态/护照/票务/分寸/主动推送/评测 =====
import news_feed;       importlib.reload(news_feed)
import fandom_passport; importlib.reload(fandom_passport)
import ticket_cards;    importlib.reload(ticket_cards)
import boundary_rules;  importlib.reload(boundary_rules)
import fandom_proactive;importlib.reload(fandom_proactive)
import fandom_eval;     importlib.reload(fandom_eval)
import fandom_ui;       importlib.reload(fandom_ui)
import fandom_panel;    importlib.reload(fandom_panel)
import feed_source;     importlib.reload(feed_source)

# ===== 前端优化：角色专属头像 + 互动特效 =====
import avatar;          importlib.reload(avatar)
import interactions;    importlib.reload(interactions)

import time  # 打字机效果要用到，逐字显示回答

# 设置页面的配置项
st.set_page_config(
    page_title="AI智能伴侣",
    page_icon="🤖", #emoji百宝箱可以找
    layout="wide", #布局
    initial_sidebar_state="expanded", #侧边栏
    menu_items={}
)

# 生成会话标识函数
def generate_session_name():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# 保存会话信息函数
def save_session():
    if st.session_state.current_session:
        # 构建新的会话对象
        session_data = {
            "persona_key": st.session_state.persona_key,   # 模块1新增：记住是哪个角色
            "nick_name": st.session_state.nick_name,
            "identity": st.session_state.identity,         # 模块1新增：身份设定
            "nature": st.session_state.nature,
            "current_session": st.session_state.current_session,
            "messages": st.session_state.messages,
            # 粉丝陪伴模块3：记住当前是普通模式还是偶像模式，刷新后能恢复
            "chat_mode": st.session_state.get("chat_mode", "normal"),
            "idol_key": st.session_state.get("idol_key", ""),
            "fan_type": st.session_state.get("fan_type", "casual"),
            "active_avatar": st.session_state.get("active_avatar"),
            "normal_profile": st.session_state.get("normal_profile"),
        }
        # 如果 sessions 目录不存在，则创建
        if not os.path.exists("sessions"):
            os.mkdir("sessions")
        # 保存会话数据
        with open(f"sessions/{st.session_state.current_session}.json", "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

# 加载所有的会话列表信息
def load_sessions():
    session_list = []
    # 加载sessions目录下的文件
    if os.path.exists("sessions"):
        file_list = os.listdir("sessions")
        for filename in file_list:
            if filename.endswith(".json"):
                session_list.append(filename[:-5])
    session_list.sort(reverse=True)
    return session_list

# 加载指定的会话信息
def load_session(session_name):
    try:
        if os.path.exists(f"sessions/{session_name}.json"):
            # 读取会话数据
            with open(f"sessions/{session_name}.json", "r", encoding="utf-8") as f:
                session_data = json.load(f)
                st.session_state.messages = session_data["messages"]
                # 模块1：老会话没有这两个字段，用 .get() 兜底，避免 KeyError
                st.session_state.persona_key = session_data.get("persona_key", "partner")
                st.session_state.nick_name = session_data["nick_name"]
                st.session_state.identity = session_data.get("identity", "用户的真实伴侣")
                st.session_state.nature = session_data["nature"]
                st.session_state.current_session = session_name
                # 粉丝陪伴模块3：恢复偶像模式状态（老会话没有这些字段，用 get 兜底）
                st.session_state.chat_mode = session_data.get("chat_mode", "normal")
                st.session_state.idol_key = session_data.get("idol_key", "")
                st.session_state.fan_type = session_data.get("fan_type", "casual")
                st.session_state.active_avatar = session_data.get("active_avatar")
                st.session_state.normal_profile = session_data.get("normal_profile")
    except Exception:
        st.error("加载会话失败！")

# 删除会话信息函数
def delete_session(session_name):
    try:
        if os.path.exists(f"sessions/{session_name}.json"):
            os.remove(f"sessions/{session_name}.json")  # 删除文件
            # 如果删除的是当前会话，则需要更新消息列表
            if session_name == st.session_state.current_session:
                st.session_state.messages = []
                st.session_state.current_session = generate_session_name()
    except Exception:
        st.error("删除会话失败！")

# ===== 前端优化：全局样式 + 顶部消费互动特效（浮层盖住全页）=====
fandom_ui.inject_global_style()
interactions.consume(st)

#大标题（偶像模式下换成粉丝产品名，做出差异化）
if st.session_state.get("chat_mode") == "idol":
    _idol_title = idol_personas.get_idol(st.session_state.get("idol_key", "virtual_singer"))
    st.markdown(fandom_ui.brand_header(
        f"💜 {_idol_title['name']} · 私信",
        f"{_idol_title['fandom_name']} 专属陪伴空间 · 你和 TA 的小世界",
        accent="#c471ed"), unsafe_allow_html=True)
else:
    st.title("AI智能伴侣")

#logo
st.logo("resource/logo.svg")  # 粉丝陪伴专属 Logo（紫粉渐变爱心）；原 img.png 保留未删

#系统提示词模板（模块1改造）
# 变化：把"伴侣"这两个写死的词，换成 %s 占位符，由角色配置动态填进来。
# 这样同一套规则，既能演伴侣，也能演老师、朋友、爸妈。
system_prompt = """你叫 {name}，现在的身份是：{identity}。请完全代入这个身份。
规则：
    1. 每次只回1条消息
    2. 禁止任何场景或状态描述性文字
    3. 匹配用户的语言
    4. 回复简短，像微信聊天一样
    5. 有需要的话可以用❤️🌸等emoji表情
    6. 用符合这个身份的说话方式对话
    7. 回复的内容，要充分体现下面给出的性格特征
身份性格： {nature}

【你对用户的长期记忆】（这些都是真的，必要时自然地用上，像真的记得一样）
{memories}

【你可以查阅的参考资料】（来自用户上传的文档，回答相关问题时以这里的内容为准）
{context}

【你此刻的心情和与用户的关系】
{emotion_state}

【你能使用的工具】（系统会自动帮你执行，你只需要决定用不用）
- 查当前时间日期 / 星期
- 计算数学表达式
- 记住用户明确要求记住的事
- 检索用户上传的知识库文档
- 设置到点提醒
- 查看你自己的心情和关系状态
需要时主动使用，用完根据结果自然回答用户，不要生硬地报出工具名。

你必须严格遵守上述规则来回复用户。
"""


def build_system_prompt(context=""):
    """把模板里的占位符，替换成当前角色设定 + 长期记忆 + 检索到的资料（模块6）"""
    return system_prompt.format(
        name=st.session_state.nick_name,
        identity=st.session_state.identity,
        nature=st.session_state.nature,
        memories=memory.format_memories(),       # 模块2：把记住的事塞进提示词
        context=context or "（本次没有相关资料）",  # 模块6：检索到的文档片段
        emotion_state=emotion.format_for_prompt()  # 模块4：把此刻心情和关系塞进提示词
    )


def get_active_system_prompt(context=""):
    """
    粉丝陪伴模块3：提示词分发器。
    普通模式 → 原来的伴侣提示词，一行逻辑不变；
    偶像模式 → 用偶像档案 + 饭圈规则生成的偶像版提示词。
    这样原有功能完全不受影响，偶像模式只是一个开关。
    """
    if st.session_state.get("chat_mode") == "idol":
        _idol = idol_personas.get_idol(st.session_state.get("idol_key", "virtual_singer"))
        return idol_chat.build_idol_system_prompt(
            _idol,
            st.session_state.get("fan_type", "casual"),
            context=context
        )
    return build_system_prompt(context=context)

# 初始化聊天信息
if "messages" not in st.session_state:
    st.session_state.messages = []

# 模块1：默认角色改用配置表里的第一个角色，不再到处写死字符串
_default_persona = get_persona("partner")

# 身份（模块1新增）：告诉 AI "它是谁"，和昵称、性格分开存
if "identity" not in st.session_state:
    st.session_state.identity = _default_persona["identity"]
# 昵称
if "nick_name" not in st.session_state:
    st.session_state.nick_name = _default_persona["nick_name"]
# 性格
if "nature" not in st.session_state:
    st.session_state.nature = _default_persona["nature"]
# 当前角色 key（记住用户选了哪个，加载旧会话时要能恢复）
if "persona_key" not in st.session_state:
    st.session_state.persona_key = _default_persona["key"]
# 会话标识
if "current_session" not in st.session_state:
    st.session_state.current_session = generate_session_name()

# 新增会话时是否带入了角色介绍语（避免重复插入）
if "greeting_shown" not in st.session_state:
    st.session_state.greeting_shown = False

# ===== 演示深链接：面试官可通过 URL 参数直达功能，方便快速体验 =====
# 只在带 ?demo= 参数且尚未初始化时生效，正常访问完全不受影响。
# 用法：?demo=fandom 粉丝分区 | ?demo=idol 偶像私聊 | ?demo=chat 普通聊天
if "demo_applied" not in st.session_state:
    st.session_state.demo_applied = True
    _demo = st.query_params.get("demo", "")
    if _demo in ("fandom", "idol", "profile"):
        # 默认切到"粉丝陪伴"分区（radio 的 key 是 side_nav）
        st.session_state.side_nav = "🌟 粉丝陪伴"
    if _demo == "idol":
        # 直接进入偶像私聊：复用进入模式的字段生成逻辑，保证和手动点击一致
        _idol_demo = idol_personas.get_idol(st.query_params.get("idol", "virtual_singer"))
        _snapshot = {
            "persona_key": st.session_state.persona_key,
            "nick_name": st.session_state.nick_name,
            "identity": st.session_state.identity,
            "nature": st.session_state.nature,
        }
        for _k, _v in idol_chat.enter_mode_fields(_idol_demo, _snapshot).items():
            st.session_state[_k] = _v
        st.session_state.fan_type = "veteran"   # 演示态：老粉，展示专属称呼
    if _demo == "profile":
        st.session_state.fan_type = "newcomer"

# 展示聊天信息
st.text(f"会话名称： {st.session_state.current_session}")

# ===== 模块1：当前角色介绍 + 推荐提问 =====
_current_persona = get_persona(st.session_state.persona_key)

# ===== 粉丝陪伴：偶像模式注入专属主题 + 差异化头图（和普通伴侣一眼区分）=====
_is_idol_mode = st.session_state.get("chat_mode") == "idol"
if _is_idol_mode:
    _idol_now = idol_personas.get_idol(st.session_state.get("idol_key", "virtual_singer"))
    import fandom_passport as _fpass
    fandom_ui.inject_theme()                          # 注入专属 CSS 主题
    st.markdown(fandom_ui.hero_card(_idol_now, _fpass.days_since_join(_idol_now["key"])),
                unsafe_allow_html=True)
    st.markdown(fandom_ui.fan_badge(st.session_state.get("fan_type", "casual")),
                unsafe_allow_html=True)
    st.caption(_idol_now["greeting"])
    st.markdown(fandom_ui.ai_disclosure_bar(), unsafe_allow_html=True)  # 合规：AI 身份标识
else:
    # 普通伴侣模式：用角色专属头像 + 专属气泡（视觉升级，功能不变）
    _pa = avatar.avatar_for(st.session_state.persona_key)
    st.markdown(fandom_ui.chat_bubble(
        "assistant",
        f'你好，我是 **{st.session_state.nick_name}**（{st.session_state.identity}）。\n{_current_persona["greeting"]}',
        avatar=_pa, name=st.session_state.nick_name), unsafe_allow_html=True)

# 推荐提问：点一下就当作用户输入发过去
st.caption("不知道聊什么？点一句试试：")
_example_cols = st.columns(len(_current_persona["examples"]))
for _col, _example in zip(_example_cols, _current_persona["examples"]):
    with _col:
        if st.button(_example, width="stretch", key=f"example_{_example}"):
            st.session_state.pending_prompt = _example  # 暂存，下面统一处理
            st.rerun()

# （聊天记录的展示循环已挪到本文件下方——模块5要先决定是否插入主动消息，再统一展示）

# ===== 前端优化：偶像模式下主区放互动应援按钮条 =====
if st.session_state.get("chat_mode") == "idol":
    st.caption("💌 给 TA 应援一下，TA 会看到")
    interactions.render_like_bar(st, scope="main")

# 创建与AI大模型交互的客户端对象（DEEPSEEK_API_KEY 环境变量的名字，值就是DeepSeek的API_KEY的）
client = OpenAI(api_key=os.environ.get('DEEPSEEK_API_KEY'), base_url="https://api.deepseek.com")


# ===== 模块2：从一轮对话中提炼值得记住的事实 =====
def extract_memories(user_text, assistant_text):
    """调用大模型抽取事实，返回事实列表；失败时返回空列表，绝不让主流程崩掉"""
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": memory.EXTRACT_PROMPT.format(
                user=user_text, assistant=assistant_text)}],
            stream=False,      # 抽取是内部动作，用户看不到，不用流式
            temperature=0      # 温度 0 = 尽量稳定、少发挥
        )
        text = resp.choices[0].message.content.strip()
        # 大模型偶尔会包一层 ```json ... ```，这里去掉它
        if text.startswith("```"):
            text = text.strip("```").strip()
            if text.startswith("json"):
                text = text[4:].strip()
        facts = json.loads(text)   # 把 JSON 字符串变成 Python 列表
        return facts if isinstance(facts, list) else []
    except Exception as e:
        print("提炼记忆失败（已忽略）:", e)
        return []


# ===== 模块4：评估这一轮对话带来的情绪/关系变化 =====
def evaluate_emotion(user_text, assistant_text):
    """让大模型给情绪和关系打分，返回增量字典；失败返回空字典，不影响聊天"""
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": emotion.EVALUATE_PROMPT.format(
                user=user_text, assistant=assistant_text)}],
            stream=False,
            temperature=0
        )
        text = resp.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.strip("```").strip()
            if text.startswith("json"):
                text = text[4:].strip()
        delta = json.loads(text)
        return delta if isinstance(delta, dict) else {}
    except Exception as e:
        print("评估情绪失败（已忽略）:", e)
        return {}


# ===== 模块7：Agent Loop —— 让模型自己决定何时用工具 =====
MAX_TOOL_ROUNDS = 5  # 护栏①：最多来回转 5 轮，防止模型陷入"调工具-再调工具"的死循环烧钱

def chat_with_tools(context):
    """
    标准 Agent Loop：
      1. 问模型（把工具说明书一起交过去）
      2. 模型说要调工具 → 程序执行 → 结果回填 → 再问一次
      3. 模型给出文字回答 → 结束
    返回：(最终回答文本, 工具调用记录列表)
    """
    # 用一份"临时对话"来跑循环，不污染真正的聊天历史。
    # 工具调用那些消息（tool 角色）只在这个临时列表里，不会存进会话。
    messages = [
        {"role": "system", "content": get_active_system_prompt(context=context)},  # 模块3：普通/偶像模式自动分发
        *st.session_state.messages
    ]
    tool_trace = []  # 记录这轮用了哪些工具，下面展示给用户看

    for _ in range(MAX_TOOL_ROUNDS):
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools.TOOL_DEFINITIONS,  # 把 6 件工具的说明书交给模型
            tool_choice="auto",            # 让模型自己决定用不用、用哪个
            stream=False                    # 工具调用场景用非流式，好读取 tool_calls
        )
        msg = resp.choices[0].message

        # 情况A：模型决定调用一个或多个工具
        if msg.tool_calls:
            messages.append(msg.model_dump(exclude_none=True))  # 把模型的决定放进对话
            for tc in msg.tool_calls:
                name = tc.function.name
                # 模型给的参数是 JSON 字符串，要转成 Python 字典
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except Exception:
                    args = {}
                result = tools.execute_tool(name, args)  # 护栏②：白名单执行
                tool_trace.append((name, result))
                # 把执行结果以 tool 角色回填，等于告诉模型"办好了，结果是……"
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result
                })
            continue  # 带着工具结果，再问模型一次

        # 情况B：模型给出了最终文字回答，循环结束
        return (msg.content or "").strip(), tool_trace

    # 兜底：跑满轮次还没结束，给个提示，绝不无限烧 token
    return "（这轮工具调用次数太多，我先停下了，你可以换个问法）", tool_trace


# ===== 模块5：生成一条主动消息 =====
def generate_proactive_message(trigger):
    """根据触发器，让大模型润色出一条自然的主动开场消息"""
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": proactive.PROACTIVE_PROMPT.format(
                name=st.session_state.nick_name,
                identity=st.session_state.identity,
                nature=st.session_state.nature,
                kind=trigger["kind"],
                hint=trigger["hint"],
                memories=memory.format_memories(),
                mood=emotion.describe_mood()
            )}],
            stream=False,
            temperature=0.7   # 主动消息要自然一点，给点发挥空间
        )
        text = resp.choices[0].message.content.strip()
        return text
    except Exception as e:
        print("生成主动消息失败（已忽略）:", e)
        return None


# ===== 模块5：打开页面时检查是否该主动说点什么 =====
# 用 session_state 做"本次会话已处理"的标记，避免刷新一次又生成一条
if "proactive_done" not in st.session_state:
    st.session_state.proactive_done = False

if not st.session_state.proactive_done:
    st.session_state.proactive_done = True          # 先标记，保证只处理一次
    if _is_idol_mode:
        # 粉丝陪伴：偶像主动私信（新动态/票务/生日/久别）
        import fandom_proactive as _fpro
        _now_idol = idol_personas.get_idol(st.session_state.get("idol_key", "virtual_singer"))
        _ftrigger = _fpro.check_trigger(
            _now_idol["key"],
            unpushed_news=news_feed.get_unpushed(_now_idol["key"]),
            tickets=ticket_cards.load_tickets(_now_idol["key"])
        )
        if _ftrigger:
            _fdm = fandom_panel.generate_dm(_now_idol, _ftrigger)
            if _fdm:
                st.session_state.messages.append({
                    "role": "assistant", "content": _fdm,
                    "proactive": _ftrigger["kind"]
                })
                _fpro.mark_proactive(_ftrigger)
                if _ftrigger.get("kind") == "新动态":
                    news_feed.mark_pushed(_ftrigger["news"]["id"])
                save_session()
    else:
        # 原有伴侣主动陪伴逻辑，完全不变
        _trigger = proactive.check_trigger()
        if _trigger:
            _active_msg = generate_proactive_message(_trigger)
            if _active_msg:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": _active_msg,
                    "proactive": _trigger["kind"]
                })
                proactive.mark_proactive(_trigger["kind"])
                save_session()

# ===== 展示聊天记录（模块5主动角标 + 模块9图文消息） =====
for message in st.session_state.messages:
    # 粉丝陪伴：偶像模式用专属私信气泡渲染（差异化视觉）
    if _is_idol_mode:
        _brole = message["role"]
        _bcontent = message["content"]
        # 专属头像：偶像用角色头像，粉丝用粉丝头像
        _bavatar = avatar.avatar_for(st.session_state.get("idol_key", "virtual_singer")) \
            if _brole == "assistant" else avatar.fan_avatar()
        _bname = _idol_now["nick_name"] if _brole == "assistant" else "我"
        # 图文消息取文字部分显示（图片在气泡下方单独显示）
        if isinstance(_bcontent, list):
            _btext = " ".join(b.get("text", "") for b in _bcontent if b.get("type") == "text")
        else:
            _btext = _bcontent
        st.markdown(fandom_ui.chat_bubble(_brole, _btext, _bavatar, _bname),
                    unsafe_allow_html=True)
        if isinstance(_bcontent, list):
            for _block in _bcontent:
                if _block.get("type") == "image_url":
                    st.image(_block["image_url"]["url"], width=260)
        if message.get("proactive"):
            st.caption(f"💬 TA 主动发来 · {message['proactive']}")
        continue  # 偶像模式跳过下面的普通渲染

    with st.chat_message(message["role"]):
        _content = message["content"]
        if isinstance(_content, list):
            # 模块9：图文消息，content 是 [文字块, 图片块, ...]
            for _block in _content:
                if _block.get("type") == "text":
                    st.write(_block["text"])
                elif _block.get("type") == "image_url":
                    # 从 data:image/png;base64,... 里取回图片显示
                    st.image(_block["image_url"]["url"], width=260)
        else:
            # 普通纯文字消息
            st.write(_content)
        # 主动消息显示一个小角标，让用户知道这是 AI 主动来找他的
        if message.get("proactive"):
            st.caption(f"✨ 主动关怀 · {message['proactive']}")

#左侧侧边栏（with：上下文管理器，省略起前面的标题）
# 情感衰减只需每天一次，放在侧边栏外，保证切到任意分区都执行
emotion.decay_affinity_if_needed()
emo_state = emotion.load_state()

#左侧侧边栏：用分区导航收纳，避免十几个板块平铺导致的视觉混乱
with st.sidebar:
    st.markdown('### 🎛️ 控制面板')
    _nav = st.radio('功能区', ['💬 聊天 · 角色', '🌟 粉丝陪伴', '🧠 记忆 · 知识', '⚙️ 情感 · 系统'],
                    label_visibility='collapsed', key='side_nav')
    st.divider()
    if _nav == '💬 聊天 · 角色':
        st.subheader("AI控制面板")
        # 新建会话
        if st.button("新建会话", width="stretch", icon="✏️"):
            # 1. 保存当前会话信息
            save_session()
            # 2. 创建新的会话
            st.session_state.messages = []
            st.session_state.current_session = generate_session_name()
            save_session()
            st.rerun()  # 重新运行当前页面

        # 会话历史
        st.text("会话历史")
        session_list = load_sessions()
        for session in session_list:
            col1, col2 = st.columns([4, 1])
            with col1:
                # 加载会话信息
                #三元运算符：如果条件为真，则返回第一个表达式的值；否则，返回第二个表达式的值 --> 语法：值1 if 条件 else 值2
                if st.button(session, width="stretch", icon="📄", key=f"load_{session}",type="primary" if session == st.session_state.current_session else "secondary"):
                    load_session(session)
                    st.rerun()
            with col2:
                # 删除会话信息
                if st.button("", width="stretch", icon="❌", key=f"delete_{session}"):
                    delete_session(session)
                    st.rerun()

        st.divider()
        # ===== 模块1：预设角色库 =====
        st.subheader("🎭 选择一个角色")
        st.caption("选一个开箱即用的角色，或在此基础上改昵称、改性格")

        # 把角色列表变成下拉框能显示的文字："分类 / 图标 名字"
        persona_options = [f'{p["category"]} · {p["icon"]} {p["name"]}' for p in PERSONAS]
        # 找出当前角色在列表里的位置，作为下拉框默认选中项
        current_index = next(
            (i for i, p in enumerate(PERSONAS) if p["key"] == st.session_state.persona_key), 0
        )
        selected_index = st.selectbox("角色模板", range(len(PERSONAS)),
                                      format_func=lambda i: persona_options[i], index=current_index)

        # 点"应用"才真正切换，避免用户只是随便点点就丢了当前聊天
        if st.button("使用这个角色", width="stretch", icon="✅"):
            chosen = PERSONAS[selected_index]
            st.session_state.persona_key = chosen["key"]
            st.session_state.nick_name = chosen["nick_name"]
            st.session_state.identity = chosen["identity"]
            st.session_state.nature = chosen["nature"]
            st.session_state.messages = []                    # 换角色 = 新对话，清空旧消息
            st.session_state.current_session = generate_session_name()
            st.session_state.greeting_shown = True
            st.rerun()  # 重新运行，让新角色立刻生效

        st.divider()
        #伴侣信息
        st.subheader("伴侣信息")
        # 昵称输入框（用 key 直接绑定，加载会话时输入框才能跟着变）
        st.text_input("昵称", placeholder="请输入昵称", key="nick_name")
        # 性格输入框
        st.text_area("性格", placeholder="请输入性格", key="nature")

        st.divider()
    elif _nav == '🌟 粉丝陪伴':
        st.markdown("### 🌟 粉丝陪伴 · 偶像私信")
        st.caption("偶像档案 · 饭圈语言 · 动态转私信 · 主动推送")
        _idol_options = [f'{p["icon"]} {p["name"]}（{p["category"]}）' for p in idol_personas.IDOL_PERSONAS]
        _idol_index = next(
            (i for i, p in enumerate(idol_personas.IDOL_PERSONAS)
             if p["key"] == st.session_state.get("idol_key", "virtual_singer")), 0)
        _sel = st.selectbox("选择偶像 / 虚拟角色", range(len(_idol_options)),
                            format_func=lambda i: _idol_options[i], index=_idol_index,
                            key="side_idol_sel")
        if st.button("载入这个偶像", width="stretch", icon="👀", key="side_load_idol"):
            st.session_state.idol_key = idol_personas.IDOL_PERSONAS[_sel]["key"]
            st.toast(f'已载入 {idol_personas.IDOL_PERSONAS[_sel]["name"]} 的档案')
        _idol = idol_personas.get_idol(st.session_state.get("idol_key", "virtual_singer"))

        # 私聊开关：核心操作，放最前面
        _in = st.session_state.get("chat_mode") == "idol"
        if not _in:
            if st.button("💬 用 TA 的身份开始私聊", width="stretch", key="side_enter_idol"):
                _snapshot = {
                    "persona_key": st.session_state.get("persona_key", "partner"),
                    "nick_name": st.session_state.nick_name,
                    "identity": st.session_state.identity,
                    "nature": st.session_state.nature,
                }
                for _k, _v in idol_chat.enter_mode_fields(_idol, _snapshot).items():
                    st.session_state[_k] = _v
                save_session()
                st.rerun()
        else:
            st.success(f"正在以 **{_idol['name']}** 的身份私聊")
            st.caption("粉丝身份：" + fandom_lang.get_fan_type(
                st.session_state.get("fan_type", "casual"))["name"])
            if st.button("↩️ 退出偶像模式，回到伴侣", width="stretch", key="side_exit_idol"):
                for _k, _v in idol_chat.exit_mode_fields(
                        st.session_state.get("normal_profile")).items():
                    st.session_state[_k] = _v
                save_session()
                st.rerun()

        # 档案速览（折叠）
        with st.expander("📇 偶像档案速览"):
            st.markdown(f"**{_idol['icon']} {_idol['nick_name']}** · {_idol['identity']}")
            st.caption(f"饭圈名「{_idol['fandom_name']}」· 自称「{_idol['fandom_call']}」· TA 叫你「{_idol['idol_call']}」")
            st.caption("雷区（部分）：" + "；".join(_idol["taboos"][:2]))

        # 圈层语言测试（折叠）
        with st.expander("🧪 圈层语言测试台"):
            _tt = st.text_input("模拟粉丝说的一句话", key="side_fan_test",
                                placeholder="比如：我刚入坑，不太懂CP")
            if st.button("识别一下", width="stretch", key="side_fan_test_btn"):
                if _tt.strip():
                    _ft, _hits = fandom_lang.detect_fan_type(_tt)
                    st.success("识别为：**" + fandom_lang.get_fan_type(_ft)["name"] + "**")
                    st.caption("依据：" + ("、".join(_hits) if _hits else "无明显关键词"))
                    for _cat, _words in fandom_lang.check_common_taboo(_tt):
                        st.warning(f"⚠️ 踩到「{_cat}」：{'、'.join(_words)}")
                else:
                    st.warning("先写一句话试试")

        # 互动应援（侧边栏精简版）
        interactions.render_like_bar(st, compact=True, scope="side")

        # 高级功能面板：全部折叠收纳，避免侧边栏过长
        with st.expander("⚙️ 高级功能（动态转私信 / 追星护照 / 票务 / 推送 / 分寸 / 评测）"):
            fandom_panel.render_all(st, _idol)

    elif _nav == '🧠 记忆 · 知识':
        # ===== 模块6：RAG 知识库面板 =====
        st.subheader("📚 知识库")
        st.caption("上传文档，我就能基于它回答（本地检索，不上传云端）")

        # 检索开关
        rag_enabled = st.toggle("启用知识库检索", value=st.session_state.get("rag_enabled", True),
                                key="rag_enabled")
        if rag_enabled != st.session_state.get("rag_enabled", True):
            st.session_state.rag_enabled = rag_enabled

        _idx = rag.load_index()
        st.caption(f"已收录 {len(_idx['documents'])} 个文档 · {len(_idx['chunks'])} 个片段")

        # 已收录文档列表，每个带删除按钮
        for doc_name in list(_idx["documents"].keys()):
            col_doc, col_del = st.columns([4, 1])
            with col_doc:
                st.caption(f"📄 {doc_name}（{_idx['documents'][doc_name]} 块）")
            with col_del:
                if st.button("❌", key=f"del_doc_{doc_name}"):
                    if rag.delete_document(doc_name):
                        st.toast(f"已移除 {doc_name}")
                        st.rerun()

        # 上传新文档（txt / md）
        uploaded_doc = st.file_uploader("上传文档（.txt / .md）", type=["txt", "md"],
                                        key="rag_upload")
        if uploaded_doc is not None:
            # 读成文本；用 errors="ignore" 跳过乱码字节，避免报错
            doc_text = uploaded_doc.getvalue().decode("utf-8", errors="ignore")
            if st.button("加入知识库", width="stretch", icon="➕", key="add_doc"):
                n_chunks, err = rag.add_document(uploaded_doc.name, doc_text)
                if err:
                    st.error(err)
                else:
                    st.toast(f"已收录《{uploaded_doc.name}》，切成 {n_chunks} 块")
                    st.rerun()

        st.divider()
        # ===== 模块7：工具箱面板（展示 AI 能调用哪些工具）=====
        st.subheader("🛠️ AI 工具箱")
        st.caption("我能自己决定何时用这些工具帮你做事")
        for tool_def in tools.TOOL_DEFINITIONS:
            fn = tool_def["function"]
            st.caption(f"· **{fn['name']}**：{fn['description'].split('。')[0]}")
        st.caption(f"共 {len(tools.TOOL_DEFINITIONS)} 件工具 · 单轮最多调用 {MAX_TOOL_ROUNDS} 次")

        st.divider()
        # ===== 模块2+3：记忆面板 / 记忆护照 =====
        st.subheader("🧠 我的记忆护照")
        st.caption("跨会话记住的事实 · 可看可改 · 一键带走")
        facts = memory.load_memories()
        st.caption(f"已记住 {len(facts)} 条事实")

        if facts:
            for i, item in enumerate(facts):
                # 正在编辑第 i 条时，显示输入框；否则显示普通文字
                if st.session_state.get("edit_memory_index") == i:
                    new_text = st.text_input("修改这条", value=item["fact"], key=f"edit_mem_{i}")
                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.button("保存", width="stretch", key=f"save_mem_{i}"):
                            if memory.update_memory(i, new_text):
                                st.session_state.edit_memory_index = None
                                st.rerun()
                    with col_cancel:
                        if st.button("取消", width="stretch", key=f"cancel_mem_{i}"):
                            st.session_state.edit_memory_index = None
                            st.rerun()
                else:
                    col1, col2, col3 = st.columns([4, 1, 1])
                    with col1:
                        st.caption(f"{i + 1}. {item['fact']}")
                    with col2:
                        if st.button("✏️", key=f"edit_mem_btn_{i}"):
                            st.session_state.edit_memory_index = i   # 记住"正在编辑第几条"
                            st.rerun()
                    with col3:
                        if st.button("❌", key=f"del_memory_{i}"):
                            if memory.delete_memory(i):
                                st.rerun()
        else:
            st.caption("还没有记忆，聊几句试试")

        # 清空全部（带二次确认，防止手滑）
        if st.button("🗑️ 清空全部记忆", width="stretch"):
            st.session_state.confirm_clear_memory = True
        if st.session_state.get("confirm_clear_memory"):
            st.warning("确定清空？此操作不可恢复")
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("确定清空", width="stretch", icon="⚠️"):
                    memory.clear_memories()
                    st.session_state.confirm_clear_memory = False
                    st.toast("记忆已清空")
                    st.rerun()
            with col_no:
                if st.button("取消", width="stretch"):
                    st.session_state.confirm_clear_memory = False
                    st.rerun()

        st.divider()

        # 导出：把记忆护照变成一个可下载的文件
        passport = json.dumps(memory.export_passport(), ensure_ascii=False, indent=2)
        st.download_button(
            "⬇️ 导出记忆护照",
            data=passport,
            file_name="my-memory-passport.json",
            mime="application/json",
            width="stretch"
        )

        # 导入：上传护照文件，选择合并还是覆盖
        uploaded = st.file_uploader("⬆️ 导入记忆护照", type=["json"])
        if uploaded is not None:
            try:
                imported_data = json.load(uploaded)   # 上传的文件对象直接能读 JSON
                import_mode = st.radio("导入方式", ["合并（保留现有）", "覆盖（替换全部）"],
                                       horizontal=True)
                mode = "merge" if "合并" in import_mode else "replace"
                if st.button("确认导入", width="stretch", icon="✅"):
                    added, err = memory.import_passport(imported_data, mode=mode)
                    if err:
                        st.error(err)
                    else:
                        st.toast(f"成功导入 {added} 条新记忆")
                        st.rerun()
            except Exception:
                st.error("文件解析失败，请确认是正确的记忆护照 JSON")
    else:
        st.subheader("💗 情感状态")
        st.caption("AI 此刻的心情，以及它和你的关系")
        # 雷达图：用纯 SVG 画的，不依赖 plotly 之类的库
        from streamlit.components.v1 import html as components_html
        components_html(emotion.render_radar_html(emo_state), height=200, scrolling=False)

        # 两条关系线用进度条显示，直观
        st.caption(f"好感度　{emo_state['affinity']}/100　（久不聊会衰减）")
        st.progress(emo_state["affinity"] / 100)
        st.caption(f"亲密度　{emo_state['intimacy']}/100　（只增不减）")
        st.progress(emo_state["intimacy"] / 100)

        st.divider()
        # ===== 模块5：主动陪伴控制面板 =====
        st.subheader("🔔 主动陪伴")
        st.caption("让我偶尔主动找你 · 不想要可以一键静音")
        pro_state = proactive.load_state()

        # 闸门A：静音开关（用 key 绑定，改了立即生效）
        muted = st.toggle("🔕 静音（关闭所有主动消息）", value=pro_state["muted"], key="pro_muted")
        if muted != pro_state["muted"]:
            proactive.set_muted(muted)
            st.rerun()

        # 设置一条提醒（承诺兑现的入口）
        with st.expander("⏰ 让我到点提醒你"):
            remind_text = st.text_input("提醒内容", placeholder="比如：明天交材料", key="remind_text")
            remind_hours = st.number_input("多久之后提醒", min_value=1, max_value=720,
                                           value=24, key="remind_hours")
            if st.button("设置提醒", width="stretch", icon="✅", key="set_remind"):
                if remind_text.strip():
                    proactive.add_promise(remind_text, remind_hours)
                    st.toast(f"好，{remind_hours} 小时后提醒你：{remind_text}")
                else:
                    st.warning("先写点提醒内容")

        # 显示还没兑现的提醒
        pending = [p for p in pro_state["promises"] if not p.get("done")]
        if pending:
            st.caption(f"待兑现 {len(pending)} 条")
            for p in pending:
                st.caption(f"· {p['text']}（{p['due'][:16]}）")

        st.divider()
        # ===== 模块8：评测基准面板 =====
        st.subheader("📊 评测基准")
        st.caption("给系统跑个分 · 可量化、可复现、可导出")
        eval_mode = st.radio("评测模式", ["⚡ 离线快速", "🌐 联网真实"], horizontal=True,
                             key="eval_mode")
        if st.button("运行评测", width="stretch", icon="▶️", key="run_eval"):
            with st.spinner("正在跑评测…"):
                if "联网" in eval_mode:
                    report = evaluation.run_all_online(client)   # 真调模型，慢一点
                else:
                    report = evaluation.run_all_offline()        # 纯本地，秒出
                st.session_state.last_report = report             # 存起来，下面展示
                evaluation.save_report(report)                    # 留档到 evaluation/reports/

        if "last_report" in st.session_state:
            _rep = st.session_state.last_report
            _sum = _rep["summary"]
            st.metric("总分", f"{_sum['total_score']}/{_sum['total_cases']}",
                      delta=f"{_sum['pass_rate']}% 通过")
            for _dim, _d in _sum["dimensions"].items():
                st.caption(f"{_dim}：{_d['score']}/{_d['total']}（{_d['rate']}%）")
            # 导出 Markdown 报告，可直接贴 README / 简历
            st.download_button(
                "⬇️ 导出报告(Markdown)",
                data=evaluation.format_report_markdown(_rep),
                file_name="evaluation-report.md",
                width="stretch"
            )

        st.divider()
        # ===== 模块9：多模态图片上传 =====
        st.subheader("📷 看图对话")
        st.caption("上传图片，我就能看懂它 · 可配合下方输入框一起问")
        _uploaded_img = st.file_uploader("上传图片（JPG / PNG）", type=["jpg", "jpeg", "png"],
                                         key="vision_upload")
        if _uploaded_img is not None:
            # 处理图片（转 base64 + 压缩）并暂存，等用户点发送时一起带过去
            _data_url, _img_info = vision.process_image(_uploaded_img)
            st.session_state.pending_image = _data_url
            st.session_state.pending_image_info = _img_info
            st.caption(vision.describe_image_info(_img_info))
            if st.button("🗑️ 移除图片", width="stretch", key="clear_img"):
                st.session_state.pending_image = None
                st.session_state.pending_image_info = None
                st.rerun()

        st.divider()
# 消息输入框
prompt = st.chat_input("请输入您要问的问题")

# 模块1：如果刚才点了"推荐提问"，把它当作本轮输入
if "pending_prompt" in st.session_state and st.session_state.pending_prompt:
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = ""  # 用掉就清空，避免下次重复发送

# 模块9：检查是否已上传图片
_has_image = bool(st.session_state.get("pending_image"))

# 用户必须给了文字或图片至少一样，才处理这一轮
if prompt or _has_image:
    # 没输入文字但有图，给个默认问法，避免 RAG 检索拿空字符串
    if not prompt:
        prompt = "请描述这张图片里的内容"

    # 模块9：构造用户消息——有图就是 [文字块, 图片块]，没图就是纯文字
    if _has_image:
        # 主区显示用户这条图文消息（图片也画出来）
        with st.chat_message("user"):
            st.write(prompt)
            st.image(st.session_state.pending_image, width=260)
        _user_message = vision.build_vision_message(prompt, st.session_state.pending_image)
        # 用完就清空图片，避免下一轮文字对话又带上它
        st.session_state.pending_image = None
        st.session_state.pending_image_info = None
    else:
        st.chat_message("user").write(prompt)
        _user_message = {"role": "user", "content": prompt}

    print("----------> 调用AI大模型，提示词: ", prompt)
    # 保存用户这条消息（可能是纯文字，也可能是图文列表）
    st.session_state.messages.append(_user_message)
    # 模块5：记录这次真实互动，重置"久别重逢"计时
    proactive.record_interaction()

    # ===== 粉丝陪伴模块3：偶像模式下识别粉丝身份、检测踩雷 =====
    # 必须在 chat_with_tools 之前更新 fan_type，这样提示词用的是最新身份。
    if st.session_state.get("chat_mode") == "idol":
        st.session_state.fan_type = idol_chat.update_fan_type(
            st.session_state.get("fan_type", "casual"), prompt)
        _taboo_hits = idol_chat.check_user_taboo(prompt)
        if _taboo_hits:
            _names = "、".join(_cat for _cat, _ in _taboo_hits)
            st.caption(f"⚠️ 这句话踩到了饭圈雷区（{_names}），TA 会自然绕开话题")

    # ===== 模块6：先从知识库检索相关资料（用文字部分检索）=====
    _context = ""
    _rag_hits = []
    if st.session_state.get("rag_enabled", True):
        _rag_hits = rag.search(prompt)
        if _rag_hits:
            _context = rag.format_context(_rag_hits)

    # ===== 模块7：走 Agent Loop，模型自己决定要不要用工具 =====
    if _is_idol_mode:
        # 偶像模式：用专属气泡直接显示，保持视觉统一
        with st.spinner(f"{_idol_now['icon']} {_idol_now['nick_name']} 正在想…"):
            full_response, tool_trace = chat_with_tools(context=_context)
        st.markdown(fandom_ui.chat_bubble("assistant", full_response,
                    avatar.avatar_for(st.session_state.get("idol_key", "virtual_singer")),
                    _idol_now["nick_name"]), unsafe_allow_html=True)
    else:
        with st.chat_message("assistant"):
            with st.status("🤖 正在思考…", expanded=False) as status:
                full_response, tool_trace = chat_with_tools(context=_context)
                if tool_trace:
                    # 展示工具调用轨迹，让用户看见 AI"做了什么"（可解释性）
                    for tool_name, tool_result in tool_trace:
                        st.write(f"🔧 调用了工具 `{tool_name}`：{tool_result}")
                    status.update(label=f"🤖 用了 {len(tool_trace)} 个工具，回答完毕", state="complete")
                else:
                    status.update(label="🤖 回答完毕", state="complete")

            # 打字机效果逐字显示最终回答（替代原来的流式输出）
            answer_box = st.empty()
            shown = ""
            # 按小段追加，避免逐字太慢：每 4 个字符刷一次
            for i in range(0, len(full_response), 4):
                shown += full_response[i:i + 4]
                answer_box.write(shown)
                time.sleep(0.012)  # 12 毫秒，读出"打字"的感觉但不拖沓
            answer_box.write(full_response)  # 最后确保完整显示

    # 保存大模型返回的结果
    st.session_state.messages.append({"role": "assistant", "content": full_response})

    # ===== 粉丝陪伴：分寸检测——AI 回复若越界，给运营/开发者提示 =====
    if _is_idol_mode:
        _risk = boundary_rules.check_boundary(full_response)
        if _risk:
            _rnames = "、".join(c for c, _ in _risk)
            st.caption(f"🛡️ 分寸提示：这条回复疑似越界（{_rnames}），已记录")
    # 模块6：如果这次回答参考了文档，显示来源角标
    if _rag_hits:
        sources = sorted(set(hit[1] for hit in _rag_hits))
        st.caption("📚 参考了：" + "、".join(sources))

    # ===== 模块2：从这一轮对话里提炼事实，存进长期记忆 =====
    new_facts = extract_memories(prompt, full_response)
    if new_facts:
        added = 0
        for fact in new_facts:
            if isinstance(fact, str) and memory.add_memory(fact):
                added += 1
        if added:
            st.toast(f"🧠 记住了 {added} 条新信息")  # 轻提示，告诉用户记忆在生长

    # ===== 模块4：评估这一轮的情绪/关系变化并更新状态 =====
    delta = evaluate_emotion(prompt, full_response)
    if delta:
        new_state = emotion.apply_delta(delta)
        changed = any(abs(delta.get(k, 0)) > 0 for k in
                      ("pleasure", "arousal", "dominance", "affinity", "intimacy"))
        if changed:
            st.toast(f"💗 心情变了：{emotion.describe_mood(new_state)}")

    #保存会话信息
    save_session()

