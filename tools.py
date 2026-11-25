"""
工具模块（模块7）：让 AI 从"只会聊天"变成"能做事"。

设计要点：
1. TOOL_DEFINITIONS 是"工具说明书"，按 OpenAI Function Calling 格式写，
   会在调用大模型时通过 tools 参数传过去，模型看了就知道有哪些工具能用。
2. execute_tool 是"工具执行器"，白名单分发：模型说要调哪个工具，
   程序只在这个清单里找，找不到就拒绝——不让模型随便执行任意代码。
3. 每个工具函数都复用前面模块的能力（memory / rag / proactive / emotion），
   把"会记、会查、会提醒、有心情"这些能力暴露给 AI 自己决定何时使用。
"""

import ast
import operator
from datetime import datetime

import memory
import rag
import proactive
import emotion


# ===== 工具说明书（OpenAI Function Calling 标准格式）=====
# 每个工具要写清楚：name（名字）、description（干什么、什么时候用）、
# parameters（参数长什么样，JSON Schema 格式）。
# description 写得越清楚，模型越能判断"这句话该不该调这个工具"。
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前的日期、星期和时间。当用户问'今天几号''现在几点''今天是星期几'等问题时使用。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "计算一个数学表达式并返回结果。当用户要算数时使用，比如'123乘以456等于多少''帮我算(35+47)*2'。只支持加减乘除、括号和小数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "要计算的数学表达式，如 '(35+47)*2'"}
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember_fact",
            "description": "把一条关于用户的信息记入长期记忆，这样以后跨会话也能记得。当用户明确说'记住...''请记住我...'时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "fact": {"type": "string", "description": "要记住的事实，如'用户养了一只叫橘子的猫'"}
                },
                "required": ["fact"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "在用户上传的知识库文档中检索相关内容。当用户问的问题可能需要查资料、文档、笔记时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "要检索的关键词或问题"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "设置一个到点提醒。当用户说'提醒我...''N小时后提醒我...'时使用。设置后到时间打开页面，AI 会主动提起这件事。",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "提醒的内容，如'交材料'"},
                    "hours_later": {"type": "number", "description": "多少小时后提醒，如 24 表示一天后"}
                },
                "required": ["text", "hours_later"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_mood",
            "description": "查看 AI 当前的心情和与用户的关系状态。当用户问'你心情怎么样''我们关系好吗'时使用。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


# ===== 6 个工具的具体实现 =====

def tool_get_current_time(**kwargs):
    now = datetime.now()
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    return f"现在是 {now.strftime('%Y年%m月%d日 %H:%M:%S')}，星期{weekdays[now.weekday()]}"


def tool_calculate(expression, **kwargs):
    """
    安全计算：用 ast 解析表达式，只放行数字和四则运算，绝不执行任意代码。

    为什么不用 eval("...")：eval 会执行任何 Python 代码，
    如果模型（或被诱导）传入 __import__('os').system('...') 就危险了。
    这里用 ast 把表达式拆成语法树，逐个节点检查，只允许安全节点。
    """
    # 允许的操作符：加减乘除、正负号
    allowed_ops = {
        ast.Add: operator.add, ast.Sub: operator.sub,
        ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.USub: operator.neg, ast.UAdd: operator.pos,
    }

    def evaluate(node):
        # 数字常量
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        # 二元运算，如 35 + 47
        if isinstance(node, ast.BinOp) and type(node.op) in allowed_ops:
            left = evaluate(node.left)
            right = evaluate(node.right)
            if type(node.op) is ast.Div and right == 0:
                raise ValueError("除数不能为 0")
            return allowed_ops[type(node.op)](left, right)
        # 一元运算，如 -5 或 +5
        if isinstance(node, ast.UnaryOp) and type(node.op) in allowed_ops:
            return allowed_ops[type(node.op)](evaluate(node.operand))
        # 其他一律拒绝（函数调用、变量、属性访问等都不允许）
        raise ValueError("只支持数字和加减乘除运算")

    try:
        tree = ast.parse(str(expression).strip(), mode="eval")
        result = evaluate(tree.body)
        return f"计算结果：{result}"
    except Exception as e:
        return f"计算失败：{e}。请检查表达式是否为纯数字四则运算。"


def tool_remember_fact(fact, **kwargs):
    fact = str(fact).strip()
    if not fact:
        return "没有可记住的内容"
    added = memory.add_memory(fact)
    return f"已记住：{fact}" if added else f"这条已经记过了：{fact}"


def tool_search_knowledge(query, **kwargs):
    hits = rag.search(str(query))
    if not hits:
        return "知识库里没有找到相关内容"
    return rag.format_context(hits)


def tool_set_reminder(text, hours_later=1, **kwargs):
    text = str(text).strip()
    if not text:
        return "提醒内容不能为空"
    ok = proactive.add_promise(text, hours_later)
    return f"已设置提醒：{hours_later} 小时后提醒你「{text}」" if ok else "设置提醒失败"


def tool_get_mood(**kwargs):
    return f"当前心情：{emotion.describe_mood()}"


# ===== 白名单分发表：工具名 → 执行函数 =====
# 模型只能调用这里登记过的工具，其他名字一律拒绝。
TOOL_HANDLERS = {
    "get_current_time": tool_get_current_time,
    "calculate": tool_calculate,
    "remember_fact": tool_remember_fact,
    "search_knowledge": tool_search_knowledge,
    "set_reminder": tool_set_reminder,
    "get_mood": tool_get_mood,
}


def execute_tool(name, arguments):
    """
    执行一个工具。arguments 是模型给出的参数字典。
    返回工具执行结果字符串；任何异常都被兜住，不让主流程崩掉。
    """
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return f"未知工具：{name}（不在可用工具清单里）"
    try:
        return handler(**(arguments or {}))
    except Exception as e:
        return f"工具执行失败：{e}"
