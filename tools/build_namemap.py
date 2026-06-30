"""
build_namemap.py
從兩份 operator_data JSON 產生 RosterReciter 用的多語言角色名稱對照表

輸出：
  config/namemap.json  — {charId: {tw, cn, en, jp}}
  供 RosterReciter 上傳使用（HR Dossier 模式）

用法：
  python tools/build_namemap.py
"""
from __future__ import annotations
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# ── 設定：各伺服器 operator_data JSON 路徑 ──────
TW_JSON = BASE_DIR / "operator_data_36548697.json"   # 繁中服（tw）
CN_JSON = BASE_DIR / "operator_data_33842330.json"   # 簡中服（cn）
# JP_JSON = BASE_DIR / "operator_data_xxxxxxxx.json" # 日服（jp）— 有資料時取消註解

OUT_JSON = BASE_DIR / "config" / "namemap.json"


def load_char_info(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("charInfoMap", {})


def build() -> None:
    tw_map = load_char_info(TW_JSON) if TW_JSON.exists() else {}
    cn_map = load_char_info(CN_JSON) if CN_JSON.exists() else {}
    # jp_map = load_char_info(JP_JSON) if JP_JSON.exists() else {}

    all_keys = sorted(set(tw_map) | set(cn_map))

    namemap = {}
    for key in all_keys:
        tw_entry = tw_map.get(key, {})
        cn_entry = cn_map.get(key, {})
        # jp_entry = jp_map.get(key, {})

        entry: dict[str, str] = {}
        if tw_entry.get("name"):
            entry["tw"] = tw_entry["name"]
        if cn_entry.get("name"):
            entry["cn"] = cn_entry["name"]
        # 英文名：兩份資料的 appellation 通常相同，取任一非空值
        en = tw_entry.get("appellation") or cn_entry.get("appellation", "")
        if en:
            entry["en"] = en
        # if jp_entry.get("name"):
        #     entry["jp"] = jp_entry["name"]

        if entry:
            namemap[key] = entry

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(namemap, f, ensure_ascii=False, indent=2)
    print(f"JSON → {OUT_JSON}  ({len(namemap)} 筆)")


if __name__ == "__main__":
    build()

