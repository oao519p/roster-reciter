"""
圖片排序工具 - 根據 PRRTS Wiki 角色排序重新命名輸出圖片

使用方式:
    python tools/sort_output.py [output目錄] [namemap.json路徑]

預設:
    output目錄: output/
    namemap.json: config/namemap.json

流程:
1. 檢查 output/ 是否有圖片（沒有則退出）
2. 爬取 PRRTS Wiki 獲取角色排序（實裝順序，越早實裝越前面）
3. 根據 namemap.json 建立 cn → tw/cn/en/jp 對照
4. 掃描 output/ 目錄中的圖片
5. 根據排序重新命名圖片（添加 001_ 002_ 等前綴）

注意:
- output/ 資料夾是 Step 5 批量生成後產生的，包含 PNG 圖片和 ZIP 檔案
- 不在 PRRTS Wiki 中的角色名稱（如自訂角色）不會被重新命名
- 可以單獨使用，也可以從網頁 Step 5 觸發
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup


def fetch_operator_order() -> list[dict[str, str]]:
    """爬取 PRRTS Wiki 獲取角色排序（實裝倒序）
    
    使用原始 HTML 的 data-sortid 來排序
    data-sortid 數字越小代表越早實裝
    """
    resp = requests.get("https://prts.wiki/w/干员一览", timeout=30)
    resp.encoding = "utf-8"
    
    # 提取 data-zh, data-en, data-ja, data-sortid
    pattern = r'data-zh="([^"]+)"[^>]*data-en="([^"]*)"[^>]*data-ja="([^"]*)"[^>]*data-sortid="([^"]*)"'
    matches = re.findall(pattern, resp.text)
    
    operators = []
    for zh, en, ja, sortid in matches:
        operators.append({
            "cn": zh,
            "en": en,
            "ja": ja,
            "sortid": int(sortid) if sortid else 0,
        })
    
    # 根據 sortid 升序排序（最早的在前）
    operators.sort(key=lambda x: x["sortid"])
    
    # 移除 sortid 字段
    for op in operators:
        del op["sortid"]
    
    return operators


def load_namemap(namemap_path: Path) -> dict[str, dict[str, str]]:
    """載入 namemap.json"""
    with open(namemap_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_name_lookup(
    operators: list[dict[str, str]],
    namemap: dict[str, dict[str, str]]
) -> dict[str, int]:
    """
    建立名稱 → 排序的對照表

    優先使用 namemap 中的 cn 名稱對應到排序
    如果 namemap 沒有，直接使用 PRRTS 的 cn 名稱
    """
    # 建立 cn 名稱到排序的對照
    cn_to_order = {}
    for idx, op in enumerate(operators):
        cn_name = op["cn"]
        cn_to_order[cn_name] = idx

    # 建立 namemap 反向對照: cn → charId
    cn_to_charid = {}
    for char_id, names in namemap.items():
        if "cn" in names:
            cn_to_charid[names["cn"]] = char_id

    # 建立所有語言名稱到排序的對照
    name_to_order = {}

    # 先加入 namemap 中的所有名稱
    for char_id, names in namemap.items():
        cn_name = names.get("cn", "")
        if cn_name in cn_to_order:
            order = cn_to_order[cn_name]
            # 加入所有語言的名稱
            for lang in ["tw", "cn", "en", "jp"]:
                if lang in names:
                    name_to_order[names[lang]] = order

    # 對於 namemap 中沒有的角色，直接使用 PRRTS 的數據
    for op in operators:
        cn_name = op["cn"]
        if cn_name not in cn_to_charid:
            # 這個角色不在 namemap 中
            order = cn_to_order[cn_name]
            name_to_order[cn_name] = order
            if op["en"]:
                name_to_order[op["en"]] = order
            if op["ja"]:
                name_to_order[op["ja"]] = order

    return name_to_order


def scan_output_images(output_dir: Path) -> list[Path]:
    """掃描 output/ 目錄中的圖片文件"""
    image_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
    images = []

    for file_path in output_dir.iterdir():
        if file_path.suffix.lower() in image_extensions:
            images.append(file_path)

    return sorted(images)


def extract_name_from_filename(filename: str) -> str:
    """從檔名中提取角色名稱（去除擴展名）"""
    return Path(filename).stem


def sort_and_rename(
    output_dir: Path,
    name_to_order: dict[str, int],
    dry_run: bool = True
) -> list[tuple[str, str, int | None]]:
    """
    根據排序重新命名圖片

    返回: [(原檔名, 新檔名, 排序), ...]
    """
    images = scan_output_images(output_dir)
    if not images:
        print(f"在 {output_dir} 中未找到圖片文件")
        return []

    print(f"找到 {len(images)} 張圖片")

    # 建立圖片名稱到路徑的對照
    name_to_path = {}
    for img_path in images:
        name = extract_name_from_filename(img_path.name)
        name_to_path[name] = img_path

    # 匹配圖片到排序
    matched = []
    unmatched = []

    for name, img_path in name_to_path.items():
        if name in name_to_order:
            order = name_to_order[name]
            # 生成新檔名
            new_name = f"{order + 1:03d}_{name}{img_path.suffix}"
            matched.append((img_path.name, new_name, order))
        else:
            unmatched.append(name)

    # 按排序排序
    matched.sort(key=lambda x: x[2] if x[2] is not None else 999999)

    print(f"\n匹配成功: {len(matched)} 張")
    print(f"未匹配: {len(unmatched)} 張")

    if unmatched:
        print(f"\n未匹配的角色名稱:")
        for name in unmatched[:10]:
            print(f"  - {name}")
        if len(unmatched) > 10:
            print(f"  ... 還有 {len(unmatched) - 10} 個")

    if dry_run:
        print("\n=== 預覽模式 (不會實際重命名) ===")
        print("\n重命名列表 (按排序順序):")
        for old, new, order in matched:
            print(f"  {new}")
    else:
        print("\n=== 實際重命名 ===")
        for old, new, order in matched:
            old_path = output_dir / old
            new_path = output_dir / new
            if old_path.exists():
                old_path.rename(new_path)
                print(f"  ✓ {old} → {new}")
            else:
                print(f"  ✗ {old} 不存在")

    return matched


def main():
    parser = argparse.ArgumentParser(description="根據 PRRTS Wiki 角色排序重新命名輸出圖片")
    parser.add_argument(
        "output_dir",
        nargs="?",
        default="output",
        help="輸出圖片目錄 (預設: output/)"
    )
    parser.add_argument(
        "--namemap",
        default="config/namemap.json",
        help="namemap.json 路徑 (預設: config/namemap.json)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="預覽模式 (預設為預覽模式，使用 --execute 實際執行)"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="實際執行重命名"
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    namemap_path = Path(args.namemap)
    dry_run = not args.execute

    if not output_dir.exists():
        print(f"錯誤: {output_dir} 不存在")
        print("請先在網頁 Step 5 進行批量生成", flush=True)
        sys.exit(1)

    if not namemap_path.exists():
        print(f"錯誤: {namemap_path} 不存在")
        sys.exit(1)

    # 先檢查 output/ 是否有圖片
    image_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
    images = [f for f in output_dir.iterdir() if f.suffix.lower() in image_extensions]
    
    if not images:
        print(f"在 {output_dir} 中未找到圖片文件")
        print("請先在網頁 Step 5 進行批量生成", flush=True)
        sys.exit(1)
    
    print(f"找到 {len(images)} 張圖片，開始爬取排序數據...", flush=True)
    print("正在爬取 PRRTS Wiki 角色排序...", flush=True)
    operators = fetch_operator_order()
    print(f"獲取到 {len(operators)} 個角色", flush=True)

    print("正在載入 namemap.json...", flush=True)
    namemap = load_namemap(namemap_path)
    print(f"namemap 包含 {len(namemap)} 個角色", flush=True)

    print("正在建立名稱對照表...", flush=True)
    name_to_order = build_name_lookup(operators, namemap)
    print(f"名稱對照表包含 {len(name_to_order)} 個條目", flush=True)

    print("\n正在排序圖片...", flush=True)
    results = sort_and_rename(output_dir, name_to_order, dry_run)

    if results:
        print(f"\n完成! 共處理 {len(results)} 張圖片", flush=True)
    else:
        print("\n沒有圖片需要處理", flush=True)


if __name__ == "__main__":
    main()
