# -*- coding: utf-8 -*-
"""
模块2：分层记忆 —— 长期语义记忆
==================================
它负责把对话里"值得记住的事"提炼出来，存成一个事实清单，
下次聊天时再把这些事实注入提示词，让 AI 跨会话也认得你。

对应路线图里的：语义记忆（本次做）
"""

import os
import json

MEMORY_FILE = "memory/memories.json"


def _ensure_file():
    """确保 memory 文件夹和 json 文件都存在，不存在就创建"""
    if not os.path.exists("memory"):
        os.mkdir("memory")
    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def load_memories():
    """读取所有已记住的事实，返回列表。文件坏了也不崩，返回空列表。"""
    _ensure_file()
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_memories(memories):
    """把事实列表写回 json 文件"""
    _ensure_file()
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memories, f, ensure_ascii=False, indent=2)


def add_memory(fact):
    """
    新增一条事实。为避免重复，如果已有完全相同的事实就不加。
    返回 True 表示新加成功，False 表示重复被忽略。
    """
    fact = fact.strip()
    if not fact:
        return False
    memories = load_memories()
    # 去重：一模一样的话就不再存一遍
    for item in memories:
        if item["fact"] == fact:
            return False
    memories.append({"fact": fact})
    save_memories(memories)
    return True


def delete_memory(index):
    """按序号删除一条事实（序号就是列表下标）"""
    memories = load_memories()
    if 0 <= index < len(memories):
        memories.pop(index)
        save_memories(memories)
        return True
    return False


# ===== 模块3：记忆护照相关功能 =====

def update_memory(index, new_fact):
    """修改第 index 条事实的内容。返回 True 表示成功。"""
    new_fact = new_fact.strip()
    if not new_fact:
        return False
    memories = load_memories()
    if 0 <= index < len(memories):
        memories[index]["fact"] = new_fact
        save_memories(memories)
        return True
    return False


def clear_memories():
    """清空全部记忆（不可恢复，界面上要二次确认）"""
    save_memories([])


def export_passport():
    """
    导出"记忆护照"——一个带版本号的开放 JSON 字典。
    包一层结构（而不是只导事实列表），是为了将来加字段不破坏老文件。
    """
    from datetime import datetime
    return {
        "format": "memory-passport",   # 格式标识：别人拿到就知道这是什么
        "version": "1.0",              # 版本号：将来升级格式能识别
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "facts": [item["fact"] for item in load_memories()]  # 只导事实文字，简单干净
    }


def import_passport(data, mode="merge"):
    """
    导入记忆护照。
    mode="merge"  : 合并——已有的保留，新的加进来（默认，更安全）
    mode="replace": 覆盖——清空后用导入的替换
    返回 (新增条数, 错误信息)；错误信息为空字符串表示成功。
    """
    # 第一层校验：格式标识对不对，防止用户传错文件
    if not isinstance(data, dict) or data.get("format") != "memory-passport":
        return 0, "不是有效的记忆护照文件"

    incoming = data.get("facts", [])
    if not isinstance(incoming, list):
        return 0, "护照里的事实列表格式不对"

    current = [] if mode == "replace" else load_memories()
    existing = {item["fact"] for item in current}  # 用集合加速去重查找
    added = 0
    for fact in incoming:
        if isinstance(fact, str) and fact.strip() and fact.strip() not in existing:
            current.append({"fact": fact.strip()})
            existing.add(fact.strip())
            added += 1
    save_memories(current)
    return added, ""


def format_memories():
    """
    把事实清单拼成一段文字，用来塞进系统提示词。
    比如 ["用户在准备考研", "用户养了一只猫"] ->
    "- 用户在准备考研\n- 用户养了一只猫"
    """
    memories = load_memories()
    if not memories:
        return "（暂无长期记忆）"
    return "\n".join(f'- {item["fact"]}' for item in memories)


# 让大模型从对话里抽取事实时用的提示词模板
EXTRACT_PROMPT = """请从下面这段对话中，提取"关于用户的、值得长期记住的事实"。

要求：
1. 只提取用户明确说过的、关于用户自己的信息（身份、职业、喜好、目标、计划、身边的人、身体状况等）
2. 不要提取闲聊内容、不要提取 AI 自己说的话、不要凭空猜测
3. 每条事实写成一句简短的陈述句，主语用"用户"
4. 如果没有值得记住的，返回空列表 []
5. 只返回一个 JSON 数组，不要任何解释文字，格式如：["用户在准备考研", "用户养了一只猫"]

对话：
用户：{user}
AI：{assistant}

现在只返回 JSON 数组："""
