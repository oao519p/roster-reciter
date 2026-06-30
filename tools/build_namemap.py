"""
build_namemap.py
從 ArknightsGameResource 的 character_table.json 更新 namemap.json

功能：
1. 檢查 GitHub commit sha，判斷是否有更新
2. 下載 character_table.json（GitHub raw）
3. 過濾 char_ 開頭的角色，排除預備/盟約幹員
4. 比對現有 namemap.json，找出新增角色
5. 詢問是否寫入
6. 對每個缺少 tw 的角色逐一詢問填寫方式（自動轉換 / 手動輸入）

用法：
  python tools/build_namemap.py

資料來源：
  https://raw.githubusercontent.com/yuanyan3060/ArknightsGameResource/refs/heads/main/gamedata/excel/character_table.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from opencc import OpenCC

BASE_DIR = Path(__file__).parent.parent
NAMEMAP_PATH = BASE_DIR / "config" / "namemap.json"
META_PATH = Path(__file__).parent / "namemap_meta.json"

REPO_OWNER = "yuanyan3060"
REPO_NAME = "ArknightsGameResource"
TABLE_FILE = "gamedata/excel/character_table.json"

TABLE_URL = (
    "https://raw.githubusercontent.com/yuanyan3060/ArknightsGameResource/"
    "refs/heads/main/gamedata/excel/character_table.json"
)
COMMIT_URL = (
    f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits"
    f"?path={TABLE_FILE}&per_page=1"
)

# 預備幹員 / 盟約活動幹員 / 特殊非正式幹員（過濾掉）
EXCLUDE_KEYS: set[str] = {
    # 預備幹員 - 近戰/術師/後勤/狙擊 (2星)
    "char_504_rguard",
    "char_505_rcast",
    "char_506_rmedic",
    "char_507_rsnipe",
    # 盟約活動幹員 (4星)
    "char_508_aguard",
    "char_509_acast",
    "char_510_amedic",
    "char_511_asnipe",
    "char_512_aprot",
    "char_513_apionr",
    # 預備幹員 - 重装 (2星)
    "char_514_rdfend",
    # 預備幹員全套 (3星)
    "char_600_cpione",
    "char_601_cguard",
    "char_602_cdfend",
    "char_603_csnipe",
    "char_604_ccast",
    "char_605_cmedic",
    "char_606_csuppo",
    "char_607_cspec",
    # 盟約活動幹員 (5星)
    "char_608_acpion",
    "char_609_acguad",
    "char_610_acfend",
    "char_611_acnipe",
    "char_612_accast",
    "char_613_acmedc",
    "char_614_acsupo",
    "char_615_acspec",
    # 盟約特殊 (3星/5星)
    "char_616_pithst",
    "char_617_sharp2",
}

cc_s2t = OpenCC("s2t")


def get_latest_commit() -> str | None:
    """取得 character_table.json 的最新 commit sha，失敗回傳 None"""
    try:
        resp = requests.get(COMMIT_URL, timeout=15)
        resp.raise_for_status()
        return resp.json()[0]["sha"]
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 403:
            print("警告: GitHub API rate limit 已達上限，跳過 commit 檢查")
            return None
        raise


def load_meta() -> dict:
    """載入 namemap_meta.json"""
    if META_PATH.exists():
        with open(META_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_meta(commit_sha: str) -> None:
    """儲存 commit sha 到 namemap_meta.json"""
    meta = {
        "source": f"{REPO_OWNER}/{REPO_NAME}",
        "file": TABLE_FILE,
        "last_commit_sha": commit_sha,
        "last_update": datetime.now(timezone.utc).isoformat(),
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def fetch_table() -> dict:
    """下載 character_table.json"""
    resp = requests.get(TABLE_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def load_namemap() -> dict:
    """載入現有 namemap.json"""
    if NAMEMAP_PATH.exists():
        with open(NAMEMAP_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_char_keys(table: dict) -> list[str]:
    """取得 char_ 開頭且不在排除清單的 key"""
    keys = []
    for k in table.keys():
        if k.startswith("char_") and k not in EXCLUDE_KEYS:
            keys.append(k)
    return sorted(keys)


def cn_to_tw(text: str) -> str:
    """簡中轉繁體（使用 opencc）"""
    return cc_s2t.convert(text)


def find_new_chars(table: dict, namemap: dict) -> list[tuple[str, dict]]:
    """找出 table 中有但 namemap 中沒有（或資料不同）的角色"""
    char_keys = get_char_keys(table)
    new_chars = []

    for key in char_keys:
        if key not in namemap:
            entry = table[key]
            name = entry.get("name", "")
            appellation = entry.get("appellation", "")
            new_chars.append((key, {
                "cn": name,
                "en": appellation,
                "tw": "",
            }))

    return new_chars


def find_missing_tw(namemap: dict) -> list[tuple[str, dict]]:
    """找出 namemap 中 tw 為空的角色"""
    missing = []
    for key, entry in sorted(namemap.items()):
        if not entry.get("tw"):
            missing.append((key, entry))
    return missing


def ask_tw_for_char(key: str, entry: dict) -> str:
    """詢問單一角色的 tw"""
    cn = entry.get("cn", "")
    en = entry.get("en", "")
    auto_tw = cn_to_tw(cn)

    print(f"  {key}")
    print(f"    cn: {cn}")
    print(f"    en: {en}")
    print(f"    [1] 自動轉換: {auto_tw}")
    print(f"    [2] 手動輸入")
    choice = input(f"    選擇 (1/2, 預設 1): ").strip()

    if choice == "2":
        tw = input(f"    請輸入 tw: ").strip()
        return tw if tw else auto_tw
    return auto_tw


def main() -> None:
    # Windows console UTF-8 支援
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    # 檢查 commit sha
    print("正在檢查 GitHub commit...")
    latest_sha = get_latest_commit()
    meta = load_meta()
    saved_sha = meta.get("last_commit_sha", "")

    if latest_sha is None:
        # API 失敗，繼續執行但不做 commit 比對
        pass
    elif saved_sha and saved_sha == latest_sha:
        last_update = meta.get("last_update", "未知時間")
        print(f"已是最新（上次更新: {last_update}）")
        force = input("要強制更新嗎? (y/n): ").strip().lower()
        if force != "y":
            print("已取消")
            return
    elif not saved_sha:
        print("首次使用，將記錄 commit sha")

    print("正在下載 character_table.json...")
    table = fetch_table()

    print("正在載入 namemap.json...")
    namemap = load_namemap()

    char_keys = get_char_keys(table)
    new_chars = find_new_chars(table, namemap)
    missing_tw = find_missing_tw(namemap)

    print(f"\ncharacter_table.json: {len(char_keys)} 個正式角色")
    print(f"namemap.json: {len(namemap)} 個角色")
    print(f"排除清單: {len(EXCLUDE_KEYS)} 個預備/盟約幹員")

    if new_chars:
        print(f"\n=== 新增角色 ({len(new_chars)} 個) ===")
        for key, entry in new_chars:
            print(f"  {key} | cn={entry['cn']} | en={entry['en']}")
    else:
        print("\n沒有新增角色")

    if missing_tw:
        print(f"\n=== 缺少 tw 的角色 ({len(missing_tw)} 個) ===")
        for key, entry in missing_tw:
            print(f"  {key} | cn={entry.get('cn', '')} | en={entry.get('en', '')}")
    else:
        print("\n所有角色都有 tw")

    # 詢問是否寫入
    if not new_chars and not missing_tw:
        print("\n沒有需要更新的內容")
        return

    print()
    apply = input("要寫入 namemap.json 嗎? (y/n): ").strip().lower()
    if apply != "y":
        print("已取消")
        return

    # 新增角色
    if new_chars:
        for key, entry in new_chars:
            namemap[key] = entry
        print(f"新增 {len(new_chars)} 個角色")

    # 處理缺少 tw 的角色
    all_missing = find_missing_tw(namemap)
    if all_missing:
        print(f"\n=== 請填寫 {len(all_missing)} 個角色的繁體中文名稱 ===\n")
        for i, (key, entry) in enumerate(all_missing, 1):
            print(f"[{i}/{len(all_missing)}]")
            tw = ask_tw_for_char(key, entry)
            namemap[key]["tw"] = tw
            print(f"  → tw = {tw}\n")

    # 寫入 namemap
    NAMEMAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NAMEMAP_PATH, "w", encoding="utf-8") as f:
        json.dump(namemap, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"已更新 {NAMEMAP_PATH} ({len(namemap)} 筆)")

    # 儲存 commit sha（如果有）
    if latest_sha:
        save_meta(latest_sha)
        print(f"已更新 {META_PATH}")


if __name__ == "__main__":
    main()
