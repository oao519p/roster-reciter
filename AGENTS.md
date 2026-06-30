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
rmdir /s /q venv
py -3.10 -m venv venv
venv\Scripts\activate
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
├── tools/
│   └── build_namemap.py      # 從 operator_data JSON 產生 namemap.json
├── config/
│   ├── default_layout.json   # 出廠預設版面（重設時讀取，進版控）
│   ├── layout.json           # 使用者目前版面（自動儲存，gitignore）
│   └── namemap.json          # 角色名稱對照表（進版控）
├── core/
│   ├── image_composer.py     # Pillow 圖片合成核心
│   ├── layout.py             # 版面 dataclass（Layout / ImageSlot / TitleBox…）
│   └── roster.py             # 角色掃描 / 名稱對照表
├── static/
│   ├── css/main.css
│   ├── fonts/                # 字型（Noto Sans TC）
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
| POST | `/api/layout/default` | 重設為預設版面（保留所有資源路徑與 namemap 設定） |
| POST | `/api/layout/reslot` | 只修改角色框 W/H（保留 title/canvas/樣式等所有其他設定） |
| POST | `/api/scan` | 掃描角色圖片清單 |
| POST | `/api/preview` | 預覽單張投影片（回傳 PNG，也供單一下載使用） |
| POST | `/api/generate` | 批量生成並下載 ZIP |
| POST | `/api/upload/background` | 上傳背景圖 |
| POST | `/api/upload/background/clear` | 清除背景圖 |
| POST | `/api/upload/default_image` | 上傳全局缺圖預設 |
| POST | `/api/upload/default_image/<n>` | 上傳玩家 n 的缺圖預設 |
| POST | `/api/upload/avatar/<n>` | 上傳玩家 n 的頭像（回傳 `img_w`/`img_h` 供前端更新框比例） |
| POST | `/api/upload/namemap` | 上傳角色名稱對照表（JSON），接受 `mode` / `lang` form fields |
| POST | `/api/upload/namemap/clear` | 清除 namemap，重置 mode/lang 為預設值 |
| GET | `/api/uploads/status` | 查詢各上傳資源是否存在（回傳 `background_name`、`default_image_name`） |
| GET | `/api/fonts` | 列出系統字型（TTF/TTC/OTF） |
| GET | `/api/browse/folder` | 開啟原生資料夾選擇對話框 |
| GET/POST | `/api/session` | 已廢棄（stub，回傳空值） |
| POST | `/api/session/clear` | 已廢棄（stub） |

---

## 核心模組說明

### `core/layout.py`
版面資料結構，全部使用 Python `dataclass`：
- `Layout` → `CanvasConfig` + `TitleBox` + `list[ImageSlot]` + 工作環境欄位 + 資源路徑欄位
- 工作環境欄位：`remember`（bool）、`base_dir`、`player_folders`、`player_count`
- 資源路徑欄位：`background_path`、`default_image_path`、`player_default_paths`、`namemap_path`、`namemap_mode`、`namemap_lang`、**`slot_mode`**
- **`label_style: TextStyle`** — 全局名字文字樣式（所有玩家共用，不 per-slot）
- **`date_style: TextStyle`** — 全局入職日樣式（`color` 作為標籤底色，文字自動白/黑）
- **`date_width: int` / `date_height: int`** — 入職日框全局尺寸
- `ImageSlot` → 每位玩家的圖片框位置，含：
  - `AvatarBox`（頭像，自由比例 `width/height`，不再強制正方形）
  - `LabelBox`（名字，只存位置/大小/文字/背景色，字型由 `label_style` 統一）
  - `DateBox`（入職日，只存 `enabled`/`x`/`y`/`date_text`，W/H 由全局設定）
- `Layout.save()` / `Layout.load()` 讀寫 JSON
- `Layout.make_default(player_count, slot_mode)` 產生預設版面，`slot_mode` 決定角色框預設大小：`formation`（180×375）或 `card`（180×360）
- **向下相容**：舊 `layout.json` 的 `avatar.size` 自動轉換為 `width=height=size`

### `core/roster.py`
- `RosterManager.scan_characters()` — 掃描第一位玩家資料夾，取得角色清單
- `RosterManager.get_image_path(player_index, file_stem)` — 取得圖片路徑，含 fallback 邏輯
- 支援 JSON namemap，格式：`{charId: {tw, cn, en, jp}}`
- `namemap_mode`：`normal`（檔名直接對應 key）或 `hr_dossier`（`序號_角色名` substring 比對）
- `namemap_lang`：`tw` / `cn` / `en` / `jp`
- HR Dossier 模式：先取 `_` 後的 `char_part` 做精確比對，找不到再做 substring fallback
- **跨伺服器比對**：`_char_aliases` 建立 `{display_name → {所有語言別名}}`，`get_image_path` 找不到精確檔名時用別名掃描目標資料夾
- CSV namemap 已移除

### `core/image_composer.py`
- `compose_slide(layout, title_text, image_paths, ...)` — 主合成函式，回傳 PNG bytes
- 圖片以 **cover** 模式裁切填滿框格（等比例縮放後中心裁切，無預設尺寸假設）
- 名字框使用 `layout.label_style` 全局樣式，忽略 `slot.label.style`
- 入職日框使用 `layout.date_style` + `layout.date_width/date_height`，字型固定 Noto Sans TC
- 缺圖預設：半透明黑色覆蓋層 + NO INFO 白字置中（字體大小依框自動縮放）
- 字型快取於 `_font_cache`，避免重複載入

### `tools/build_namemap.py`
- 從 ArknightsGameResource 的 `character_table.json`（GitHub raw）更新 `config/namemap.json`
- 過濾 `char_` 開頭的角色，排除 29 個預備/盟約幹員（`EXCLUDE_KEYS`）
- 比對現有 namemap.json，只新增缺少的角色
- 自動填入 `cn`（name）和 `en`（appellation），`tw` 留空
- 使用方式：`python tools/build_namemap.py`（互動式）
- 流程：檢查 commit sha → 下載 → 比對 → 顯示新增/缺少 tw → 詢問是否寫入 → 逐一詢問每個缺少 tw 的角色（[1] 自動轉換 / [2] 手動輸入）
- 使用 `opencc-python-reimplemented` 進行簡繁轉換（s2t）
- commit sha 記錄在 `tools/namemap_meta.json`（不影響 namemap.json 結構）
- GitHub API 使用 `?path=gamedata/excel/character_table.json` 精確查詢該檔案的 commit
- 如果 commit sha 未變，提示「已是最新」並詢問是否強制更新
- GitHub API rate limit（403）時自動跳過 commit 檢查並繼續執行
- 寫入時按 key 字母排序（`sort_keys=True`）
- Windows console 支援 UTF-8（`sys.stdout.reconfigure`）

---

## 前端模組說明

### `static/js/main.js`
主控制器，管理全域 `state`（baseDir、playerFolders、characters、selectedCharIndex、layout）。
- `init()` → 載入版面、還原工作環境、綁定事件
- `scanCharacters()` → 呼叫 `/api/scan`，掃描完成後自動預覽第一個角色
- `_saveAndRescan()` → 儲存 layout 後若已有掃描結果則自動重新掃描（namemap mode/lang 變更時呼叫）
- `_downloadSingle(char)` → 呼叫 `/api/preview` 取得單一角色 PNG 並觸發下載
- `generateAll()` → 批量生成 ZIP，自訂角色 `file_stem` 映射為 `"__blank__"`
- `immediateSaveLayout()` → 預覽前呼叫，確保後端用最新設定
- `syncEnvToLayout()` → 將 baseDir / playerFolders / remember 注入 `state.layout` 再儲存
- `syncLayoutToForm()` / `collectLayoutFromForm()` → 包含 `label_style`、`date_style`、`date_width`、`date_height` 的雙向同步
- `loadUploadsStatus()` → 查詢 `/api/uploads/status`，分別設定 `*-file`（檔名）和 `*-status`（狀態）span
- **上傳處理**：所有上傳 change handler 在呼叫 API 前更新對應的 `*-file` span 顯示檔名；清除 handler 清除後重置為 `"未選擇檔案"`
- **標題開關**：`titleEnabled` change handler 設定 `state.layout.title_enabled`，切換表單欄位顯示/停用，呼叫 `layoutEditor.renderDragBoxes()` 和 `previewMgr.requestBlankPreview()`
- **自訂角色**：`btnAddChar` 點擊後 `prompt` 輸入名稱，建立 `{file_stem: "__custom__N", display_name, _custom: true}` 物件。`_custom=true` 的標籤會顯示 ✕ 刪除按鈕。預覽/下載/批量生成時，`file_stem` 映射為 `"__blank__"`（不匹配任何實際圖片，使用缺圖預設）

### `static/js/preview.js`
- `requestPreview()` → 以目前選取角色呼叫 `/api/preview`，更新右側預覽圖
- `requestBlankPreview()` → 無角色時預覽空版面（背景 + 框格位置）

### `static/js/layout-editor.js`
- `renderSlotInputs()` → 渲染每個玩家的 accordion 設定區塊，自動還原展開狀態
- `renderDragBoxes()` → 在預覽圖上疊加可拖拉的方塊（標題框/圖片框/頭像框/名字框/入職日框）。**標題框只在 `layout.title_enabled !== false` 時渲染**
- `_refreshAvatarThumbs()` → 查詢 `/api/uploads/status`，只對 `avatar.enabled=true` 的 slot 填入縮圖 src
- `collectSlotInputs()` → 將表單值收集回 `state.layout.image_slots`（不含字型欄位，字型由全局 label_style 管理）
- `_applySyncSlot()` → 同步角色框大小/位置（受 size/alignX/alignY checkbox 控制）
- `_applySyncSub()` → 同步頭像框/名字框/入職日框相對位置、大小、enabled（各自圖片、名字文字與日期保留）
- 頭像框：只顯示高度輸入，寬度由 `_bindSlotEvents` 的 `av-h` 分支等比例計算；上傳後根據圖片實際比例更新
- 入職日框：個人設定只留 X/Y + 日期文字，W/H 由全局 `date_width/date_height` 管理
- 名字框/入職日框子區塊：可點擊標題列收合/展開

---

## UI 結構（Step 說明）

| Step | 面板 | 主要內容 |
|------|------|---------|
| 1 | 資料夾 | base_dir、玩家數量、玩家資料夾、**namemap 設定（模式/語言/上傳/清除，含 ? 圖示 hover 說明）**、**角色框比例（僅 HR Dossier 顯示）**、掃描按鈕 |
| 2 | 資源 | 背景圖、全局缺圖、個別玩家缺圖（**上傳區塊顯示 `[檔案名] [狀態] [清除] [上傳]`**，檔案名過長自動截斷） |
| 3 | 版面 | 畫布尺寸、背景色、**標題啟用開關**、標題文字樣式（含字型掃描）、重設版面 |
| 4 | 圖片框 | **名字文字樣式（全局可收合，含字型掃描）**、**入職日樣式（全局可收合，含 W/H）**、等比例鎖定、同步角色框、同步頭像/名字/入職日框、各玩家 accordion（含頭像/名字/入職日 toggle） |
| 5 | 生成 | 角色標籤列表（含單一 ⬇ 下載）、**+ 新增角色（全缺圖）**、批量生成 ZIP |

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

1. **venv 執行檔缺失**：`venv/Scripts/python.exe` 不存在時，需重建 venv。
2. **中文字型**：`label_style.font_path` 與 `title.style.font_path` 都必須指向支援中文的 TTF/TTC，例如 `C:/Windows/Fonts/msjh.ttc`。入職日框字型固定使用 `static/fonts/NotoSansCJKtc-Regular.otf`。
3. **背景圖快取**：Flask 已設定 `SEND_FILE_MAX_AGE_DEFAULT = 0`，預覽時加 `?t=timestamp` 防快取。
4. **上傳大小限制**：`MAX_CONTENT_LENGTH = 50MB`，超大圖片需先壓縮。
5. **`/api/browse/folder`**：使用 `tkinter` 開啟原生對話框，需在有 GUI 的環境執行。
6. **`output/` 每次批量生成前會被清空**（`shutil.rmtree`），請先下載上次的 ZIP。
7. **頭像縮圖 404**：`avatar.enabled=false` 的 slot 不會發出圖片請求；`_refreshAvatarThumbs()` 負責在確認檔案存在後才填入 src。
8. **namemap_path 保留**：`/api/layout/default` 重設版面時會保留所有資源路徑（`background_path`、`namemap_path` 等），不會清除已上傳的資源設定。
9. **namemap mode/lang 同步**：上傳 namemap 或切換 mode/lang radio 後，`state.layout.namemap_mode/lang` 會立即更新，避免後續 `immediateSaveLayout()` 覆蓋掉正確值。
10. **圖片裁切**：cover 模式不假設圖片尺寸，框格寬高比決定裁切結果，建議框格比例與來源圖片一致。
11. **頭像框比例**：`AvatarBox` 改為 `width/height` 自由比例，UI 只顯示高度輸入，寬度等比例自動計算。上傳頭像後自動根據圖片比例更新。舊 `layout.json` 的 `avatar.size` 會自動轉換。
12. **跨伺服器比對**：HR Dossier 模式下，`get_image_path` 會用 `_char_aliases` 掃描目標資料夾，支援繁中/簡中/英文跨伺服器自動對應。`preview_slide` 和 `generate_all` 端點已正確傳入 `namemap_mode/lang`。
13. **入職日框**：W/H 為全局設定（`date_width/date_height`），個人只設 X/Y + 日期文字。`date_style.color` 作為「入職日」標籤底色，文字顏色自動白/黑。
14. **全局設定區收合**：Step 4 的名字/入職日全局設定使用 `<details>/<summary>` 原生收合，預設收合。
15. **自訂角色**：`_custom=true` 的角色在預覽/下載/批量生成時，`file_stem` 一律映射為 `"__blank__"`（不匹配任何實際圖片，使用缺圖預設）。批量生成輸出檔名使用 `display_name`（非 `file_stem`）
16. **角色框比例**：切換比例呼叫 `/api/layout/reslot`，只修改 slot W/H 與 label.width，X/Y 位置完全不變。一般模式不顯示比例選擇器，HR Dossier 模式下預設為編隊模式（180×375）
17. **標題啟用/停用**：`title_enabled` 欄位控制標題顯示。停用時，Step 3 的標題設定表單隱藏且欄位停用，`renderDragBoxes()` 不渲染標題框。切換時自動觸發 `requestBlankPreview()` 更新預覽
18. **上傳區塊 UI 模式**：使用 `[upload-file span] [upload-state span] [清除 button] [上傳 label] [hidden input]` 結構。`.hidden-file-input` 隱藏瀏覽器預設 input，`.upload-file` 限制 max-width 160px 並使用 `text-overflow: ellipsis` 截斷長檔名
19. **上傳狀態更新**：上傳 change handler 在呼叫 API 前更新 `*-file` span 的 `textContent` 為 `file.name`；清除 handler 清除後重置為 `"未選擇檔案"`。`loadUploadsStatus()` 分別設定檔名和狀態 span
20. **namemap 預設路徑**：`default_layout.json` 的 `namemap_path` 預設為 `"static/uploads/namemap.json"`，`/api/layout/default` 重設時保留
21. **版本號**：Topbar 右上角顯示 `.version-badge`（v0.2.0），使用 `margin-left: auto` 右對齊
