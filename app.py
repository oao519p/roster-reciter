"""
RosterReciter — Flask 後端
啟動：python app.py
瀏覽器開啟：http://localhost:5000
"""
from __future__ import annotations
import io
import json
import shutil
import zipfile
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file
from PIL import Image

from core.layout import Layout
from core.roster import RosterManager
from core.image_composer import compose_slide

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
CONFIG_DIR = BASE_DIR / "config"
DEFAULT_LAYOUT_PATH = CONFIG_DIR / "default_layout.json"  # 出廠預設，只有重設版面時寫入
CURRENT_LAYOUT_PATH = CONFIG_DIR / "layout.json"           # 使用者目前版面，自動儲存寫入

for d in [UPLOAD_DIR, OUTPUT_DIR, CONFIG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # 停用靜態檔案快取

ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_DATA_EXT = {".csv", ".json"}


def _allowed_image(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_IMAGE_EXT


def _allowed_data(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_DATA_EXT


def _load_layout() -> Layout:
    """
    載入版面邏輯：
    1. layout.json 不存在 → 讀 default，同步寫入 layout.json
    2. layout.json 存在且 remember=True → 直接使用（含工作環境）
    3. layout.json 存在但 remember=False → 讀 default，同步覆蓋 layout.json
    """
    def _load_default_and_sync() -> Layout:
        if DEFAULT_LAYOUT_PATH.exists():
            layout = Layout.load(DEFAULT_LAYOUT_PATH)
        else:
            # 唯一允許寫入 default_layout.json 的時機：檔案完全不存在時初次建立
            layout = Layout.make_default(player_count=1)
            layout.save(DEFAULT_LAYOUT_PATH)
        layout.save(CURRENT_LAYOUT_PATH)   # 同步覆蓋 layout.json（不動 default）
        return layout

    if not CURRENT_LAYOUT_PATH.exists():
        return _load_default_and_sync()

    layout = Layout.load(CURRENT_LAYOUT_PATH)
    if not layout.remember:
        return _load_default_and_sync()
    return layout


def _save_layout(layout: Layout) -> None:
    layout.save(CURRENT_LAYOUT_PATH)  # 只寫入 layout.json，不動 default


def _get_background_path(layout: Layout = None):
    """優先用 layout 記錄的路徑，fallback 到固定檔名"""
    if layout and layout.background_path:
        p = Path(layout.background_path)
        if p.exists():
            return p
    p = UPLOAD_DIR / "background.png"
    return p if p.exists() else None


def _get_default_image_path(layout: Layout = None):
    if layout and layout.default_image_path:
        p = Path(layout.default_image_path)
        if p.exists():
            return p
    p = UPLOAD_DIR / "default_image.png"
    return p if p.exists() else None


def _get_player_default_paths_from_layout(layout: Layout) -> list:
    """從 layout.player_default_paths 取得路徑，不足的補 None"""
    result = []
    for i in range(layout.player_count):
        path_str = layout.player_default_paths[i] if i < len(layout.player_default_paths) else ""
        if path_str:
            p = Path(path_str)
            result.append(p if p.exists() else None)
        else:
            p = UPLOAD_DIR / f"default_{i}.png"
            result.append(p if p.exists() else None)
    return result


def _load_name_map(layout: Layout = None) -> dict:
    """優先用 layout 記錄的路徑，fallback 到固定檔名"""
    candidates = []
    if layout and layout.namemap_path:
        candidates.append(Path(layout.namemap_path))
    for ext in [".csv", ".json"]:
        candidates.append(UPLOAD_DIR / f"namemap{ext}")
    for p in candidates:
        if p.exists():
            try:
                if p.suffix.lower() == ".csv":
                    return RosterManager.load_name_map_csv(p)
                else:
                    return RosterManager.load_name_map_json(p)
            except Exception:
                pass
    return {}


# ── 上傳狀態查詢 ──────────────────────────────
@app.route("/api/uploads/status", methods=["GET"])
def uploads_status():
    """回傳各上傳資源是否存在，供前端初始化時顯示狀態"""
    player_count = int(request.args.get("player_count", 1))

    # 名稱對照表筆數
    namemap_count = 0
    for ext in [".csv", ".json"]:
        p = UPLOAD_DIR / f"namemap{ext}"
        if p.exists():
            try:
                if ext == ".csv":
                    nm = RosterManager.load_name_map_csv(p)
                else:
                    nm = RosterManager.load_name_map_json(p)
                namemap_count = len(nm)
            except Exception:
                pass
            break

    return jsonify({
        "ok": True,
        "background":      (UPLOAD_DIR / "background.png").exists(),
        "default_image":   (UPLOAD_DIR / "default_image.png").exists(),
        "namemap_count":   namemap_count,
        "player_defaults": [(UPLOAD_DIR / f"default_{i}.png").exists() for i in range(player_count)],
        "avatars":         [(UPLOAD_DIR / f"avatar_{i}.png").exists() for i in range(player_count)],
    })


# ── 頁面 ──────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    return "", 204


@app.route("/api/browse/folder", methods=["GET"])
def browse_folder():
    """開啟原生資料夾選擇對話框，回傳選取的完整路徑"""
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", True)
    folder = filedialog.askdirectory(title="選擇資料夾")
    root.destroy()
    if folder:
        return jsonify({"ok": True, "path": folder.replace("\\", "/")})
    return jsonify({"ok": False, "path": ""})


def _read_font_name(path: str) -> tuple[str, str]:
    """
    解析 TTF/TTC name table，優先讀取中文 Preferred Family Name。
    回傳 (display_name, english_family)。
    - nameID 16 = Preferred Family（通常是完整中文名）
    - nameID  1 = Family（英文或短名）
    - platformID 3 = Windows；langID 0x0404=繁中, 0x0804=簡中, 0x0409=英文
    """
    import struct

    def _read_names(data: bytes) -> dict:
        """回傳 {(nameID, langID): str}"""
        result = {}
        if len(data) < 6:
            return result
        fmt, count, offset = struct.unpack_from(">HHH", data, 0)
        for i in range(count):
            base = 6 + i * 12
            if base + 12 > len(data):
                break
            platform_id, enc_id, lang_id, name_id, length, str_offset = \
                struct.unpack_from(">HHHHHH", data, base)
            if platform_id != 3:   # 只讀 Windows platform
                continue
            abs_offset = offset + str_offset
            if abs_offset + length > len(data):
                continue
            raw = data[abs_offset: abs_offset + length]
            try:
                text = raw.decode("utf-16-be")
                result[(name_id, lang_id)] = text
            except Exception:
                pass
        return result

    try:
        with open(path, "rb") as fh:
            sig = fh.read(4)
            fh.seek(0)

            # TTC 容器：取第一個字型的 offset
            if sig == b"ttcf":
                fh.seek(8)
                num_fonts = struct.unpack(">I", fh.read(4))[0]
                if num_fonts == 0:
                    raise ValueError("empty ttc")
                font_offset = struct.unpack(">I", fh.read(4))[0]
                fh.seek(font_offset)

            # 讀 Offset Table → 找 name table
            fh.read(4)   # sfVersion
            num_tables = struct.unpack(">H", fh.read(2))[0]
            fh.read(6)   # searchRange, entrySelector, rangeShift
            name_offset = None
            for _ in range(num_tables):
                tag = fh.read(4)
                fh.read(4)   # checksum
                tbl_offset = struct.unpack(">I", fh.read(4))[0]
                fh.read(4)   # length
                if tag == b"name":
                    name_offset = tbl_offset
                    break
            if name_offset is None:
                raise ValueError("no name table")

            fh.seek(name_offset)
            name_data = fh.read(65536)

        names = _read_names(name_data)

        # 優先順序：繁中 Preferred > 簡中 Preferred > 英文 Preferred > 繁中 Family > 英文 Family
        priority = [
            (16, 0x0404), (16, 0x0804), (16, 0x0409),
            (1,  0x0404), (1,  0x0804), (1,  0x0409),
        ]
        display = ""
        for name_id, lang_id in priority:
            if (name_id, lang_id) in names:
                display = names[(name_id, lang_id)]
                break

        # Style（nameID=2 或 nameID=17 Preferred Subfamily）
        style_priority = [
            (17, 0x0404), (17, 0x0804), (17, 0x0409),
            (2,  0x0404), (2,  0x0804), (2,  0x0409),
        ]
        style_str = ""
        for name_id, lang_id in style_priority:
            if (name_id, lang_id) in names:
                style_str = names[(name_id, lang_id)]
                break
        # 只在非 Regular 時附加 style
        if style_str and style_str.lower() not in ("regular", "標準"):
            display = f"{display or ''} {style_str}".strip() if display else style_str

        # English family（用於 is_chinese 判斷）
        eng_family = names.get((1, 0x0409), names.get((16, 0x0409), ""))
        return display or eng_family, eng_family

    except Exception:
        return "", ""


@app.route("/api/fonts", methods=["GET"])
def list_fonts():
    """掃描系統字型資料夾，回傳 TTF/TTC 清單（含中文顯示名稱）"""
    import os
    font_dirs = [
        r"C:\Windows\Fonts",
        os.path.expanduser("~\\AppData\\Local\\Microsoft\\Windows\\Fonts"),
    ]
    fonts = []
    seen = set()
    for d in font_dirs:
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.lower().endswith((".ttf", ".ttc", ".otf")):
                full = os.path.join(d, f).replace("\\", "/")
                file_stem = os.path.splitext(f)[0]
                if file_stem in seen:
                    continue
                seen.add(file_stem)

                display_name, eng_family = _read_font_name(full)
                if not display_name:
                    display_name = file_stem   # 完全讀不到時 fallback 到檔名

                fonts.append({
                    "name": display_name,
                    "path": full,
                    "_eng": eng_family.lower(),   # 僅供後端判斷，前端不顯示
                })

    # 標記中文字型：只比對英文 family name 和路徑中的明確關鍵字，避免誤判
    chinese_keywords = [
        "jheng", "jhenghei", "mingliu", "mingliub", "dfkai", "simsun", "simhei",
        "noto sans cjk", "noto serif cjk", "yahei", "heiti", "kaiu",
        "微軟", "新細明", "標楷", "黑體", "宋體", "正黑", "細明",
    ]
    for f in fonts:
        combined = (f["_eng"] + f["path"]).lower()
        f["is_chinese"] = any(kw in combined for kw in chinese_keywords)
        del f["_eng"]   # 不回傳給前端

    return jsonify({"ok": True, "fonts": fonts})


# ── 版面配置 ──────────────────────────────────
@app.route("/api/layout", methods=["GET"])
def get_layout():
    return jsonify(_load_layout().to_dict())


@app.route("/api/layout", methods=["POST"])
def save_layout():
    data = request.get_json(force=True)
    try:
        layout = Layout.from_dict(data)
        _save_layout(layout)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/layout/default", methods=["POST"])
def reset_layout():
    player_count = int((request.json or {}).get("player_count", 1))
    player_count = max(1, min(20, player_count))

    # 步驟 1：從 default_layout.json 讀取原廠 canvas / title 樣式
    #         不存在時用程式碼預設並初次建立
    if DEFAULT_LAYOUT_PATH.exists():
        base = Layout.load(DEFAULT_LAYOUT_PATH)
    else:
        base = Layout.make_default(player_count=player_count)
        base.save(DEFAULT_LAYOUT_PATH)

    # 步驟 2：用前端傳入的 player_count 重新產生 image_slots，
    #         但套用 default 的 canvas / title 樣式
    new_layout = Layout.make_default(player_count=player_count)
    new_layout.canvas = base.canvas
    new_layout.title  = base.title

    # 步驟 3：保留目前的工作環境欄位，不被 default 覆蓋
    if CURRENT_LAYOUT_PATH.exists():
        try:
            current = Layout.load(CURRENT_LAYOUT_PATH)
            new_layout.remember       = current.remember
            new_layout.base_dir       = current.base_dir
            new_layout.player_folders = current.player_folders
            new_layout.player_count   = player_count
        except Exception:
            pass

    new_layout.save(CURRENT_LAYOUT_PATH)   # 只寫 layout.json，不動 default
    return jsonify(new_layout.to_dict())



def _get_avatar_paths(player_count: int) -> list:
    """取得所有玩家頭像路徑，無頭像回傳 None"""
    paths = []
    for i in range(player_count):
        p = UPLOAD_DIR / f"avatar_{i}.png"
        paths.append(p if p.exists() else None)
    return paths


# ── 上傳 ──────────────────────────────────────
@app.route("/api/upload/avatar/<int:player_index>", methods=["POST"])
def upload_avatar(player_index: int):
    """上傳指定玩家的頭像（0-based index）"""
    if player_index < 0 or player_index >= 20:
        return jsonify({"ok": False, "error": "玩家索引超出範圍"}), 400
    f = request.files.get("file")
    if not f or not _allowed_image(f.filename):
        return jsonify({"ok": False, "error": "不支援的檔案格式"}), 400
    save_path = UPLOAD_DIR / f"avatar_{player_index}.png"
    img = Image.open(io.BytesIO(f.read())).convert("RGBA")
    img.save(save_path, format="PNG")
    return jsonify({"ok": True, "url": f"/static/uploads/avatar_{player_index}.png"})


@app.route("/api/upload/background/clear", methods=["POST"])
def clear_background():
    p = UPLOAD_DIR / "background.png"
    if p.exists():
        p.unlink()
    # 清除 layout 記錄
    layout = _load_layout()
    layout.background_path = ""
    _save_layout(layout)
    return jsonify({"ok": True})


@app.route("/api/upload/background", methods=["POST"])
def upload_background():
    f = request.files.get("file")
    if not f or not _allowed_image(f.filename):
        return jsonify({"ok": False, "error": "不支援的檔案格式"}), 400
    save_path = UPLOAD_DIR / "background.png"
    img = Image.open(io.BytesIO(f.read())).convert("RGB")
    img.save(save_path, format="PNG")
    # 寫入 layout
    layout = _load_layout()
    layout.background_path = str(save_path).replace("\\", "/")
    _save_layout(layout)
    return jsonify({"ok": True, "url": "/static/uploads/background.png"})


@app.route("/api/upload/default_image", methods=["POST"])
def upload_default_image():
    f = request.files.get("file")
    if not f or not _allowed_image(f.filename):
        return jsonify({"ok": False, "error": "不支援的檔案格式"}), 400
    save_path = UPLOAD_DIR / "default_image.png"
    img = Image.open(io.BytesIO(f.read())).convert("RGBA")
    img.save(save_path, format="PNG")
    # 寫入 layout
    layout = _load_layout()
    layout.default_image_path = str(save_path).replace("\\", "/")
    _save_layout(layout)
    return jsonify({"ok": True})


@app.route("/api/upload/default_image/<int:player_index>", methods=["POST"])
def upload_player_default_image(player_index: int):
    """上傳指定玩家的缺圖預設圖片（0-based）"""
    if player_index < 0 or player_index >= 20:
        return jsonify({"ok": False, "error": "玩家索引超出範圍"}), 400
    f = request.files.get("file")
    if not f or not _allowed_image(f.filename):
        return jsonify({"ok": False, "error": "不支援的檔案格式"}), 400
    save_path = UPLOAD_DIR / f"default_{player_index}.png"
    img = Image.open(io.BytesIO(f.read())).convert("RGBA")
    img.save(save_path, format="PNG")
    # 寫入 layout（確保 list 夠長）
    layout = _load_layout()
    while len(layout.player_default_paths) <= player_index:
        layout.player_default_paths.append("")
    layout.player_default_paths[player_index] = str(save_path).replace("\\", "/")
    _save_layout(layout)
    return jsonify({"ok": True})


@app.route("/api/upload/namemap", methods=["POST"])
def upload_namemap():
    f = request.files.get("file")
    if not f or not _allowed_data(f.filename):
        return jsonify({"ok": False, "error": "請上傳 CSV 或 JSON 檔案"}), 400
    ext = Path(f.filename).suffix.lower()
    save_path = UPLOAD_DIR / f"namemap{ext}"
    f.save(save_path)
    try:
        if ext == ".csv":
            name_map = RosterManager.load_name_map_csv(save_path)
        else:
            name_map = RosterManager.load_name_map_json(save_path)
        # 寫入 layout
        layout = _load_layout()
        layout.namemap_path = str(save_path).replace("\\", "/")
        _save_layout(layout)
        return jsonify({"ok": True, "count": len(name_map)})
    except Exception as e:
        save_path.unlink(missing_ok=True)
        return jsonify({"ok": False, "error": f"格式錯誤：{e}"}), 400


# ── 掃描角色 ──────────────────────────────────
@app.route("/api/scan", methods=["POST"])
def scan_characters():
    data = request.get_json(force=True)
    base_dir = data.get("base_dir", "")
    player_folders = data.get("player_folders", [])

    if not base_dir or not player_folders:
        return jsonify({"ok": False, "error": "請填寫 base_dir 與 player_folders"}), 400

    name_map = _load_name_map()
    try:
        manager = RosterManager(base_dir=base_dir, player_folders=player_folders, name_map=name_map)
        characters = manager.scan_characters()
        return jsonify({
            "ok": True,
            "characters": [{"file_stem": c.file_stem, "display_name": c.display_name} for c in characters]
        })
    except FileNotFoundError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── 預覽 ──────────────────────────────────────
@app.route("/api/preview", methods=["POST"])
def preview_slide():
    data = request.get_json(force=True)
    base_dir = data.get("base_dir", "")
    player_folders = data.get("player_folders", [])
    file_stem = data.get("file_stem", "")
    display_name = data.get("display_name", file_stem)

    layout = _load_layout()
    manager = RosterManager(
        base_dir=base_dir,
        player_folders=player_folders,
        name_map=_load_name_map(layout),
        default_image=_get_default_image_path(layout),
        player_default_images=_get_player_default_paths_from_layout(layout),
    )
    image_paths = [manager.get_image_path(i, file_stem) for i in range(len(player_folders))]
    avatar_paths = _get_avatar_paths(len(player_folders))

    try:
        png_bytes = compose_slide(
            layout=layout,
            title_text=display_name,
            image_paths=image_paths,
            avatar_paths=avatar_paths,
            background_image=_get_background_path(layout),
        )
        resp = send_file(io.BytesIO(png_bytes), mimetype="image/png")
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        return resp
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── 批量生成 ──────────────────────────────────
@app.route("/api/generate", methods=["POST"])
def generate_all():
    data = request.get_json(force=True)
    base_dir = data.get("base_dir", "")
    player_folders = data.get("player_folders", [])
    characters = data.get("characters", [])

    if not base_dir or not player_folders or not characters:
        return jsonify({"ok": False, "error": "缺少必要參數"}), 400

    layout = _load_layout()
    manager = RosterManager(
        base_dir=base_dir,
        player_folders=player_folders,
        name_map=_load_name_map(layout),
        default_image=_get_default_image_path(layout),
        player_default_images=_get_player_default_paths_from_layout(layout),
    )
    bg_path = _get_background_path(layout)
    avatar_paths = _get_avatar_paths(len(player_folders))

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    for char in characters:
        file_stem = char.get("file_stem", "")
        display_name = char.get("display_name", file_stem)
        image_paths = [manager.get_image_path(i, file_stem) for i in range(len(player_folders))]
        out_path = OUTPUT_DIR / f"{file_stem}.png"
        try:
            compose_slide(
                layout=layout,
                title_text=display_name,
                image_paths=image_paths,
                avatar_paths=avatar_paths,
                background_image=bg_path,
                output_path=out_path,
            )
        except Exception:
            pass

    zip_path = BASE_DIR / "output.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for png in OUTPUT_DIR.glob("*.png"):
            zf.write(png, png.name)

    return send_file(zip_path, mimetype="application/zip", as_attachment=True, download_name="roster_slides.zip")


# session.json 已廢棄，工作環境改存於 layout.json（remember 欄位控制）
# 保留空路由以防舊前端呼叫，回傳空值不報錯
@app.route("/api/session", methods=["GET"])
def get_session():
    return jsonify({"ok": True, "session": None})


@app.route("/api/session", methods=["POST"])
def save_session():
    return jsonify({"ok": True})


@app.route("/api/session/clear", methods=["POST"])
def clear_session():
    return jsonify({"ok": True})


if __name__ == "__main__":
    print("=" * 50)
    print("  RosterReciter 啟動中...")
    print("  瀏覽器開啟：http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, host="127.0.0.1", port=5000)
