---
id: "d21e2e6b-6ce7-4ebb-aded-87e3a2eb6489"
title: "RosterReciter Codepilot Setup & Environment Config"
kind: process
created: 2026-05-19
updated: 2026-05-19
review_after: 2026-08-17
status: active
tags: ["codepilot", "completed", "configuration", "development", "flask", "python", "rosterreciter", "setup", "task-report", "venv"]
filenames: ["D:\project\python\roster-reciter\.codepilot\toolbox_commands\install.yaml", "D:\project\python\roster-reciter\.codepilot\toolbox_commands\start.yaml", "D:\project\python\roster-reciter\AGENTS.md"]
links: ["\\?\D:\project\python\roster-reciter\.codepilot_knowledge\2026-05-19_144921_c832e99e_rosterreciter-架構與開發環境筆記.md"]
source_chat_id: "603b15c1-faee-4fec-a5d5-aaf85fb98b9a"
created_at: "2026-05-19T06:49:41.685509100+00:00"
summary: "RosterReciter — Codepilot 設定完成"
description: "建立的 Artifacts"
related_files: ["venv/Scripts/python.exe"]
content_hash: "d19f2ebb8b205e706df47773e4416bfd37f3e5ec41760295845779c7ba6e869d"
source_tool: "memories_add_enriched"
---

## RosterReciter — Codepilot 設定完成

### 建立的 Artifacts

| 檔案 | 類型 | 說明 |
|------|------|------|
| `AGENTS.md` | 專案說明文件 | 環境設定、啟動指令、目錄結構、API 速覽、核心模組說明、程式碼慣例、常見陷阱 |
| `.codepilot/toolbox_commands/start.yaml` | Service 指令 | 啟動 Flask dev server，自動開啟 http://localhost:5000 |
| `.codepilot/toolbox_commands/install.yaml` | Cmdline 指令 | 重建 venv（py -3.10）並安裝相依套件 |
| Knowledge entry | 知識庫 | 架構筆記、venv 重建方式、資料流說明 |

### 重要發現
- **venv 已損壞**：`venv/Scripts/python.exe` 不存在，需執行 `/install` 指令重建
- Python 版本：3.10（使用 `py -3.10` launcher）
- 相依套件極簡：僅 Flask + Pillow

### 驗證步驟
1. 在 Codepilot Toolbox 執行 `/install` → 應看到 pip 安裝成功訊息
2. 執行 `/start` → 應看到 Flask 啟動訊息，瀏覽器自動開啟 http://localhost:5000
