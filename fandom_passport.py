# -*- coding: utf-8 -*-
"""
粉丝陪伴 · 追星护照（模块5）
============================

灵感来自项目里已有的"记忆护照"，但换成粉丝版：
记录"我是谁家的、什么时候入坑、看了哪些现场、买了哪些周边"。

为什么要单独做：
  · 真人偶像记不住几万个粉丝，但 AI 可以——这是订阅制产品做不到的差异点
  · 偶像主动提起"你上次说要去那场live"，粉丝会疯
  · 开放格式 + 可导出导入，数据属于粉丝自己，可携带

数据结构（一个偶像一份档案）：
  {
    "idol_key": {
      "join_date": "入坑时间",
      "fandom_name": "粉丝名（自动从档案带出）",
      "concerts": [{"name":..., "date":..., "city":...}],
      "merch": [{"name":..., "date":...}],
      "notes": ["自由记录"]
    }
  }
"""

import os
import json
from datetime import datetime

PASSPORT_FILE = "fandom_data/fandom_passport.json"


def _ensure_file():
    if not os.path.exists("fandom_data"):
        os.makedirs("fandom_data", exist_ok=True)
    if not os.path.exists(PASSPORT_FILE):
        with open(PASSPORT_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)


def load_all():
    """读取全部护照数据"""
    _ensure_file()
    try:
        with open(PASSPORT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_all(data):
    _ensure_file()
    with open(PASSPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _blank():
    """一个新偶像的空白护照"""
    return {"join_date": "", "concerts": [], "merch": [], "notes": []}


def get_passport(idol_key):
    """取某个偶像的护照，没有就返回空白结构（不写盘，读到才写）"""
    data = load_all()
    return data.get(idol_key, _blank())


def update_passport(idol_key, **fields):
    """更新某个偶像护照的字段，返回更新后的护照"""
    data = load_all()
    if idol_key not in data:
        data[idol_key] = _blank()
    for k, v in fields.items():
        if k in data[idol_key]:
            data[idol_key][k] = v
    save_all(data)
    return data[idol_key]


def set_join_date(idol_key, date_str):
    return update_passport(idol_key, join_date=date_str)


def add_concert(idol_key, name, date_str="", city=""):
    """记一场看过的现场"""
    p = get_passport(idol_key)
    p["concerts"].append({"name": name.strip(), "date": date_str, "city": city})
    update_passport(idol_key, concerts=p["concerts"])
    return p["concerts"]


def remove_concert(idol_key, index):
    p = get_passport(idol_key)
    if 0 <= index < len(p["concerts"]):
        p["concerts"].pop(index)
        update_passport(idol_key, concerts=p["concerts"])
        return True
    return False


def add_merch(idol_key, name, date_str=""):
    """记一件买过的周边"""
    p = get_passport(idol_key)
    p["merch"].append({"name": name.strip(), "date": date_str})
    update_passport(idol_key, merch=p["merch"])
    return p["merch"]


def remove_merch(idol_key, index):
    p = get_passport(idol_key)
    if 0 <= index < len(p["merch"]):
        p["merch"].pop(index)
        update_passport(idol_key, merch=p["merch"])
        return True
    return False


def add_note(idol_key, text):
    """自由记录一句，比如'第一次接机'"""
    p = get_passport(idol_key)
    if text.strip():
        p["notes"].append(text.strip())
        update_passport(idol_key, notes=p["notes"])
    return p["notes"]


def days_since_join(idol_key):
    """入坑多少天了；没填或格式错返回 None"""
    p = get_passport(idol_key)
    if not p.get("join_date"):
        return None
    try:
        d = datetime.strptime(p["join_date"], "%Y-%m-%d")
        return (datetime.now() - d).days
    except Exception:
        return None


def format_for_prompt(idol_key):
    """把护照拼成一段文字，注入系统提示词，让偶像'记得'这段关系"""
    p = get_passport(idol_key)
    lines = []
    if p.get("join_date"):
        days = days_since_join(idol_key)
        suffix = f"（已经 {days} 天了）" if days is not None and days >= 0 else ""
        lines.append(f"- 粉丝 {p['join_date']} 入坑{suffix}，是个老资格了")
    if p.get("concerts"):
        names = "、".join(c["name"] for c in p["concerts"][-5:])
        lines.append(f"- 一起经历过这些现场：{names}")
    if p.get("merch"):
        names = "、".join(m["name"] for m in p["merch"][-5:])
        lines.append(f"- Ta 收藏的周边：{names}")
    if p.get("notes"):
        lines.append("- Ta 还说过：" + "；".join(p["notes"][-3:]))
    return "\n".join(lines) if lines else "（这份追星护照还是空的）"


def export_passport():
    """导出开放格式，版本号兜底，方便将来字段升级"""
    return {
        "format": "fandom-passport",
        "version": "1.0",
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "passports": load_all(),
    }


def import_passport(data, mode="merge"):
    """
    导入追星护照。merge=合并，replace=覆盖。
    返回 (导入的偶像份数, 错误信息)。
    """
    if not isinstance(data, dict) or data.get("format") != "fandom-passport":
        return 0, "不是有效的追星护照文件"
    incoming = data.get("passports", {})
    if not isinstance(incoming, dict):
        return 0, "护照数据格式不对"
    current = {} if mode == "replace" else load_all()
    for key, val in incoming.items():
        if isinstance(val, dict):
            if key in current and mode == "merge":
                # 合并：列表叠加去重，标量用新的覆盖
                for f in ("concerts", "merch", "notes"):
                    old = current[key].get(f, [])
                    new = val.get(f, [])
                    combined = old + [x for x in new if x not in old]
                    current[key][f] = combined
                if val.get("join_date"):
                    current[key]["join_date"] = val["join_date"]
            else:
                current[key] = val
    save_all(current)
    return len(incoming), ""
