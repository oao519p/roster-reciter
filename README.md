# RosterReciter 🎴

報菜名遊戲投影片生成器。
自動將多位玩家的角色圖片合成為單張 PNG，供影片剪輯使用。

## 快速開始

```bash
pip install -r requirements.txt
python app.py
```

瀏覽器開啟 **http://localhost:5000**

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

### Step 2：資源設定
- **背景圖片**：所有投影片共用
- **缺圖預設圖片**：某玩家缺少某角色時使用
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
調整畫布尺寸、標題文字樣式，點「儲存版面」。

> ⚠️ **中文標題**：需填寫支援中文的 TTF 字型路徑，例如：
> `C:/Windows/Fonts/msjh.ttc`

### Step 4：圖片框位置
在右側預覽區**拖拉方塊**調整位置，或在左側輸入精確座標，點「儲存版面」。

### Step 5：生成輸出
選取角色 → 點「👁 預覽」確認效果 → 點「⬇ 批量生成 ZIP」下載所有 PNG。

---

## 目錄結構

```
roster-reciter/
├── app.py                 # Flask 主程式
├── requirements.txt
├── config/
│   └── default_layout.json  # 版面配置（自動儲存）
├── core/
│   ├── image_composer.py  # Pillow 圖片合成
│   ├── layout.py          # 版面資料結構
│   └── roster.py          # 角色/玩家管理
├── static/
│   ├── css/main.css
│   ├── js/
│   │   ├── main.js
│   │   ├── layout-editor.js
│   │   └── preview.js
│   └── uploads/           # 上傳暫存（自動產生）
├── templates/
│   └── index.html
└── output/                # 輸出 PNG（自動產生）
```

---

## Git 設定（獨立 repo）

```bash
cd roster-reciter
git init
git add .
git commit -m "feat: initial commit"
```

建議在 `.gitignore` 加入：
```
static/uploads/
output/
output.zip
__pycache__/
*.pyc
```
