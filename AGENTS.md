# RosterReciter — Agent Instructions

## 專案概述

**RosterReciter（報菜名投影片生成器）**
將多位玩家的角色圖片合成為單張 1920×1080 PNG，供影片剪輯使用。

- **語言 / 框架：** Python 3.10 · Flask 3.0.3 · Pillow 10.4.0
- **前端：** 純 HTML + Vanilla JS（無 build step）
- **執行方式：** 本機 Flask dev server，瀏覽器操作

---

## 環境設定

### 建立 / 重建 venv

```bash
# 刪除舊 venv（若存在）
rmdir /s /q venv

# 用 py launcher 建立新 venv（Python 3.10）
py -3.10 -m venv venv

# 啟動 venv
venv\Scripts\activate

# 安裝相依套件
pip install -r requirements.txt
```

### 啟動開發伺服器

```bash
venv\Scripts\activate
python app.py
```

瀏覽器開啟：**http://localhost:5000**

> Flask 以 `debug=True` 啟動，修改 Python 檔案後自動重載。
> 前端 JS/CSS 修改需手動重新整理瀏覽器（靜態檔案快取已停用）。

---

## 目錄結構

```
roster-reciter/
├── app.py                    # Flask 主程式，所有 API 路由
├── requirements.txt          # Flask + Pillow（僅 2 個相依）
├── config/
│   ├── default_layout.json   # 出廠預設版面（重設時讀取，進版控）
│   └── layout.json           # 使用者目前版面（自動儲存，gitignore）
├── core/
│   ├── image_composer.py     # Pillow 圖片合成核心
│   ├── layout.py             # 版面 dataclass（Layout / ImageSlot / TitleBox…）
│   └── roster.py             # 角色掃描 / 名稱對照表
├── static/
│   ├── css/main.css
│   ├── js/
│   │   ├── main.js           # 主要 UI 邏輯
│   │   ├── layout-editor.js  # 版面拖拉編輯器
│   │   └── preview.js        # 預覽面板
│   └── uploads/              # 上傳暫存（自動產生，gitignore）
├── templates/
│   └── index.html            # 單頁應用主模板
└── output/                   # 輸出 PNG（自動產生，gitignore）
```

---

## API 端點速覽

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/` | 主頁面 |
| GET | `/api/layout` | 取得目前版面設定 |
| POST | `/api/layout` | 儲存版面設定 |
| POST | `/api/layout/default` | 重設為預設版面 |
| POST | `/api/scan` | 掃描角色圖片清單 |
| POST | `/api/preview` | 預覽單張投影片（回傳 PNG） |
| POST | `/api/generate` | 批量生成並下載 ZIP |
| POST | `/api/upload/background` | 上傳背景圖 |
| POST | `/api/upload/background/clear` | 清除背景圖 |
| POST | `/api/upload/default_image` | 上傳全局缺圖預設 |
| POST | `/api/upload/default_image/<n>` | 上傳玩家 n 的缺圖預設 |
| POST | `/api/upload/avatar/<n>` | 上傳玩家 n 的頭像 |
| POST | `/api/upload/namemap` | 上傳角色名稱對照表（CSV/JSON） |
| GET | `/api/uploads/status` | 查詢各上傳資源是否存在 |
| GET | `/api/fonts` | 列出系統字型（TTF/TTC/OTF） |
| GET | `/api/browse/folder` | 開啟原生資料夾選擇對話框 |
| GET/POST | `/api/session` | 已廢棄（stub，回傳空值） |
| POST | `/api/session/clear` | 已廢棄（stub） |

---

## 核心模組說明

### `core/layout.py`
版面資料結構，全部使用 Python `dataclass`：
- `Layout` → `CanvasConfig` + `TitleBox` + `list[ImageSlot]` + 工作環境欄位
- 工作環境欄位：`remember`（bool）、`base_dir`、`player_folders`、`player_count`
- `ImageSlot` → 每位玩家的圖片框位置，含 `AvatarBox`（頭像）和 `LabelBox`（名字）
- `Layout.save()` / `Layout.load()` 讀寫 JSON
- `Layout.make_default(player_count)` 產生預設版面

### `core/roster.py`
- `RosterManager.scan_characters()` — 掃描第一位玩家資料夾，取得角色清單
- `RosterManager.get_image_path(player_index, file_stem)` — 取得圖片路徑，含 fallback 邏輯
- 支援 CSV（`file_stem,display_name`）和 JSON（`{"stem": "名稱"}`）名稱對照表

### `core/image_composer.py`
- `compose_slide(layout, title_text, image_paths, ...)` — 主合成函式，回傳 PNG bytes
- 圖片以 **cover** 模式裁切填滿框格
- 字型快取於 `_font_cache`，避免重複載入
- 中文標題需指定 TTF/TTC 字型路徑（預設：`C:/Windows/Fonts/msjh.ttc`）

---

## 前端模組說明

### `static/js/main.js`
主控制器，管理全域 `state`（baseDir、playerFolders、characters、selectedCharIndex、layout）。
- `init()` → 載入版面、還原工作環境、綁定事件
- `scanCharacters()` → 呼叫 `/api/scan`，掃描完成後自動預覽第一個角色
- `immediateSaveLayout()` → 預覽前呼叫，確保後端用最新設定
- `syncEnvToLayout()` → 將 baseDir / playerFolders / remember 注入 `state.layout` 再儲存

### `static/js/preview.js`
- `requestPreview()` → 以目前選取角色呼叫 `/api/preview`，更新右側預覽圖
- `requestBlankPreview()` → 無角色時預覽空版面（背景 + 框格位置）

### `static/js/layout-editor.js`
- `renderSlotInputs()` → 渲染每個玩家的圖片框 / 頭像 / 名字設定區塊，結束後呼叫 `_refreshAvatarThumbs()`
- `renderDragBoxes()` → 在預覽圖上疊加可拖拉的方塊
- `_refreshAvatarThumbs()` → 查詢 `/api/uploads/status`，只對 `avatar.enabled=true` 的 slot 填入縮圖 src（避免 404）
- `collectSlotInputs()` → 將表單值收集回 `state.layout.image_slots`

---

## 程式碼慣例

- **Python 版本：** 3.10，使用 `from __future__ import annotations`
- **型別標注：** 函式簽名加型別，dataclass 欄位有預設值
- **路徑處理：** 一律使用 `pathlib.Path`，不用字串拼接
- **錯誤回應：** API 一律回傳 `{"ok": false, "error": "..."}` + 適當 HTTP 狀態碼
- **前端 API 呼叫：** 使用 `fetch`，回應格式統一為 `{"ok": true/false, ...}`
- **無測試框架：** 目前無自動化測試，手動用瀏覽器驗證

---

## 常見問題 / 陷阱

1. **venv 執行檔缺失**：`venv/Scripts/python.exe` 不存在時，需重建 venv（見上方環境設定）。
2. **中文標題亂碼**：版面設定中 `font_path` 必須指向支援中文的 TTF/TTC，例如 `C:/Windows/Fonts/msjh.ttc`。
3. **背景圖快取**：Flask 已設定 `SEND_FILE_MAX_AGE_DEFAULT = 0`，但瀏覽器仍可能快取，預覽時加 `?t=timestamp` 參數。
4. **上傳大小限制**：`MAX_CONTENT_LENGTH = 50MB`，超大圖片需先壓縮。
5. **`/api/browse/folder`**：使用 `tkinter` 開啟原生對話框，需在有 GUI 的環境執行（不支援 headless server）。
6. **`output/` 每次批量生成前會被清空**（`shutil.rmtree`），請先下載上次的 ZIP。
7. **頭像縮圖 404**：`avatar.enabled=false` 的 slot 不會發出圖片請求；`_refreshAvatarThumbs()` 負責在確認檔案存在後才填入 src。
8. **`dom.previewCharName` 已移除**：`preview.js` 不再設定此元素，角色名稱顯示在 toolbar 的 `char-switcher-label`。
