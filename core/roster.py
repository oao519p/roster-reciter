"""
角色與玩家資料管理。
支援 JSON 對照表（多語言格式），以及從資料夾自動掃描。

namemap JSON 格式：
  {
    "char_002_amiya": {"tw": "阿米婭", "cn": "阿米娅", "en": "Amiya"},
    ...
  }

比對模式：
  normal     — file_stem 直接對應 namemap key（使用者自訂檔名）
  hr_dossier — file_stem 格式為 "N_角色名"，從 namemap value 的各語言名稱做 substring 比對
"""
from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Character:
    file_stem: str
    display_name: str


class RosterManager:
    SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

    def __init__(
        self,
        base_dir,
        player_folders: list,
        name_map: dict = None,
        default_image=None,
        player_default_images: list = None,
        namemap_mode: str = "normal",   # "normal" | "hr_dossier"
        namemap_lang: str = "tw",       # "tw" | "cn" | "en" | "jp"
    ):
        self.base_dir = Path(base_dir)
        self.player_folders = player_folders
        self.name_map = name_map or {}
        self.default_image = Path(default_image) if default_image else None
        self.player_default_images = player_default_images or []
        self.namemap_mode = namemap_mode
        self.namemap_lang = namemap_lang

        # hr_dossier 模式：預先建立 {語言名稱 -> display_name} 的反查表，加速比對
        self._hr_lookup: dict[str, str] = {}
        if namemap_mode == "hr_dossier":
            self._build_hr_lookup()

    def _build_hr_lookup(self) -> None:
        """建立所有語言名稱 → display_name 的反查表（用於 substring 比對）"""
        lang = self.namemap_lang
        for entry in self.name_map.values():
            if not isinstance(entry, dict):
                continue
            display = entry.get(lang) or next(
                (entry[k] for k in ("tw", "cn", "en", "jp") if entry.get(k)), ""
            )
            if not display:
                continue
            # 每個語言的名稱都加入 lookup，這樣不管圖片是哪個伺服器都能命中
            for name in entry.values():
                if name:
                    self._hr_lookup[name] = display

    def _resolve_display(self, stem: str) -> str:
        """根據 mode 解析 file_stem 對應的 display_name"""
        if self.namemap_mode == "hr_dossier":
            # HR Dossier 格式：序號_角色名，取 _ 後面的部分做精確比對
            char_part = stem.split("_", 1)[1] if "_" in stem else stem
            # 先嘗試精確比對（避免短名稱誤命中長名稱）
            if char_part in self._hr_lookup:
                return self._hr_lookup[char_part]
            # fallback：substring 比對（應對名稱有空格或特殊字元的情況）
            for name, display in self._hr_lookup.items():
                if name in char_part or char_part in name:
                    return display
            return stem  # 找不到就用原始 stem
        else:
            # normal 模式：直接 key 比對，支援舊格式（str value）和新格式（dict value）
            entry = self.name_map.get(stem)
            if entry is None:
                return stem
            if isinstance(entry, dict):
                lang = self.namemap_lang
                return entry.get(lang) or next(
                    (entry[k] for k in ("tw", "cn", "en", "jp") if entry.get(k)), stem
                )
            return str(entry)

    def scan_characters(self) -> list:
        if not self.player_folders:
            return []

        ref_folder = self.base_dir / self.player_folders[0]
        if not ref_folder.exists():
            raise FileNotFoundError(f"參考資料夾不存在：{ref_folder}")

        characters = []
        for f in sorted(ref_folder.iterdir()):
            if f.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                stem = f.stem
                display = self._resolve_display(stem)
                characters.append(Character(file_stem=stem, display_name=display))

        return characters

    def get_image_path(self, player_index: int, file_stem: str):
        folder = self.base_dir / self.player_folders[player_index]
        for ext in self.SUPPORTED_EXTENSIONS:
            candidate = folder / f"{file_stem}{ext}"
            if candidate.exists():
                return candidate
        # fallback: 個別玩家預設 → 全局預設
        if player_index < len(self.player_default_images) and self.player_default_images[player_index]:
            return self.player_default_images[player_index]
        return self.default_image

    @staticmethod
    def load_name_map_json(json_path) -> dict:
        return json.loads(Path(json_path).read_text(encoding="utf-8"))
