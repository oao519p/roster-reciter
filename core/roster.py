"""
角色與玩家資料管理。
支援 CSV / JSON 對照表，以及從資料夾自動掃描。
"""
from __future__ import annotations
import csv
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
        player_default_images: list = None,  # 每位玩家的個別預設圖，優先於 default_image
    ):
        self.base_dir = Path(base_dir)
        self.player_folders = player_folders
        self.name_map = name_map or {}
        self.default_image = Path(default_image) if default_image else None
        self.player_default_images = player_default_images or []

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
                display = self.name_map.get(stem, stem)
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
    def load_name_map_csv(csv_path) -> dict:
        result = {}
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                result[row["file_stem"].strip()] = row["display_name"].strip()
        return result

    @staticmethod
    def load_name_map_json(json_path) -> dict:
        return json.loads(Path(json_path).read_text(encoding="utf-8"))
