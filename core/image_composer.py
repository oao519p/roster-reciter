"""
Pillow 圖片合成核心。
"""
from __future__ import annotations
from pathlib import Path
import io

from PIL import Image, ImageDraw, ImageFont, ImageColor

from .layout import Layout, ImageSlot, TextStyle, AvatarBox, LabelBox, DateBox

_font_cache: dict = {}


def _get_font(style: TextStyle):
    key = (style.font_path, style.font_size)
    if key in _font_cache:
        return _font_cache[key]
    try:
        if style.font_path and Path(style.font_path).exists():
            font = ImageFont.truetype(style.font_path, style.font_size)
        else:
            font = ImageFont.load_default(size=style.font_size)
    except Exception:
        font = ImageFont.load_default()
    _font_cache[key] = font
    return font


def _fit_image_cover(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def _parse_color(hex_color: str, default=(255, 255, 255, 255)) -> tuple:
    """解析 hex 色碼，回傳 RGBA tuple。空字串回傳 None（透明）。"""
    if not hex_color or hex_color.strip() == "":
        return None
    try:
        rgb = ImageColor.getrgb(hex_color)
        return rgb + (255,) if len(rgb) == 3 else rgb
    except ValueError:
        return default


def compose_slide(
    layout: Layout,
    title_text: str,
    image_paths: list,
    avatar_paths: list = None,   # 每位玩家的頭像路徑，None 表示無
    background_image=None,
    output_path=None,
) -> bytes:
    canvas_w = layout.canvas.width
    canvas_h = layout.canvas.height

    if avatar_paths is None:
        avatar_paths = [None] * len(layout.image_slots)

    # 背景
    if background_image and Path(background_image).exists():
        bg = Image.open(background_image).convert("RGBA")
        canvas = _fit_image_cover(bg, canvas_w, canvas_h)
        if canvas.mode != "RGBA":
            canvas = canvas.convert("RGBA")
    else:
        bg_color = _parse_color(layout.canvas.background_color) or (26, 26, 46, 255)
        canvas = Image.new("RGBA", (canvas_w, canvas_h), bg_color)

    draw = ImageDraw.Draw(canvas)

    # 玩家圖片 → 頭像 → 名字（由下往上，確保覆蓋順序正確）
    for slot in layout.image_slots:
        idx = slot.player_index
        img_path = image_paths[idx] if idx < len(image_paths) else None
        av_path  = avatar_paths[idx] if idx < len(avatar_paths) else None

        # ── 角色圖片 ──
        if img_path and Path(img_path).exists():
            try:
                img = Image.open(img_path).convert("RGBA")
                img = _fit_image_cover(img, slot.width, slot.height)
                canvas.paste(img, (slot.x, slot.y), img)
            except Exception:
                _draw_placeholder(draw, slot, "載入失敗")
        else:
            _draw_placeholder(draw, slot, "缺圖")

        # ── 名字框 ──
        if slot.label.enabled:
            _draw_label(canvas, draw, slot.label, layout.label_style)

        # ── 入職日框 ──
        if slot.date.enabled:
            _draw_date_box(canvas, draw, slot.date, layout.date_style,
                           layout.date_width, layout.date_height)

        # ── 頭像框 ──
        if slot.avatar.enabled:
            _draw_avatar(canvas, slot.avatar, av_path)

    # 標題
    _draw_title(draw, layout.title, title_text)

    canvas = canvas.convert("RGB")
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(png_bytes)

    return png_bytes


def _draw_placeholder(draw: ImageDraw.Draw, slot: ImageSlot, text: str) -> None:
    x0, y0 = slot.x, slot.y
    x1, y1 = x0 + slot.width, y0 + slot.height
    # 半透明黑色覆蓋層（RGBA，透明度 160/255 ≈ 63%）
    overlay = Image.new("RGBA", (slot.width, slot.height), (0, 0, 0, 160))
    draw._image.paste(overlay, (x0, y0), overlay)
    # NO INFO 白色字，根據框大小自動縮放
    font_size = max(12, min(slot.width, slot.height) // 8)
    try:
        font = ImageFont.load_default(size=font_size)
    except Exception:
        font = ImageFont.load_default()
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    draw.text((cx, cy), "NO INFO", fill=(255, 255, 255), font=font, anchor="mm")


def _draw_avatar(canvas: Image.Image, av: AvatarBox, av_path) -> None:
    """繪製玩家頭像（自由比例，cover 裁切）"""
    w = max(av.width, 1)
    h = max(av.height, 1)
    x, y = av.x, av.y

    # 背景色
    bg = _parse_color(av.bg_color)
    if bg:
        bg_layer = Image.new("RGBA", (w, h), bg)
        canvas.paste(bg_layer, (x, y), bg_layer)

    # 頭像圖片
    if av_path and Path(av_path).exists():
        try:
            img = Image.open(av_path).convert("RGBA")
            img = _fit_image_cover(img, w, h)
            canvas.paste(img, (x, y), img)
        except Exception:
            pass
    else:
        # 無頭像時畫佔位框
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([x, y, x + w - 1, y + h - 1],
                       fill=(80, 80, 80), outline=(150, 150, 150), width=1)


def _draw_label(canvas: Image.Image, draw: ImageDraw.Draw, lb: LabelBox, style: "TextStyle" = None) -> None:
    """繪製玩家名字框，style 為全局名字樣式（優先於 lb.style）"""
    x, y = lb.x, lb.y
    w, h = lb.width, lb.height

    # 背景色
    bg = _parse_color(lb.bg_color)
    if bg:
        bg_layer = Image.new("RGBA", (w, h), bg)
        canvas.paste(bg_layer, (x, y), bg_layer)

    if not lb.text:
        return

    effective_style = style if style is not None else lb.style
    font = _get_font(effective_style)
    try:
        color = ImageColor.getrgb(effective_style.color)
    except ValueError:
        color = (255, 255, 255)

    if effective_style.align == "left":
        tx, anchor = x, "lm"
    elif effective_style.align == "right":
        tx, anchor = x + w, "rm"
    else:
        tx, anchor = x + w // 2, "mm"

    ty = y + h // 2
    draw.text((tx, ty), lb.text, fill=color, font=font, anchor=anchor)


_NOTO_FONT_PATH = Path(__file__).parent.parent / "static" / "fonts" / "NotoSansCJKtc-Regular.otf"


def _draw_date_box(canvas: Image.Image, draw: ImageDraw.Draw, db: "DateBox", style: "TextStyle",
                   w: int = 260, h: int = 36) -> None:
    """繪製入職日框：[入職日底色區] 入職日  [白底區] 20xx-xx-xx
    - 「入職日」標籤：底色由 style.color 決定（自動選白/黑字）
    - 日期：白底黑字固定
    - 字型：優先使用 NotoSansCJKtc，fallback 到 style.font_path
    - w/h 為全局尺寸，由 layout.date_width/date_height 傳入
    """
    x, y = db.x, db.y
    if w <= 0 or h <= 0:
        return

    # 字型：優先 Noto，fallback style.font_path
    font_size = style.font_size
    font = None
    if _NOTO_FONT_PATH.exists():
        try:
            font = ImageFont.truetype(str(_NOTO_FONT_PATH), font_size)
        except Exception:
            font = None
    if font is None:
        font = _get_font(style)

    label_text = "入職日"
    date_text = db.date_text or ""

    # 量測文字寬度（用 getbbox）
    def text_w(t):
        bb = font.getbbox(t)
        return bb[2] - bb[0] if bb else font_size * len(t)

    padding = max(4, h // 6)
    lw = text_w(label_text) + padding * 2
    dw = w - lw

    # ── 入職日標籤區（date_style.color 作為標籤底色）──
    label_bg = _parse_color(style.color) if style.color else (30, 30, 30, 255)
    if label_bg is None:
        label_bg = (30, 30, 30, 255)
    label_layer = Image.new("RGBA", (lw, h), label_bg)
    canvas.paste(label_layer, (x, y), label_layer)

    # 自動選白/黑字（亮度判斷）
    r, g, b = label_bg[:3]
    brightness = 0.299 * r + 0.587 * g + 0.114 * b
    label_text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)
    draw.text((x + lw // 2, y + h // 2), label_text,
              fill=label_text_color, font=font, anchor="mm")

    # ── 日期區（白底黑字）──
    if dw > 0:
        date_layer = Image.new("RGBA", (dw, h), (255, 255, 255, 255))
        canvas.paste(date_layer, (x + lw, y), date_layer)
        if date_text:
            draw.text((x + lw + padding, y + h // 2), date_text,
                      fill=(0, 0, 0), font=font, anchor="lm")


def _draw_title(draw: ImageDraw.Draw, title_box, text: str) -> None:
    style = title_box.style
    font = _get_font(style)
    try:
        color = ImageColor.getrgb(style.color)
    except ValueError:
        color = (255, 255, 255)

    if style.align == "left":
        x = title_box.x
        anchor = "lm"
    elif style.align == "right":
        x = title_box.x + title_box.width
        anchor = "rm"
    else:
        x = title_box.x + title_box.width // 2
        anchor = "mm"

    y = title_box.y + title_box.height // 2
    draw.text((x, y), text, fill=color, font=font, anchor=anchor)
