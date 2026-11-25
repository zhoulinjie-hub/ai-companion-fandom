# -*- coding: utf-8 -*-
"""
粉丝陪伴 · 功能面板集合（模块4-10 的界面层）
================================================

把实验窗口里的所有新功能面板封装成函数，主程序只需调用 render_all()。
这样主程序保持简洁，面板逻辑集中在这里。

面板清单：
  render_news_panel     动态转私信
  render_passport_panel 追星护照
  render_ticket_panel   票务卡片
  render_proactive_panel 主动推送设置
  render_boundary_panel 分寸与合规
  render_eval_panel     粉丝向评测

每个函数自己惰性创建 client（Streamlit 脚本从上往下跑，client 在主程序
后段才创建，面板若依赖它会有先后问题，所以这里用缓存的 client）。
"""

import os

_client_cache = None


def _get_client():
    """惰性创建并缓存 OpenAI client，避免重复创建"""
    global _client_cache
    if _client_cache is None:
        from openai import OpenAI
        _client_cache = OpenAI(
            api_key=os.environ.get("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )
    return _client_cache


def render_news_panel(st, idol):
    """动态转私信：真实抓取/示例 → 转成偶像口吻私信 → 展示对照卡"""
    import news_feed
    import fandom_ui
    import feed_source

    st.markdown("**📰 动态转私信**")
    st.caption("把抓来的动态改写成'偶像本人发给你的私信'——这是追星感的关键")
    key = idol["key"]

    # ===== 真实数据源抓取 =====
    with st.expander("🌐 数据源（真实 RSS 抓取）"):
        st.caption("从公开 RSS/Atom 源抓取真实动态，自动去重、有频率限制")
        sources = feed_source.list_sources()
        for s in sources:
            st.caption(f"· **{s['name']}** — {s.get('note','')}")
        if st.button("立即抓取全部源", width="stretch", icon="🔄", key="fetch_all_btn"):
            with st.spinner("正在抓取公开源…"):
                items, errors = feed_source.fetch_all(force=True)
                added = feed_source.sync_to_news(items, key)
            if added:
                st.toast(f"抓到 {len(items)} 条，新入库 {added} 条")
            else:
                st.info("这次没有新条目（可能已抓过或源暂时不可用）")
            for name, err in errors:
                st.caption(f"⚠️ {name}：{err[:50]}")
            if added:
                st.rerun()

        # 自定义源
        with st.expander("➕ 添加自定义 RSS 源"):
            sk = st.text_input("源标识（英文）", key="fs_key", placeholder="my_idol")
            sn = st.text_input("显示名称", key="fs_name", placeholder="官方动态")
            su = st.text_input("RSS/Atom 地址", key="fs_url", placeholder="https://.../feed.xml")
            if st.button("添加这个源", width="stretch", key="fs_add"):
                if sk.strip() and sn.strip() and su.strip():
                    feed_source.add_source(sk, sn, su)
                    st.toast(f"已添加 {sn}")
                    st.rerun()
                else:
                    st.warning("三项都要填")

    # 载入示例（保留，作为无网络时的兜底）
    if st.button("载入示例动态（离线兜底）", width="stretch", icon="📥", key="load_demo_news"):
        demos = news_feed.demo_news_for(key)
        for d in demos:
            news_feed.add_news(
                key, d["title"], d["content"], d["type"], d["source"]
            )
        st.toast(f"载入了 {len(demos)} 条示例动态")
        st.rerun()

    news_list = news_feed.load_news(key)
    if not news_list:
        st.caption("还没有动态，点上面按钮载入示例")
        return

    st.caption(f"共 {len(news_list)} 条动态")
    for news in news_list:
        rewritten = news.get("rewritten", "")
        st.markdown(fandom_ui.news_card(news, rewritten), unsafe_allow_html=True)
        if not rewritten:
            if st.button(f"让 TA 用口吻告诉我", key=f"rewrite_{news['id']}"):
                with st.spinner("正在改写…"):
                    text = news_feed.rewrite_to_dm(news, idol, _get_client())
                if text:
                    news_feed.mark_rewritten(news["id"], text)
                    st.toast("改好了")
                    st.rerun()
                else:
                    st.error("改写失败，检查 API Key")


def render_passport_panel(st, idol):
    """追星护照：编辑入坑时间/现场/周边，时间轴可视化，导出导入"""
    import fandom_passport as fp
    import fandom_ui
    import json

    st.markdown("**💜 追星护照**")
    st.caption("你什么时候入坑、看了哪些现场——让 TA 记得这段关系")
    key = idol["key"]
    p = fp.get_passport(key)
    days = fp.days_since_join(key)

    with st.expander("编辑护照"):
        join = st.text_input("入坑时间（YYYY-MM-DD）", value=p.get("join_date", ""),
                             key="pp_join")
        if st.button("保存入坑时间", key="pp_save_join"):
            fp.set_join_date(key, join)
            st.toast("保存好了")
            st.rerun()

        c1, c2 = st.columns([3, 1])
        with c1:
            concert = st.text_input("看过的现场/演出名", key="pp_concert")
        with c2:
            cd = st.text_input("日期", key="pp_cdate", placeholder="YYYY-MM-DD")
        if st.button("加一条现场", key="pp_add_concert"):
            if concert.strip():
                fp.add_concert(key, concert, cd)
                st.rerun()

        m1, m2 = st.columns([3, 1])
        with m1:
            merch = st.text_input("收藏的周边", key="pp_merch")
        with m2:
            md = st.text_input("日期", key="pp_mdate")
        if st.button("加一条周边", key="pp_add_merch"):
            if merch.strip():
                fp.add_merch(key, merch, md)
                st.rerun()

        note = st.text_input("随手记一句", key="pp_note")
        if st.button("记下来", key="pp_add_note"):
            fp.add_note(key, note)
            st.rerun()

    st.markdown(fandom_ui.passport_timeline(p), unsafe_allow_html=True)
    if days is not None and days >= 0:
        st.caption(f"💜 已经陪 TA 走过 {days} 天")

    # 导出/导入
    exp = json.dumps(fp.export_passport(), ensure_ascii=False, indent=2)
    st.download_button("⬇️ 导出追星护照", data=exp, file_name="fandom-passport.json",
                       width="stretch", key="pp_export")
    up = st.file_uploader("⬆️ 导入追星护照", type=["json"], key="pp_import")
    if up is not None:
        try:
            data = json.load(up)
            cnt, err = fp.import_passport(data, mode="merge")
            if err:
                st.error(err)
            else:
                st.toast(f"导入了 {cnt} 份护照")
                st.rerun()
        except Exception:
            st.error("文件解析失败")


def render_ticket_panel(st, idol):
    """票务卡片：只提醒不交易"""
    import ticket_cards as tc
    import fandom_ui

    st.markdown("**🎫 票务 / 物料提醒**")
    st.caption("开售倒计时 + 跳官方链接 · 只提醒，不售票不收款")
    key = idol["key"]

    if st.button("载入示例票务", width="stretch", icon="📥", key="load_demo_ticket"):
        for t in tc.demo_tickets_for(key):
            tc.add_ticket(key, t["title"], t["sale_time"], t["official_url"], t["note"])
        st.toast("载入了示例票务")
        st.rerun()

    tickets = tc.load_tickets(key)
    if not tickets:
        st.caption("还没有提醒，点上面按钮载入示例")
        return
    for t in tickets:
        st.markdown(fandom_ui.ticket_card(t), unsafe_allow_html=True)
        if st.button("删除这条", key=f"del_ticket_{t['id']}"):
            tc.delete_ticket(t["id"])
            st.rerun()


def render_proactive_panel(st, idol):
    """主动推送设置：静音、生日、手动预览一条主动私信"""
    import fandom_proactive as fpro

    st.markdown("**🔔 偶像主动私信**")
    st.caption("新动态/票务/生日/久别时，TA 主动来私信你")
    state = fpro.load_state()

    muted = st.toggle("🔕 静音", value=state["muted"], key="fm_pro_muted")
    if muted != state["muted"]:
        fpro.set_muted(muted)
        st.rerun()

    bday = st.text_input("你的生日（MM-DD，可留空）", value=state.get("birthday", ""),
                         key="fm_bday", placeholder="11-25")
    if st.button("保存生日", key="fm_save_bday"):
        ok, err = fpro.set_birthday(bday)
        if ok:
            st.toast("生日保存好了，当天 TA 会来祝福")
        else:
            st.error(err)

    if st.button("👀 预览一条主动私信", width="stretch", key="fm_preview_active"):
        news = news_feed_unpushed(idol["key"])
        trigger = fpro.check_trigger(
            idol["key"],
            unpushed_news=news,
            tickets=ticket_cards_load(idol["key"])
        )
        if not trigger:
            st.info("现在没有触发条件（可能被静音/冷却中）。稍后再试或载入新动态。")
        else:
            with st.spinner("TA 正在想怎么开口…"):
                text = generate_dm(idol, trigger)
            if text:
                st.success(f"【{trigger['kind']}】{text}")


def news_feed_unpushed(key):
    import news_feed
    return news_feed.get_unpushed(key)


def ticket_cards_load(key):
    import ticket_cards
    return ticket_cards.load_tickets(key)


def generate_dm(idol, trigger):
    """生成一条主动私信（转译/触发共用一套 prompt）"""
    import fandom_proactive as fpro
    import boundary_rules as br

    news_detail = ""
    if_news = ""
    if trigger.get("news"):
        n = trigger["news"]
        if_news = "【这条动态】"
        news_detail = f"{n.get('title','')}：{n.get('content','')}"

    prompt = fpro.PROACTIVE_DM_PROMPT.format(
        name=idol["nick_name"],
        identity=idol["identity"],
        nature=idol["nature"],
        kind=trigger["kind"],
        hint=trigger["hint"],
        rules=br.BOUNDARY_PROMPT,
        fandom_name=idol["fandom_name"],
        idol_call=idol["idol_call"],
        if_news=if_news,
        news_detail=news_detail,
        end_news="" if if_news else "",
    )
    try:
        resp = _get_client().chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            temperature=0.8
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print("生成主动私信失败:", e)
        return None


def render_boundary_panel(st, idol):
    """分寸与合规：展示红线 + AI 身份标识"""
    import boundary_rules as br
    import fandom_ui

    st.markdown("**🛡️ 分寸与合规**")
    st.markdown(fandom_ui.ai_disclosure_bar(), unsafe_allow_html=True)
    st.caption("以下红线优先级高于饭圈规则，AI 必须遵守：")
    for line in br.BOUNDARY_PROMPT.split("\n"):
        if line.strip() and line.strip()[0].isdigit():
            st.caption(line.strip())


def render_eval_panel(st, idol):
    """粉丝向评测：一键跑分"""
    import fandom_eval

    st.markdown("**📊 粉丝陪伴评测**")
    st.caption("称呼正确率 / 分寸安全 / 护照完整性 / 转译格式")
    if st.button("跑一遍粉丝评测", width="stretch", icon="▶️", key="fm_eval_run"):
        with st.spinner("评测中…"):
            report = fandom_eval.run_all()
        s = report["summary"]
        st.metric("总分", f"{s['total_score']}/{s['total_cases']}",
                  delta=f"{s['pass_rate']}% 通过")
        for name, d in s["dimensions"].items():
            st.caption(f"{name}：{d['score']}/{d['total']}（{d['rate']}%）")
        st.download_button("⬇️ 导出报告", data=fandom_eval.format_markdown(report),
                           file_name="fandom-eval.md", width="stretch", key="fm_eval_dl")


def render_all(st, idol):
    """在实验窗口里依次渲染所有新面板"""
    st.divider()
    render_news_panel(st, idol)
    st.divider()
    render_passport_panel(st, idol)
    st.divider()
    render_ticket_panel(st, idol)
    st.divider()
    render_proactive_panel(st, idol)
    st.divider()
    render_boundary_panel(st, idol)
    st.divider()
    render_eval_panel(st, idol)
