# -*- coding: utf-8 -*-
"""
粉丝陪伴 · 票务/物料卡片（模块6）
==================================

给用户展示"开售提醒、倒计时、跳官方链接"。

硬规则：只提醒，不交易。
  · 绝不自己做收款、下单、抢票
  · 只跳官方链接，价格/余票以官方为准
  · 这是合规红线，也是产品信誉线——票务纠纷粉丝最容易被骗

数据结构：
  {"id","idol_key","title","sale_time","official_url","note","created_at"}
"""

import os
import json
from datetime import datetime

TICKET_FILE = "fandom_data/tickets.json"
TIME_FMT = "%Y-%m-%d %H:%M"


def _ensure_file():
    if not os.path.exists("fandom_data"):
        os.makedirs("fandom_data", exist_ok=True)
    if not os.path.exists(TICKET_FILE):
        with open(TICKET_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def load_tickets(idol_key=None):
    _ensure_file()
    try:
        with open(TICKET_FILE, "r", encoding="utf-8") as f:
            items = json.load(f)
    except Exception:
        return []
    if idol_key:
        items = [t for t in items if t.get("idol_key") == idol_key]
    # 按开售时间从近到远排；没填时间的排最后
    return sorted(items, key=lambda x: x.get("sale_time") or "9999")


def save_tickets(items):
    _ensure_file()
    with open(TICKET_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def add_ticket(idol_key, title, sale_time="", official_url="", note=""):
    """新增一条票务/物料提醒"""
    items = load_tickets()
    tid = datetime.now().strftime("%Y%m%d%H%M%S") + str(len(items) % 100)
    items.append({
        "id": tid,
        "idol_key": idol_key,
        "title": title.strip(),
        "sale_time": sale_time,
        "official_url": official_url.strip(),
        "note": note.strip(),
        "created_at": datetime.now().strftime(TIME_FMT),
    })
    save_tickets(items)
    return tid


def delete_ticket(tid):
    items = load_tickets()
    before = len(items)
    items = [t for t in items if t.get("id") != tid]
    if len(items) < before:
        save_tickets(items)
        return True
    return False


def days_until(sale_time):
    """距离开售还有几天；已过时返回负数；格式错返回 None"""
    if not sale_time:
        return None
    for fmt in (TIME_FMT, "%Y-%m-%d"):
        try:
            d = datetime.strptime(sale_time, fmt)
            return (d - datetime.now()).days
        except Exception:
            continue
    return None


def status_of(ticket):
    """返回这张卡的展示状态：'即将开售'/'已开售'/'待公布'"""
    d = days_until(ticket.get("sale_time", ""))
    if d is None:
        return "待公布"
    if d < 0:
        return "已开售"
    if d <= 3:
        return "即将开售"
    return f"还有 {d} 天"


def demo_tickets_for(idol_key):
    """演示用的示例票务（原创虚构，不指向真实售票页）"""
    demos = {
        "virtual_singer": [
            {"title": "《星轨》限定实体专辑", "sale_time": "2026-12-01 12:00",
             "official_url": "", "note": "含签名小卡，数量有限，以官方公告为准"},
        ],
        "novel_hero": [
            {"title": "典藏版第4册预售", "sale_time": "2026-12-15 10:00",
             "official_url": "", "note": "出版社官方渠道，谨防盗版"},
        ],
        "vtuber": [
            {"title": "周年纪念周边套装", "sale_time": "2026-11-30 20:00",
             "official_url": "", "note": "直播间同款，官方周边店"},
        ],
    }
    return demos.get(idol_key, [])
