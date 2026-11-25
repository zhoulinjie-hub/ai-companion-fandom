"""
评测基准模块（模块8）：让系统的能力可量化、可复现。

为什么重要：
  别人开源项目只放几张聊天截图，你能放一张"五维度评测报告 + 总分"。
  面试官问"你怎么证明这系统好用"，你拿出实测分数，比空口说强得多。
  以后改代码，跑一遍评测就知道有没有把旧功能改坏（回归测试）。

五个维度：
  ① 工具调用  ② 记忆与去重  ③ RAG检索  ④ 安全  ⑤ 角色一致性

两种模式：
  offline（默认）：只测本地规则逻辑，秒出、零成本、不需要网络
  online（可选）：真的调用 DeepSeek，验证模型能否正确触发工具
"""

import json
import os
from datetime import datetime

import memory
import rag
import proactive
import emotion
import tools
from personas import PERSONAS


REPORT_DIR = "evaluation/reports"


# ===== 测试用例集（这是评测的核心资产，面试时可单独展示）=====

# 工具调用：问题 → 期望触发的工具名
TOOL_CASES = [
    {"question": "(35+47)*2等于多少？", "expect": "calculate"},
    {"question": "现在几点了？", "expect": "get_current_time"},
    {"question": "今天星期几？", "expect": "get_current_time"},
    {"question": "记住我在准备考研", "expect": "remember_fact"},
    {"question": "帮我算 100 除以 7", "expect": "calculate"},
    {"question": "3 小时后提醒我交材料", "expect": "set_reminder"},
]

# RAG检索：文档内容 → 一组该命中/不该命中的问题
RAG_CASES = [
    {"doc": "考研数学复习指南.txt",
     "text": "考研数学要复习高等数学、线性代数、概率论。每天做两套真题，错题要整理到本子上反复看。",
     "should_hit": "考研数学怎么复习",
     "should_miss": "今天天气怎么样"},
    {"doc": "养猫手册.txt",
     "text": "猫喜欢晒太阳，要定期铲屎，喂猫粮和罐头。猫砂盆要放在安静的地方，每天清理一次。",
     "should_hit": "猫砂盆怎么放",
     "should_miss": "股票怎么开户"},
]

# 安全测试：恶意/异常输入是否会被正确拦下
SECURITY_CASES = [
    # 计算工具：注入攻击必须被拒，不能真的执行
    {"name": "代码注入拦截", "tool": "calculate",
     "args": {"expression": "__import__('os').system('echo HACK')"}, "must_reject": True},
    {"name": "除以零拦截", "tool": "calculate",
     "args": {"expression": "1/0"}, "must_reject": True},
    # 白名单：没登记的工具必须拒绝
    {"name": "陌生工具拒绝", "tool": "delete_all_files",
     "args": {}, "must_reject": True},
    # 正常计算必须放行（反向测试，防止"一刀切全拒绝"）
    {"name": "正常计算放行", "tool": "calculate",
     "args": {"expression": "12*12"}, "must_reject": False},
]


# ===== 五个维度的评测函数 =====

def eval_memory():
    """② 记忆：存→读→去重，用临时文件避免污染真实记忆"""
    import tempfile
    original_file = memory.MEMORY_FILE
    tmpdir = tempfile.mkdtemp()
    memory.MEMORY_FILE = os.path.join(tmpdir, "test_memories.json")
    try:
        score = 0
        total = 0
        details = []

        # 用例1：新增一条事实
        total += 1
        ok1 = memory.add_memory("评测用户养了一只猫")
        score += 1 if ok1 else 0
        details.append({"case": "新增事实", "pass": ok1})

        # 用例2：能读回来
        total += 1
        facts = memory.load_memories()
        ok2 = any("猫" in f["fact"] for f in facts)
        score += 1 if ok2 else 0
        details.append({"case": "读回事实", "pass": ok2})

        # 用例3：重复内容被去重（幂等）
        total += 1
        ok3 = (memory.add_memory("评测用户养了一只猫") is False)
        score += 1 if ok3 else 0
        details.append({"case": "重复去重", "pass": ok3})

        return {"score": score, "total": total, "details": details}
    finally:
        # 无论成功失败，都把记忆文件路径还原，绝不留下副作用
        memory.MEMORY_FILE = original_file


def eval_rag():
    """③ RAG：相关文档命中、无关问题过滤，同样用临时索引"""
    import tempfile
    original_file = rag.INDEX_FILE
    tmpdir = tempfile.mkdtemp()
    rag.INDEX_FILE = os.path.join(tmpdir, "test_index.json")
    try:
        score = 0
        total = 0
        details = []

        for case in RAG_CASES:
            rag.add_document(case["doc"], case["text"])

            # 相关问题是命中
            total += 1
            hits = rag.search(case["should_hit"])
            hit_ok = len(hits) > 0
            score += 1 if hit_ok else 0
            details.append({"case": f"命中：{case['should_hit']}", "pass": hit_ok})

            # 无关问题应被过滤（不命中这个文档）
            total += 1
            miss_hits = rag.search(case["should_miss"])
            miss_ok = not any(case["doc"] == h[1] for h in miss_hits)
            score += 1 if miss_ok else 0
            details.append({"case": f"过滤：{case['should_miss']}", "pass": miss_ok})

        return {"score": score, "total": total, "details": details}
    finally:
        rag.INDEX_FILE = original_file


def eval_security():
    """④ 安全：注入被拦、陌生工具被拒、正常计算放行"""
    score = 0
    details = []
    for case in SECURITY_CASES:
        result = tools.execute_tool(case["tool"], case["args"])
        rejected = ("失败" in result) or ("未知工具" in result)
        passed = (rejected == case["must_reject"])
        score += 1 if passed else 0
        details.append({"case": case["name"], "pass": passed, "result": result[:60]})
    return {"score": score, "total": len(SECURITY_CASES), "details": details}


def eval_persona():
    """⑤ 角色一致性：每个角色的字段是否齐全、能否按 key 找到"""
    from personas import get_persona
    required = ("key", "name", "icon", "category", "identity", "nature", "greeting", "examples")
    score = 0
    total = 0
    details = []
    for p in PERSONAS:
        total += 1
        complete = all(k in p and p[k] for k in required)
        # 再验证按 key 能找回同一个角色
        retrievable = get_persona(p["key"])["key"] == p["key"]
        ok = complete and retrievable
        score += 1 if ok else 0
        details.append({"case": f"角色 {p['name']}", "pass": ok})
    return {"score": score, "total": total, "details": details}


def eval_tool_offline():
    """
    ① 工具调用（离线档）：不调大模型，直接验证工具说明书格式合法、
       每个声明的工具都有对应执行器。这是 Agent 能工作的基础设施检查。
    """
    score = 0
    total = 0
    details = []

    # 检查1：每条工具说明书格式是否完整
    for t in tools.TOOL_DEFINITIONS:
        total += 1
        fn = t.get("function", {})
        ok = bool(fn.get("name")) and bool(fn.get("description")) and "parameters" in fn
        score += 1 if ok else 0
        details.append({"case": f"说明书 {fn.get('name', '?')}", "pass": ok})

    # 检查2：每个说明书里的工具都有执行器（避免"说了却做不了"）
    for t in tools.TOOL_DEFINITIONS:
        name = t["function"]["name"]
        total += 1
        ok = name in tools.TOOL_HANDLERS
        score += 1 if ok else 0
        details.append({"case": f"执行器 {name}", "pass": ok})

    return {"score": score, "total": total, "details": details}


def eval_tool_online(client, model="deepseek-chat"):
    """
    ① 工具调用（联网真实档）：真的问 DeepSeek，看它能否为每类问题
       选中正确的工具。这才是验证"模型决策"真实能力的评测。
    需要传一个已经创建好的 OpenAI client。
    """
    score = 0
    details = []
    for case in TOOL_CASES:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个助手。需要时使用工具，用完根据结果自然回答。"},
                    {"role": "user", "content": case["question"]}
                ],
                tools=tools.TOOL_DEFINITIONS,
                tool_choice="auto",
                stream=False,
                temperature=0
            )
            msg = resp.choices[0].message
            called = [tc.function.name for tc in (msg.tool_calls or [])]
            ok = case["expect"] in called
            score += 1 if ok else 0
            details.append({"case": case["question"], "pass": ok,
                            "expect": case["expect"], "called": called})
        except Exception as e:
            details.append({"case": case["question"], "pass": False, "error": str(e)[:80]})
    return {"score": score, "total": len(TOOL_CASES), "details": details}


# ===== 汇总报告 =====

def run_all_offline():
    """跑全部离线维度，返回一份完整报告"""
    dimensions = {
        "工具调用(基础设施)": eval_tool_offline(),
        "记忆与去重": eval_memory(),
        "RAG检索": eval_rag(),
        "安全测试": eval_security(),
        "角色一致性": eval_persona(),
    }
    return build_report(dimensions, mode="offline")


def run_all_online(client, model="deepseek-chat"):
    """跑全部维度，其中工具调用用真实模型"""
    dimensions = {
        "工具调用(真实模型)": eval_tool_online(client, model),
        "记忆与去重": eval_memory(),
        "RAG检索": eval_rag(),
        "安全测试": eval_security(),
        "角色一致性": eval_persona(),
    }
    return build_report(dimensions, mode="online")


def build_report(dimensions, mode):
    """把各维度分数汇总成一份带总分的报告字典"""
    total_score = sum(d["score"] for d in dimensions.values())
    total_count = sum(d["total"] for d in dimensions.values())
    pct = round(total_score / total_count * 100, 1) if total_count else 0
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": mode,
        "summary": {
            "total_score": total_score,
            "total_cases": total_count,
            "pass_rate": pct,
            "dimensions": {
                name: {
                    "score": d["score"], "total": d["total"],
                    "rate": round(d["score"] / d["total"] * 100, 1) if d["total"] else 0
                }
                for name, d in dimensions.items()
            }
        },
        "details": dimensions,   # 每题明细都留着，出问题能定位
    }


def save_report(report):
    """把报告存成 json，留档、可对比历史成绩"""
    if not os.path.exists(REPORT_DIR):
        os.makedirs(REPORT_DIR, exist_ok=True)
    filename = f"report_{report['generated_at'].replace(':', '-').replace(' ', '_')}_{report['mode']}.json"
    path = os.path.join(REPORT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return path


def format_report_markdown(report):
    """把报告转成 Markdown，方便贴到 README / 简历 / 面试文档"""
    s = report["summary"]
    lines = [
        f"# AI 伴侣系统评测报告",
        "",
        f"- 生成时间：{report['generated_at']}",
        f"- 评测模式：{report['mode']}",
        f"- **总分：{s['total_score']}/{s['total_cases']}（通过率 {s['pass_rate']}%）**",
        "",
        "| 维度 | 通过 | 总数 | 通过率 |",
        "|---|---|---|---|",
    ]
    for name, d in s["dimensions"].items():
        lines.append(f"| {name} | {d['score']} | {d['total']} | {d['rate']}% |")
    return "\n".join(lines)
