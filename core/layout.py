"""
版面配置資料結構。
所有座標與尺寸單位為「像素」，對應最終輸出 PNG 的解析度。
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
import json
from pathlib import Path


@dataclass
class TextStyle:
    font_path: str = ""
    font_size: int = 60
    color: str = "#FFFFFF"
    bold: bool = False
    align: str = "center"  # left / center / right


@dataclass
class TitleBox:
    x: int = 50
    y: int = 30
    width: int = 1820
    height: int = 120
    style: TextStyle = field(default_factory=TextStyle)


@dataclass
class AvatarBox:
    """玩家頭像框（正方形，相對於畫布絕對座標）"""
    enabled: bool = False
    x: int = 0
    y: int = 0
    size: int = 60          # 寬高相同
    bg_color: str = ""      # 空字串 = 透明


@dataclass
class LabelBox:
    """玩家名字框（相對於畫布絕對座標）"""
    enabled: bool = False
    x: int = 0
    y: int = 0
    width: int = 200
    height: int = 40
    text: str = ""          # 玩家名字
    bg_color: str = ""      # 空字串 = 透明
    style: TextStyle = field(default_factory=lambda: TextStyle(font_size=24, color="#FFFFFF", align="center"))


@dataclass
class ImageSlot:
    player_index: int = 0
    x: int = 0
    y: int = 0
    width: int = 200
    height: int = 400
    avatar: AvatarBox = field(default_factory=AvatarBox)
    label: LabelBox = field(default_factory=LabelBox)


@dataclass
class CanvasConfig:
    width: int = 1920
    height: int = 1080
    background_color: str = "#1a1a2e"


@dataclass
class Layout:
    canvas: CanvasConfig = field(default_factory=CanvasConfig)
    title: TitleBox = field(default_factory=TitleBox)
    image_slots: list = field(default_factory=list)
    # ── 工作環境（合併自原 session.json）──
    remember: bool = True          # True → 下次開啟還原此版面與環境；False → 下次讀 default
    base_dir: str = ""
    player_folders: list = field(default_factory=list)
    player_count: int = 1
    # ── 資源路徑 ──
    background_path: str = ""      # 背景圖（static/uploads/background.png）
    default_image_path: str = ""   # 全局缺圖預設
    player_default_paths: list = field(default_factory=list)  # 個別玩家缺圖預設
    namemap_path: str = ""         # 名稱對照表（json）
    namemap_mode: str = "normal"   # "normal" | "hr_dossier"
    namemap_lang: str = "tw"       # "tw" | "cn" | "en" | "jp"
    label_style: TextStyle = field(default_factory=lambda: TextStyle(font_size=24, color="#FFFFFF", align="center"))

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Layout":
        canvas = CanvasConfig(**data.get("canvas", {}))
        title_data = dict(data.get("title", {}))
        style_data = title_data.pop("style", {})
        title = TitleBox(**title_data, style=TextStyle(**style_data))

        slots = []
        for s in data.get("image_slots", []):
            s = dict(s)
            av_data = s.pop("avatar", {})
            avatar = AvatarBox(**av_data) if av_data else AvatarBox()
            lb_data = s.pop("label", {})
            if lb_data:
                lb_style = lb_data.pop("style", {})
                label = LabelBox(**lb_data, style=TextStyle(**lb_style))
            else:
                label = LabelBox()
            slots.append(ImageSlot(**s, avatar=avatar, label=label))

        return cls(
            canvas=canvas,
            title=title,
            image_slots=slots,
            remember=data.get("remember", True),
            base_dir=data.get("base_dir", ""),
            player_folders=data.get("player_folders", []),
            player_count=data.get("player_count", len(slots) or 1),
            background_path=data.get("background_path", ""),
            default_image_path=data.get("default_image_path", ""),
            player_default_paths=data.get("player_default_paths", []),
            namemap_path=data.get("namemap_path", ""),
            namemap_mode=data.get("namemap_mode", "normal"),
            namemap_lang=data.get("namemap_lang", "tw"),
            label_style=TextStyle(**data["label_style"]) if data.get("label_style") else TextStyle(font_size=24, color="#FFFFFF", align="center"),
        )

    def save(self, path) -> None:
        Path(path).write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    @classmethod
    def load(cls, path) -> "Layout":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def make_default(cls, player_count: int = 1) -> "Layout":
        canvas = CanvasConfig(width=1920, height=1080)
        title = TitleBox(
            x=50, y=20, width=1820, height=100,
            style=TextStyle(font_size=72, color="#FFFFFF", align="center")
        )

        slot_w = 200
        slot_h = 400
        gap = 20
        total_w = slot_w * player_count + gap * (player_count - 1)
        start_x = (canvas.width - total_w) // 2
        slot_y = (canvas.height - slot_h) // 2 + 40

        slots = []
        for i in range(player_count):
            x = start_x + i * (slot_w + gap)
            # avatar 預設：圖片框左上角，60x60
            avatar = AvatarBox(
                enabled=False,
                x=x, y=slot_y,
                size=60, bg_color=""
            )
            # label 預設：圖片框正下方置中
            label = LabelBox(
                enabled=False,
                x=x, y=slot_y + slot_h + 8,
                width=slot_w, height=36,
                text=f"玩家{i + 1}",
                bg_color="",
                style=TextStyle(font_size=24, color="#FFFFFF", align="center")
            )
            slots.append(ImageSlot(
                player_index=i,
                x=x, y=slot_y,
                width=slot_w, height=slot_h,
                avatar=avatar, label=label
            ))

        return cls(
            canvas=canvas,
            title=title,
            image_slots=slots,
            remember=True,
            base_dir="",
            player_folders=[],
            player_count=player_count,
            background_path="",
            default_image_path="",
            player_default_paths=[],
            namemap_path="",
            namemap_mode="normal",
            namemap_lang="tw",
            label_style=TextStyle(font_size=24, color="#FFFFFF", align="center"),
        )
