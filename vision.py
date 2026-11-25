"""
多模态视觉模块（模块9）：让 AI 能看懂图片。

实测结论：DeepSeek 的 deepseek-chat 支持视觉输入（image_url），
能准确读出图中文字、识别颜色、描述场景。所以这里做的是真正的视觉理解。

核心概念：
- base64：把图片二进制变成一串文本，塞进 JSON 传给大模型（data:image/...;base64,...）
- 多模态消息：content 不再是字符串，而是 [文字块, 图片块] 组成的列表
- Pillow：读图片的宽高、格式，并压缩大图（省 token、省流量）
"""

import base64
import io
from PIL import Image

# 大图先缩小到这个最大边长，避免传输太大、浪费 token
MAX_SIDE = 1024


def process_image(uploaded_file):
    """
    接收 Streamlit 上传的文件对象，返回 (data_url, info_dict)。
    data_url 形如 "data:image/png;base64,xxxxx"，可直接给多模态消息用。
    """
    raw = uploaded_file.getvalue()
    img = Image.open(io.BytesIO(raw))
    fmt = (img.format or "PNG").upper()
    orig_size = img.size  # (宽, 高)

    # 大图等比缩小，控制体积
    if max(orig_size) > MAX_SIDE:
        ratio = MAX_SIDE / max(orig_size)
        new_size = (int(orig_size[0] * ratio), int(orig_size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    # 统一转 RGB 再存 PNG，避免 RGBA/P 模式的兼容问题
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    data_url = f"data:image/png;base64,{b64}"

    info = {
        "name": getattr(uploaded_file, "name", "image"),
        "format": fmt,
        "size": orig_size,
        "compressed": max(orig_size) > MAX_SIDE,
    }
    return data_url, info


def build_vision_message(text, data_url):
    """
    构造一条带图的用户消息。
    content 是列表：先文字块，再图片块 —— 这是 OpenAI 兼容的多模态格式。
    """
    return {
        "role": "user",
        "content": [
            {"type": "text", "text": text},
            {"type": "image_url", "image_url": {"url": data_url, "detail": "auto"}}
        ]
    }


def describe_image_info(info):
    """把图片元信息变成一行友好文字，展示给用户"""
    w, h = info["size"]
    extra = "（已自动压缩）" if info["compressed"] else ""
    return f"{info['name']} · {info['format']} · {w}×{h}{extra}"
