<div align="center">

# 🌟 AI 智能伴侣 · 粉丝偶像陪伴版

**一个能记住你、懂你情绪、会主动找你，还能化身偶像与你私信聊天的开源 AI Agent 应用**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek-purple)](https://www.deepseek.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 🎯 **面试作品集项目**：打开即可亲手体验，代码模块化、知识点可讲解、能力可量化评测。

</div>

---

## 📖 一句话介绍

这是一个基于 **Streamlit + DeepSeek** 的对话式 AI 应用，包含两条产品线：

1. **🤖 AI 智能伴侣**：能定制角色、长期记忆、识别情绪、主动关怀、查知识库、调用工具、看懂图片的贴心伴侣。
2. **🌟 粉丝偶像陪伴**（核心创新）：懂饭圈黑话、会认粉丝身份、把官方动态改写成"偶像本人私信"、带追星护照和应援互动的虚拟陪伴体验。

整个系统由 **23 个 Python 模块、5 层架构** 组成，除 Streamlit/OpenAI/Pillow 外全部零依赖手写实现。

---

## 🖼️ 成品展示

### ① 主界面 · 四分区侧边栏

侧边栏用导航分区收纳所有功能，告别十几个板块平铺的混乱感。

![主界面](docs/images/01_home.png)

### ② 粉丝陪伴 · 偶像私信模式

进入偶像模式后，整屏切换成专属紫粉主题：偶像头图卡、粉丝身份徽章、AI 身份标识、应援互动条，一眼区别于普通聊天。

![偶像私信模式](docs/images/03_idol_mode.png)

### ③ 不同角色 · 专属头像与档案

每个角色有独一无二的 SVG 头像和饭圈设定（粉丝名、互称、雷区）。图为原创小说人物"沈砚"。

![小说人物沈砚](docs/images/04_idol_novel.png)

### ④ 侧边栏 · 粉丝功能区

偶像选择、私聊开关、档案速览、圈层语言测试台、互动应援、高级功能面板全部收纳在这里。

![粉丝功能分区](docs/images/02_fandom_tab.png)

> 💡 **演示深链接**：可直接访问 `?demo=idol` 进入偶像私聊、`?demo=fandom` 打开粉丝分区、`?demo=idol&idol=vtuber` 切换角色，方便面试官快速体验。

---

## ✨ 核心功能与亮点

### 🤖 伴侣线（通用 AI Agent 能力）

| 功能 | 说明 | 技术亮点 |
|---|---|---|
| 🎭 预设角色库 | 8 个开箱即用的角色（伴侣/爸妈/孩子/朋友/各类导师） | 数据与代码分离，加角色不动主程序 |
| 🧠 长期记忆 | 记住你随口说的偏好，跨会话自动注入 | **双层记忆**（会话+语义事实）、去重、记忆护照导出导入 |
| 💗 情感状态 | AI 有心情、好感度、亲密度，会随时间变化 | **PAD 情绪模型**、好感衰减/亲密累积、纯 SVG 雷达图 |
| 🔔 主动陪伴 | 久别重逢、时段问候、情绪关心、承诺提醒 | 拉取式架构、静音+冷却双闸门防骚扰 |
| 📚 知识库 RAG | 上传文档后 AI 基于文档回答 | **零依赖手写 TF-IDF** + 中文 n-gram + 余弦相似度 |
| 🛠️ AI 工具箱 | AI 自主调工具：查时间/算数/记事/检索/提醒/看心情 | **Function Calling + Agent Loop**、`ast` 安全计算 |
| 🖼️ 看图对话 | 上传图片，AI 看懂内容 | base64 data URI + Pillow 压缩省 token |
| 📊 评测基准 | 五维度可量化评测，可导出报告 | 离线/联网双模式、临时文件隔离 |

### 🌟 粉丝线（创新差异化能力）

| 功能 | 说明 | 技术亮点 |
|---|---|---|
| 🎤 偶像档案 | 3 个原创偶像，各带饭圈专属字段 | 原创角色规避肖像权/IP 授权风险 |
| 🗣️ 圈层语言引擎 | 识别 6 类粉丝身份、自动适配称呼、避开雷区 | 关键词规则引擎、提示词动态注入 |
| 💬 偶像私聊 | 用偶像口吻+饭圈规则聊天，身份累积识别 | 提示词分发器、快照-恢复零侵入切换 |
| 📰 动态转私信 | 官方公告改写成"偶像本人发的私信" | LLM 口吻转译 + 结果缓存避免重复烧钱 |
| 🌐 真实数据源 | 抓取公开 RSS/Atom 源自动入库 | **零依赖 RSS+Atom 双格式解析**、频率控制、去重 |
| 💼 追星护照 | 记录入坑时间/现场/周边，可导出携带 | 开放 JSON 格式、版本号、merge/replace |
| 🎫 票务卡 | 开售倒计时 + 跳官方链接 | **只提醒不交易**合规红线 |
| 🛡️ 分寸规则 | 不假装恋爱/不承诺见面/AI 身份明示 | 提示词约束 + 规则检测双保险 |
| 💌 主动私信 | 新动态/票务/生日/久别触发偶像主动发消息 | 四类触发器、静音+冷却闸门 |
| 🎊 互动特效 | 爱心雨/撒花/打call/烟花 | CSS 动画 + nonce 防重播 |

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│  ① 编排层    AI_partner.py — 状态管理 / 分区导航 / 对话主循环      │
├─────────────────────────────────────────────────────────────┤
│  ② 表现层    fandom_ui / fandom_panel / avatar / interactions  │
│              CSS主题 · HTML组件 · SVG头像 · 动画特效              │
├─────────────────────────────────────────────────────────────┤
│  ③ 对话层    idol_chat / fandom_lang / boundary_rules / tools   │
│              提示词注入 · 身份识别 · 分寸规则 · Function Calling  │
├─────────────────────────────────────────────────────────────┤
│  ④ 能力层    memory / emotion / proactive / rag / vision /      │
│              news_feed / fandom_passport / ticket_cards /       │
│              fandom_proactive / feed_source                     │
├─────────────────────────────────────────────────────────────┤
│  ⑤ 数据层    personas / idol_personas（纯配置表）                │
│  ──────────  横切：evaluation / fandom_eval（可量化评测）         │
└─────────────────────────────────────────────────────────────┘
```

**一条消息的数据流**：

```
用户输入 → [身份识别/踩雷检测] → [RAG检索] → 组装系统提示词
        → Agent Loop(工具自主调用) → 大模型生成 → [分寸检测]
        → [记忆抽取/情绪更新] → 落盘 → 展示（专属气泡/打字机）
```

两条产品线通过 `chat_mode` 开关共存，偶像模式用**快照-恢复**机制保护原伴侣系统不受影响。

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

```bash
# Windows PowerShell
$env:DEEPSEEK_API_KEY = "你的DeepSeek密钥"

# macOS / Linux
export DEEPSEEK_API_KEY="你的DeepSeek密钥"
```

> 🔑 密钥只从环境变量读取，**不会写入代码或仓库**。

### 3. 启动

```bash
streamlit run AI_partner.py
```

浏览器打开 `http://localhost:8501`。

### 4. 体验路径

- **普通模式**：直接聊天 → 侧边栏「🧠 记忆·知识」上传文档试 RAG →「⚙️ 情感·系统」看情绪雷达图。
- **粉丝模式**：侧边栏切到「🌟 粉丝陪伴」→ 选偶像 →「用 TA 的身份开始私聊」→ 发一句"我是同担，今天好累啊"看专属称呼 → 点"发爱心"看爱心雨。

---

## 📁 项目结构

<details>
<summary>点击展开 23 个模块清单</summary>

| 文件 | 定位 |
|---|---|
| `AI_partner.py` | 主程序：编排、状态、分区、对话主循环 |
| `personas.py` | 8 个伴侣角色配置表 |
| `memory.py` | 长期语义记忆 + 记忆护照 |
| `emotion.py` | PAD 情绪 + 双关系模型 + SVG 雷达图 |
| `proactive.py` | 伴侣版主动陪伴触发器 |
| `rag.py` | 零依赖 TF-IDF 检索 |
| `tools.py` | Function Calling 工具集 + AST 安全计算 |
| `evaluation.py` | 五维评测基准 |
| `vision.py` | 多模态图片处理 |
| `idol_personas.py` | 3 个偶像档案配置表 |
| `fandom_lang.py` | 圈层语言引擎 |
| `idol_chat.py` | 偶像对话引擎 + 模式开关 |
| `news_feed.py` | 动态存取 + 口吻转译 |
| `fandom_passport.py` | 追星护照 |
| `ticket_cards.py` | 票务/物料卡 |
| `boundary_rules.py` | 分寸与合规规则 |
| `fandom_proactive.py` | 粉丝版主动私信 |
| `fandom_eval.py` | 粉丝向四维评测 |
| `feed_source.py` | RSS/Atom 抓取器 |
| `fandom_ui.py` | 差异化前端组件 |
| `fandom_panel.py` | 粉丝功能面板封装 |
| `avatar.py` | 角色专属 SVG 头像 |
| `interactions.py` | CSS 动画互动特效 |

</details>

---

## 🎓 面向招聘：能力映射

本项目覆盖 AI 应用/ Agent 岗位的常见能力要求：

- **Prompt 工程**：动态系统提示词、角色 Persona 设计、上下文工程
- **Agent 开发**：Function Calling、Agent Loop、工具白名单、可解释性
- **RAG**：文档切块、TF-IDF、向量检索、阈值调优
- **记忆与状态**：双层记忆、session_state 管理、快照-恢复
- **多模态**：image_url 消息、base64、图片压缩
- **前端交互**：Streamlit 组件化、CSS 主题、SVG 生成、动画
- **工程素养**：数据代码分离、零依赖设计、异常兜底、可量化评测、合规意识

> 📄 详细的模块实现讲解、知识点拆解、面试问答预测，见项目配套的《面试技术报告》。

---

## ⚠️ 合规说明

- 项目中所有偶像角色（星遥/沈砚/阿栗）均为**原创虚构角色**，不使用任何真实明星的姓名、肖像、声音。
- 头像由 SVG 程序化生成，零图片文件、零版权风险。
- RSS 抓取仅面向公开订阅源，用于演示技术链路。
- 票务功能**只提醒不交易**，不收款、不抢票。
- 系统内置 AI 身份明示与分寸红线，不假装真人、不承诺私下见面。

本项目为**非商业学习演示**，如有任何合规问题请联系作者。

---

<div align="center">

⭐ 如果这个项目对你有帮助，欢迎 Star！

Made with ❤️ for learning & sharing

</div>
