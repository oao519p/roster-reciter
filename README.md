# RosterReciter 🎴

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

## 使用流程

### Step 1：資料夾設定
填寫圖片根目錄、玩家數量與各玩家資料夾名稱，點「掃描角色」。

**資料夾結構範例：**
```
D:/images/
├── 玩家1/
│   ├── A.png
│   └── B.png
├── 玩家2/
│   ├── A.png
│   └── B.png
```

掃描完成後會自動預覽第一個角色。

### Step 2：資源設定
- **背景圖片**：所有投影片共用，上傳後自動預覽
- **缺圖預設圖片（全局）**：某玩家缺少某角色時使用
- **缺圖預設圖片（個別玩家）**：優先於全局設定
- **頭像**：在 Step 4 圖片框設定中各別上傳
- **角色名稱對照表**：CSV 或 JSON

**CSV 格式：**
```csv
file_stem,display_name
A,角色甲
B,角色乙
```

**JSON 格式：**
```json
{"A": "角色甲", "B": "角色乙"}
```

### Step 3：版面設定
調整畫布尺寸、背景顏色、標題文字樣式。

> ⚠️ **中文標題**：點「掃描」自動列出系統字型，選擇標有 ★ 的中文字型，
> 或手動填寫路徑，例如：`C:/Windows/Fonts/msjh.ttc`

### Step 4：圖片框 / 頭像 / 名字
- 在右側預覽區**拖拉方塊**調整位置，或在左側輸入精確座標
- 可開關各玩家的頭像框、名字框
- 「🔁 套用同步」可將 P1 的框格設定複製到所有玩家

### Step 5：生成輸出
點角色標籤或使用右上角下拉切換預覽 → 確認效果後點「⬇ 批量生成 ZIP」下載所有 PNG。

> ⚠️ 每次批量生成前 `output/` 會被清空，請先下載上次的 ZIP。

---

## 目錄結構

```
roster-reciter/
├── app.py                    # Flask 主程式，所有 API 路由
├── requirements.txt          # Flask + Pillow
├── config/
│   ├── default_layout.json   # 出廠預設版面（重設時讀取）
│   └── layout.json           # 使用者目前版面（自動儲存，gitignore）
├── core/
│   ├── image_composer.py     # Pillow 圖片合成核心
│   ├── layout.py             # 版面 dataclass
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

## .gitignore 排除項目

```
venv/
static/uploads/
output/
output.zip
config/layout.json
config/session.json
.codepilot/trajectories/
.codepilot_knowledge/
__pycache__/
*.pyc
*.pyo
.env
```
