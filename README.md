# RosterReciter 🎴

![version](https://img.shields.io/badge/version-v0.2.0-blue)

報菜名遊戲投影片生成器。
自動將多位玩家的角色圖片合成為單張 1920×1080 PNG，供影片剪輯使用。

## 快速開始

```bash
# 建立 venv（Python 3.10）
py -3.10 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 啟動
python app.py
```

瀏覽器開啟 **http://localhost:5000**

> Flask 以 `debug=True` 啟動，修改 Python 檔案後自動重載。
> 前端 JS/CSS 修改需手動重新整理瀏覽器。

---

## 工具

### `tools/build_namemap.py` — 更新 namemap.json

從 ArknightsGameResource 的 `character_table.json` 更新 `config/namemap.json`。

```bash
python tools/build_namemap.py
```

**互動流程：**
1. 檢查 GitHub commit sha（判斷 character_table.json 是否有更新）
2. 下載並比對 character_table.json 與 namemap.json
3. 顯示新增角色和缺少 tw 的角色
4. 詢問是否寫入 namemap.json
5. 對每個缺少 tw 的角色逐一詢問：
   - `[1]` 自動轉換（使用 opencc 簡轉繁，顯示結果供確認）
   - `[2]` 手動輸入
6. 寫入 namemap.json 並記錄 commit sha（`tools/namemap_meta.json`）

**注意事項：**
- 使用 `opencc-python-reimplemented` 進行簡繁轉換
- commit sha 記錄在 `tools/namemap_meta.json`，不會影響 namemap.json 的結構
- 如果 commit sha 未變，會提示「已是最新」並詢問是否強制更新
- GitHub API rate limit 時自動跳過 commit 檢查並繼續執行
- 寫入時按 key 字母排序（`sort_keys=True`）

### `tools/sort_output.py` — 根據 PRRTS Wiki 排序輸出圖片

批量生成後，可將 `output/` 中的圖片按角色實裝順序重新命名（添加 `001_`、`002_` 等前綴）。

```bash
# 預覽模式（預設，不會實際重命名）
python tools/sort_output.py

# 實際執行重命名
python tools/sort_output.py --execute

# 自訂路徑
python tools/sort_output.py output/ --namemap config/namemap.json
```

**注意事項：**
- 需要先完成 Step 5 批量生成，`output/` 中有圖片才能執行
- 需要 `config/namemap.json` 存在
- 會爬取 PRRTS Wiki（`https://prts.wiki/w/干员一览`）獲取角色排序
- 不在 PRRTS Wiki 中的角色名稱（如自訂角色）不會被重新命名
- 也可從網頁 Step 5 的排序勾選框觸發（透過 `/api/sort` 端點）

---

## 使用流程

### Step 1：資料夾設定
填寫圖片根目錄、玩家數量與各玩家資料夾名稱。

**資料夾結構範例：**
```
D:/images/
├── 玩家1/
│   ├── 001_阿.png
│   └── 002_阿米婭.png
├── 玩家2/
│   ├── 001_阿.png
│   └── 002_阿米婭.png
```

**角色名稱對照表**（在掃描前設定）：
- **比對模式**：
  - 一般（`normal`）：檔名直接對應 namemap key
  - HR Dossier：檔名格式為 `序號_角色名`，自動從 namemap 做 substring 比對
- **顯示語言**（HR Dossier 模式）：繁中 / 簡中 / 英文
- **角色框預設比例**（HR Dossier 模式）：
  - 編隊模式（180×375，預設）
  - 卡片模式（180×360）
  - 切換比例會重設角色框位置/大小，但保留 Step 3/4 的樣式設定（字型、顏色等）
- 上傳 JSON 格式的 namemap 後，切換語言或模式會**自動重新掃描**
- **跨伺服器支援**：HR Dossier 模式下，不同伺服器的玩家資料夾可使用不同語言的角色名（如繁中 `011_琳瑯詩懷雅.png` 與簡中 `005_琳琅诗怀雅.png`），系統會自動根據 namemap 的別名對應找到正確圖片
- **namemap 預設路徑**：`default_layout.json` 預設 `"namemap_path": "static/uploads/namemap.json"`，重設版面時保留已上傳的 namemap 設定

**namemap JSON 格式：**
```json
{
  "char_001_kjerag": {"tw": "阿", "cn": "阿", "en": "Aak"},
  "char_002_amiya":  {"tw": "阿米婭", "cn": "阿米娅", "en": "Amiya"}
}
```

點「🔍 掃描角色」後自動預覽第一個角色。

### Step 2：資源設定
- **背景圖片**：所有投影片共用，上傳後自動預覽
- **缺圖預設圖片（全局）**：某玩家缺少某角色時使用（預設顯示半透明黑色 + NO INFO 白字）
- **缺圖預設圖片（個別玩家）**：優先於全局設定
- **上傳狀態顯示**：每個上傳區塊顯示 `[檔案名] [狀態] [清除] [上傳]`，檔案名過長時自動截斷顯示省略號。上傳/清除後自動更新檔案名與狀態

### Step 3：版面設定
調整畫布尺寸、背景顏色、標題文字樣式。

**標題開關**：可切換標題的啟用/停用。停用時，標題設定表單與右側預覽區的標題框會同時隱藏。切換時自動觸發預覽更新。

> ⚠️ **中文字型**：點「掃描」自動列出系統字型，選擇標有 ★ 的中文字型，
> 或手動填寫路徑，例如：`C:/Windows/Fonts/msjh.ttc`

### Step 4：圖片框 / 頭像 / 名字 / 入職日
- 在右側預覽區**拖拉方塊**調整位置，或在左側輸入精確座標
- 每個玩家的設定區塊可**點擊收合/展開**（預設收合）
- 標題列上的「頭像 ✓/○」「名字 ✓/○」「入職日 ✓/○」按鈕可直接切換開關，不需展開
- **全局設定區**（可收合）：
  - 🔤 名字文字樣式：字型（含掃描）、大小、顏色、對齊（所有玩家共用）
  - 📅 入職日樣式：字體大小、標籤底色、寬、高（字型固定 Noto Sans TC）
- **頭像框**：自由比例，只調整高度時寬度依目前比例自動計算；上傳後自動根據圖片比例更新
- **入職日框**：同一行顯示 `[入職日底色] 入職日 [白底] 20xx-xx-xx`，個人設定只留 X/Y + 日期文字
- **同步功能**分為兩個獨立按鈕：
  - 「🔁 同步角色框」：將 P1 的框格大小/位置同步到其他玩家（受 size/X/Y checkbox 控制）
  - 「🔁 同步頭像 / 名字 / 入職日框」：將 P1 的頭像框、名字框、入職日框相對位置、大小、enabled 同步到其他玩家（各自圖片、名字文字與日期保留）

> 圖片以 **cover** 模式填滿框格（等比例縮放後中心裁切）。
> 框格的寬高比決定裁切方式，建議設成與來源圖片相同的比例。

### Step 5：生成輸出
- 點角色標籤選取並預覽
- 每個角色標籤右側有 **⬇ 按鈕**可單獨下載該角色的 PNG
- **「+ 新增角色（全缺圖）」**：手動輸入角色名稱，新增一個全缺圖角色（所有玩家皆使用缺圖預設圖片）。自訂角色標籤右側有 **✕ 刪除** 按鈕
- **排序勾選框**：勾選後批量生成時會根據 PRRTS Wiki 的角色順序排序輸出
- 「⬇ 批量生成 ZIP」下載所有角色的 PNG（含自訂角色，輸出檔名使用角色名稱）

> ⚠️ 每次批量生成前 `output/` 會被清空，請先下載上次的 ZIP。

---

## UI 功能

### Topbar
- 右上角顯示版本號（v0.2.0）

### 上傳區塊
- 顯示已上傳檔案的實際檔名（過長時自動截斷顯示 `...`）
- 自訂樣式的「📁 上傳」按鈕（隱藏瀏覽器預設檔案輸入框文字）
- 上傳/清除後即時更新檔名與狀態顯示

### 標題開關
- Step 3 的標題啟用/停用開關
- 停用時自動隱藏標題相關設定欄位與預覽區的標題拖拉框
- 切換時自動觸發預覽更新

### namemap 說明
- Step 1 的 namemap 說明改為 `?` 圖示，hover 時顯示提示文字

---

## 目錄結構

```
roster-reciter/
├── app.py                    # Flask 主程式，所有 API 路由
├── requirements.txt          # Flask + Pillow
├── tools/
│   ├── build_namemap.py      # 從 character_table.json 更新 namemap.json
│   ├── namemap_meta.json     # commit sha 記錄（自動產生）
│   └── sort_output.py        # 根據 PRRTS Wiki 排序輸出圖片
├── config/
│   ├── default_layout.json   # 出廠預設版面（重設時讀取）
│   ├── layout.json           # 使用者目前版面（自動儲存，gitignore）
│   └── namemap.json          # 角色名稱對照表（進版控）
├── core/
│   ├── image_composer.py     # Pillow 圖片合成核心
│   ├── layout.py             # 版面 dataclass
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

## .gitignore 排除項目

```
venv/
static/uploads/
output/
output.zip
config/layout.json
config/session.json
config/namemap_incomplete.json
.codepilot/trajectories/
.codepilot_knowledge/
__pycache__/
*.pyc
*.pyo
.env
```
