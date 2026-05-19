/**
 * RosterReciter — 主控制器
 */
import { LayoutEditor } from "./layout-editor.js";
import { PreviewManager } from "./preview.js";

// ── 全域狀態 ──────────────────────────────────
const state = {
  baseDir: "",
  playerFolders: [],
  playerCount: 7,
  characters: [],
  selectedCharIndex: -1,
  layout: null,
};

// ── DOM 參考 ──────────────────────────────────
const $ = (id) => document.getElementById(id);
const dom = {
  baseDir:         $("base-dir"),
  btnBrowseBase:   $("btn-browse-base"),
  playerCount:     $("player-count"),
  btnApplyCount:   $("btn-apply-count"),
  playerFolderList:$("player-folder-list"),
  btnScan:         $("btn-scan"),
  scanResult:      $("scan-result"),

  uploadBg:        $("upload-bg"),
  bgStatus:        $("bg-status"),
  uploadDefault:   $("upload-default"),
  defaultStatus:   $("default-status"),
  uploadNamemap:   $("upload-namemap"),
  namemapStatus:   $("namemap-status"),

  canvasW:         $("canvas-w"),
  canvasH:         $("canvas-h"),
  canvasBgColor:   $("canvas-bg-color"),
  titleFontSelect: $("title-font-select"),
  btnLoadFonts:    $("btn-load-fonts"),
  titleFontPath:   $("title-font-path"),
  titleFontSize:   $("title-font-size"),
  titleColor:      $("title-color"),
  titleAlign:      $("title-align"),
  titleX:          $("title-x"),
  titleY:          $("title-y"),
  titleW:          $("title-w"),
  titleH:          $("title-h"),

  btnResetLayout:  $("btn-reset-layout"),
  btnLoadDefault:  $("btn-load-default"),
  layoutStatus:    $("layout-status"),
  slotInputs:      $("slot-inputs"),

  charListHint:    $("char-list-hint"),
  characterList:   $("character-list"),
  btnPreview:      $("btn-preview"),
  btnGenerate:     $("btn-generate"),
  generateStatus:  $("generate-status"),

  previewImg:      $("preview-img"),
  previewPlaceholder: $("preview-placeholder"),
  charSwitcher:      $("char-switcher"),
  charSwitcherLabel: $("char-switcher-label"),
  charSwitcherList:  $("char-switcher-list"),
  previewWrapper:  $("preview-wrapper"),
  dragOverlay:     $("drag-overlay"),
  autosaveIndicator: $("autosave-indicator"),
  btnClearBg:        $("btn-clear-bg"),
  btnSaveNow:        $("btn-save-now"),
  sessionToggle:     $("session-save-toggle"),
};

// ── 子模組 ────────────────────────────────────
const layoutEditor = new LayoutEditor(state, dom, onLayoutChanged, autoSaveLayout);
const previewMgr   = new PreviewManager(state, dom, layoutEditor);

// ── 初始化 ────────────────────────────────────
async function init() {
  await loadLayout();
  await loadSession();
  renderPlayerFolderInputs();
  renderPlayerDefaultList(state.playerCount);
  await loadUploadsStatus();    // 還原 step2 上傳狀態提示
  bindEvents();
  bindStepBar();
  setStepActive(1);
  // 若有記憶設定（remember=true）且有背景圖，自動刷新預覽
  if (state.layout?.remember) {
    previewMgr.requestBlankPreview();
  }
}

// ── 版面載入 ──────────────────────────────────
async function loadLayout() {
  try {
    const res = await fetch("/api/layout");
    state.layout = await res.json();
    syncLayoutToForm();
    layoutEditor.renderSlotInputs();
    layoutEditor.renderDragBoxes();
  } catch (e) {
    console.error("載入版面失敗", e);
  }
}

function syncLayoutToForm() {
  const l = state.layout;
  if (!l) return;
  dom.canvasW.value       = l.canvas.width;
  dom.canvasH.value       = l.canvas.height;
  dom.canvasBgColor.value = l.canvas.background_color;
  dom.titleFontPath.value = l.title.style.font_path;
  dom.titleFontSize.value = l.title.style.font_size;
  dom.titleColor.value    = l.title.style.color;
  dom.titleAlign.value    = l.title.style.align;
  dom.titleX.value        = l.title.x;
  dom.titleY.value        = l.title.y;
  dom.titleW.value        = l.title.width;
  dom.titleH.value        = l.title.height;

  const slotCount = l.image_slots.length;
  if (slotCount > 0) {
    state.playerCount = slotCount;
    dom.playerCount.value = slotCount;
  }
}

function collectLayoutFromForm() {
  const l = state.layout;
  l.canvas.width            = parseInt(dom.canvasW.value) || 1920;
  l.canvas.height           = parseInt(dom.canvasH.value) || 1080;
  l.canvas.background_color = dom.canvasBgColor.value;
  l.title.style.font_path   = dom.titleFontPath.value.trim();
  l.title.style.font_size   = parseInt(dom.titleFontSize.value) || 72;
  l.title.style.color       = dom.titleColor.value;
  l.title.style.align       = dom.titleAlign.value;
  l.title.x      = parseInt(dom.titleX.value) || 0;
  l.title.y      = parseInt(dom.titleY.value) || 0;
  l.title.width  = parseInt(dom.titleW.value) || 1920;
  l.title.height = parseInt(dom.titleH.value) || 100;
}

function onLayoutChanged() {
  const l = state.layout;
  dom.titleX.value = l.title.x;
  dom.titleY.value = l.title.y;
  layoutEditor.renderSlotInputs();
}

// ── 玩家資料夾輸入框 ──────────────────────────
function renderPlayerFolderInputs() {
  const count = state.playerCount;
  const oldValues = state.playerFolders.slice();
  dom.playerFolderList.innerHTML = "";

  for (let i = 0; i < count; i++) {
    const div = document.createElement("div");
    div.className = "player-folder-item";
    div.innerHTML = `
      <span class="player-label">玩家 ${i + 1}</span>
      <input type="text" class="player-folder-input" data-index="${i}"
             placeholder="資料夾名稱" value="${oldValues[i] || `玩家${i + 1}`}" />
    `;
    dom.playerFolderList.appendChild(div);
  }

  // 同步更新個別預設圖上傳區
  renderPlayerDefaultList(count);
}

function renderPlayerDefaultList(count) {
  const container = document.getElementById("player-default-list");
  if (!container) return;
  container.innerHTML = "";
  container.className = "";
  for (let i = 0; i < count; i++) {
    const row = document.createElement("div");
    row.className = "upload-row";
    row.style.marginBottom = "4px";
    row.innerHTML = `
      <span class="player-label" style="width:52px;flex-shrink:0;font-size:12px;color:var(--text-muted)">玩家 ${i + 1}</span>
      <input type="file" accept="image/*" class="player-default-upload" data-i="${i}" style="font-size:12px;flex:1" />
      <span class="player-default-status status-inline" data-i="${i}"></span>
    `;
    container.appendChild(row);
  }

  container.querySelectorAll(".player-default-upload").forEach((input) => {
    input.addEventListener("change", async () => {
      const i = input.dataset.i;
      const file = input.files[0];
      if (!file) return;
      const statusEl = container.querySelector(`.player-default-status[data-i="${i}"]`);
      const formData = new FormData();
      formData.append("file", file);
      statusEl.textContent = "上傳中...";
      try {
        const res = await fetch(`/api/upload/default_image/${i}`, { method: "POST", body: formData });
        const data = await res.json();
        statusEl.textContent = data.ok ? "✓" : "✗";
        statusEl.className = `player-default-status status-inline ${data.ok ? "ok" : "err"}`;
      } catch {
        statusEl.textContent = "✗";
        statusEl.className = "player-default-status status-inline err";
      }
    });
  });
}

function collectPlayerFolders() {
  state.playerFolders = Array.from(
    document.querySelectorAll(".player-folder-input")
  ).map((el) => el.value.trim());
  state.baseDir = dom.baseDir.value.trim();
}

// ── 事件綁定 ──────────────────────────────────
function bindEvents() {
  // ── 資料夾瀏覽按鈕（呼叫後端 tkinter 對話框）──
  dom.btnBrowseBase.addEventListener("click", async () => {
    dom.btnBrowseBase.disabled = true;
    dom.btnBrowseBase.textContent = "...";
    try {
      const res = await fetch("/api/browse/folder");
      const data = await res.json();
      if (data.ok && data.path) {
        dom.baseDir.value = data.path;
      }
    } catch (e) {
      console.error("瀏覽資料夾失敗", e);
    } finally {
      dom.btnBrowseBase.disabled = false;
      dom.btnBrowseBase.textContent = "📁";
    }
  });

  // ── 套用玩家數 → 自動重設版面 ──
  dom.btnApplyCount.addEventListener("click", async () => {
    const n = Math.max(1, Math.min(20, parseInt(dom.playerCount.value) || 7));
    state.playerCount = n;
    dom.playerCount.value = n;
    renderPlayerFolderInputs();
    // 自動重設版面，讓 image_slots 立即產生
    const res = await fetch("/api/layout/default", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_count: n }),
    });
    state.layout = await res.json();
    syncLayoutToForm();
    await loadSession();              // 還原工作環境（base_dir / player_folders）
    renderPlayerFolderInputs();
    layoutEditor.renderSlotInputs();
    layoutEditor.renderDragBoxes();
    setStatus(dom.layoutStatus, `已套用 ${n} 位玩家版面`, "ok");
  });

  dom.btnScan.addEventListener("click", scanCharacters);

  // 立即儲存版面
  dom.btnSaveNow.addEventListener("click", async () => {
    dom.btnSaveNow.disabled = true;
    dom.btnSaveNow.textContent = "儲存中...";
    await immediateSaveLayout();
    dom.btnSaveNow.textContent = "💾 儲存";
    dom.btnSaveNow.disabled = false;
  });

  // 清除背景圖片
  dom.btnClearBg.addEventListener("click", async () => {
    await fetch("/api/upload/background/clear", { method: "POST" });
    dom.uploadBg.value = "";
    setStatus(dom.bgStatus, "已清除", "ok");
    // 清除後重新預覽（顯示純色背景）
    collectPlayerFolders();
    previewMgr.requestBlankPreview();
  });

  // 記住設定 toggle：ON/OFF 都立即寫入 layout.json（remember 欄位）
  dom.sessionToggle.addEventListener("change", async () => {
    syncEnvToLayout();          // 把 remember 值注入 state.layout
    await immediateSaveLayout(); // 立即儲存到後端
  });

  dom.uploadBg.addEventListener("change", async () => {
    await uploadFile(dom.uploadBg, "/api/upload/background", dom.bgStatus);
    // 上傳後自動預覽：有角色就預覽角色，否則預覽空版面
    collectPlayerFolders();
    if (state.characters.length > 0 && state.selectedCharIndex >= 0) {
      previewMgr.requestPreview();
    } else {
      previewMgr.requestBlankPreview();
    }
  });
  dom.uploadDefault.addEventListener("change", () =>
    uploadFile(dom.uploadDefault, "/api/upload/default_image", dom.defaultStatus)
  );
  dom.uploadNamemap.addEventListener("change", () =>
    uploadFile(dom.uploadNamemap, "/api/upload/namemap", dom.namemapStatus,
      (d) => `已載入 ${d.count} 筆`)
  );

  // ── 掃描系統字型 ──
  dom.btnLoadFonts.addEventListener("click", async () => {
    dom.btnLoadFonts.textContent = "掃描中...";
    try {
      const res = await fetch("/api/fonts");
      const data = await res.json();
      if (data.ok && data.fonts.length > 0) {
        dom.titleFontSelect.innerHTML = `<option value="">── 手動輸入路徑 ──</option>`;
        let firstChinesePath = "";
        data.fonts.forEach((f) => {
          const opt = document.createElement("option");
          opt.value = f.path;
          opt.textContent = f.is_chinese ? `★ ${f.name}` : f.name;
          dom.titleFontSelect.appendChild(opt);
          if (f.is_chinese && !firstChinesePath) firstChinesePath = f.path;
        });
        dom.btnLoadFonts.textContent = `✓ ${data.fonts.length} 個`;
        // 自動預選第一個中文字型
        if (firstChinesePath) {
          dom.titleFontSelect.value = firstChinesePath;
          dom.titleFontPath.value = firstChinesePath;
        }
      }
    } catch (e) {
      dom.btnLoadFonts.textContent = "失敗";
    }
  });

  // 選字型 → 填入路徑欄
  dom.titleFontSelect.addEventListener("change", () => {
    if (dom.titleFontSelect.value) {
      dom.titleFontPath.value = dom.titleFontSelect.value;
    }
  });

  // step3 內的「重設為原廠版面」：只重設 canvas/title/image_slots，保留工作環境
  dom.btnResetLayout.addEventListener("click", async () => {
    const res = await fetch("/api/layout/default", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_count: state.playerCount }),
    });
    state.layout = await res.json();
    syncLayoutToForm();
    await loadSession();
    renderPlayerFolderInputs();
    layoutEditor.renderSlotInputs();
    layoutEditor.renderDragBoxes();
    dom.titleFontSelect.innerHTML = `<option value="">── 手動輸入路徑 ──</option>`;
    dom.btnLoadFonts.textContent = "掃描";
    setStatus(dom.layoutStatus, "已重設為原廠版面（canvas / title / image_slots）", "ok");
    previewMgr.requestBlankPreview();
  });

  // toolbar 的「載入原廠設定」：完整重設，包含清空工作環境
  dom.btnLoadDefault?.addEventListener("click", async () => {
    const res = await fetch("/api/layout/default", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_count: 1 }),
    });
    state.layout = await res.json();
    // 清空工作環境
    state.baseDir = ""; dom.baseDir.value = "";
    state.playerFolders = [];
    state.playerCount = 1; dom.playerCount.value = 1;
    state.characters = []; state.selectedCharIndex = -1;
    syncLayoutToForm();
    renderPlayerFolderInputs();
    layoutEditor.renderSlotInputs();
    layoutEditor.renderDragBoxes();
    dom.titleFontSelect.innerHTML = `<option value="">── 手動輸入路徑 ──</option>`;
    dom.btnLoadFonts.textContent = "掃描";
    dom.characterList.innerHTML = "";
    dom.charListHint.style.display = "";
    previewMgr.requestBlankPreview();
  });



  // ── 預覽（修正：確保 selectedCharIndex 有效）──
  dom.btnPreview.addEventListener("click", async () => {
    collectPlayerFolders();
    // 先立即儲存，確保後端用最新設定
    await immediateSaveLayout();

    if (state.characters.length === 0) {
      // 無角色時預覽空版面（只顯示背景 + 框框）
      previewMgr.requestBlankPreview();
      return;
    }
    // 若沒有選取，自動選第一個
    if (state.selectedCharIndex < 0) {
      state.selectedCharIndex = 0;
      document.querySelectorAll(".char-tag").forEach((t, i) =>
        t.classList.toggle("selected", i === 0)
      );
    }
    previewMgr.requestPreview();
  });

  // 角色切換下拉：點擊 label 開關
  dom.charSwitcher.addEventListener("click", (e) => {
    e.stopPropagation();
    const isOpen = dom.charSwitcher.classList.toggle("open");
    if (isOpen) {
      const rect = dom.charSwitcher.getBoundingClientRect();
      dom.charSwitcherList.style.top  = `${rect.bottom + 2}px`;
      dom.charSwitcherList.style.left = `${rect.left}px`;
    }
  });
  document.addEventListener("click", () => {
    dom.charSwitcher.classList.remove("open");
  });

  dom.btnGenerate.addEventListener("click", generateAll);
}

// ── 掃描角色 ──────────────────────────────────
async function scanCharacters() {
  collectPlayerFolders();

  if (!state.baseDir) {
    setStatus(dom.scanResult, "請填寫圖片根目錄", "err");
    return;
  }
  if (state.playerFolders.some((f) => !f)) {
    setStatus(dom.scanResult, "請填寫所有玩家資料夾名稱", "err");
    return;
  }

  setStatus(dom.scanResult, "掃描中...", "");

  try {
    const res = await fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ base_dir: state.baseDir, player_folders: state.playerFolders }),
    });
    const data = await res.json();

    if (!data.ok) {
      setStatus(dom.scanResult, `錯誤：${data.error}`, "err");
      return;
    }

    state.characters = data.characters;
    state.selectedCharIndex = data.characters.length > 0 ? 0 : -1;
    renderCharacterList();
    setStatus(dom.scanResult, `找到 ${data.characters.length} 個角色`, "ok");

    if (data.characters.length > 0) {
      dom.charListHint.style.display = "none";
      // 掃描完成後自動儲存並預覽第一個角色
      await immediateSaveLayout();
      previewMgr.requestPreview();
    }
  } catch (e) {
    setStatus(dom.scanResult, `網路錯誤：${e.message}`, "err");
  }
}

function renderCharacterList() {
  // step5 角色標籤列表
  dom.characterList.innerHTML = "";
  state.characters.forEach((char, i) => {
    const tag = document.createElement("div");
    tag.className = "char-tag" + (i === state.selectedCharIndex ? " selected" : "");
    tag.textContent = char.display_name;
    tag.dataset.index = i;
    tag.addEventListener("click", () => {
      state.selectedCharIndex = i;
      document.querySelectorAll(".char-tag").forEach((t) =>
        t.classList.toggle("selected", parseInt(t.dataset.index) === i)
      );
      // 同步 toolbar 角色切換下拉
      dom.charSwitcherLabel.textContent = char.display_name;
      dom.charSwitcherList.querySelectorAll("li").forEach((el, j) =>
        el.classList.toggle("selected", j === i)
      );
      previewMgr.requestPreview();
    });
    dom.characterList.appendChild(tag);
  });
  // toolbar 角色切換下拉
  dom.charSwitcherList.innerHTML = "";

  if (state.characters.length === 0) {
    dom.charSwitcherLabel.textContent = "— 尚未掃描 —";
    return;
  }

  state.characters.forEach((char, i) => {
    const li = document.createElement("li");
    li.textContent = char.display_name;
    if (i === state.selectedCharIndex) li.classList.add("selected");
    li.addEventListener("click", (e) => {
      e.stopPropagation();
      state.selectedCharIndex = i;
      dom.charSwitcherLabel.textContent = char.display_name;
      dom.charSwitcherList.querySelectorAll("li").forEach((el, j) =>
        el.classList.toggle("selected", j === i)
      );
      document.querySelectorAll(".char-tag").forEach((t) =>
        t.classList.toggle("selected", parseInt(t.dataset.index) === i)
      );
      dom.charSwitcher.classList.remove("open");
      previewMgr.requestPreview();
    });
    dom.charSwitcherList.appendChild(li);
  });

  const selIdx = Math.max(0, state.selectedCharIndex);
  dom.charSwitcherLabel.textContent = state.characters[selIdx]?.display_name ?? "— 尚未掃描 —";
}

// ── 儲存版面 ──────────────────────────────────
export async function saveLayout(showStatus = false) {
  collectLayoutFromForm();
  layoutEditor.collectSlotInputs();

  try {
    const res = await fetch("/api/layout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state.layout),
    });
    const data = await res.json();
    if (showStatus) {
      if (data.ok) setStatus(dom.layoutStatus, "✓ 版面已儲存", "ok");
      else setStatus(dom.layoutStatus, `儲存失敗：${data.error}`, "err");
    }
    return data.ok;
  } catch (e) {
    if (showStatus) setStatus(dom.layoutStatus, `網路錯誤：${e.message}`, "err");
    return false;
  }
}

// ── 批量生成 ──────────────────────────────────
async function generateAll() {
  if (state.characters.length === 0) {
    setStatus(dom.generateStatus, "請先掃描角色", "err");
    return;
  }

  collectPlayerFolders();
  await saveLayout(false);

  setStatus(dom.generateStatus, `<span class="spinner"></span>生成中（${state.characters.length} 張）...`, "");
  dom.btnGenerate.disabled = true;

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        base_dir: state.baseDir,
        player_folders: state.playerFolders,
        characters: state.characters,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: "未知錯誤" }));
      setStatus(dom.generateStatus, `生成失敗：${err.error}`, "err");
      return;
    }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "roster_slides.zip";
    a.click();
    URL.revokeObjectURL(url);

    setStatus(dom.generateStatus, `✅ 完成，共 ${state.characters.length} 張`, "ok");
  } catch (e) {
    setStatus(dom.generateStatus, `網路錯誤：${e.message}`, "err");
  } finally {
    dom.btnGenerate.disabled = false;
  }
}

// ── 通用上傳 ──────────────────────────────────
async function uploadFile(inputEl, url, statusEl, successMsg = null) {
  const file = inputEl.files[0];
  if (!file) return false;
  const formData = new FormData();
  formData.append("file", file);
  setStatus(statusEl, "上傳中...", "");
  try {
    const res = await fetch(url, { method: "POST", body: formData });
    const data = await res.json();
    if (data.ok) {
      if (successMsg) setStatus(statusEl, successMsg(data), "ok");
      // 若呼叫端沒有自訂訊息，先顯示預設（呼叫端可再覆蓋）
      else setStatus(statusEl, "✓ 上傳成功", "ok");
      return true;
    } else {
      setStatus(statusEl, `✗ ${data.error}`, "err");
      return false;
    }
  } catch (e) {
    setStatus(statusEl, "✗ 網路錯誤", "err");
    return false;
  }
}

// ── 立即儲存版面（無 debounce，預覽前呼叫）──────
async function immediateSaveLayout() {
  collectLayoutFromForm();
  layoutEditor.collectSlotInputs();
  syncEnvToLayout();            // ← 確保 remember / base_dir / player_folders 先注入
  const indicator = dom.autosaveIndicator;
  indicator.textContent = "⟳ 儲存中...";
  indicator.className = "autosave-indicator saving";
  try {
    const res = await fetch("/api/layout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state.layout),
    });
    const data = await res.json();
    if (data.ok) {
      indicator.textContent = "✓ 已儲存";
      indicator.className = "autosave-indicator saved";
      setTimeout(() => {
        indicator.textContent = "";
        indicator.className = "autosave-indicator";
      }, 1500);
    }
  } catch (e) {
    indicator.textContent = "";
    indicator.className = "autosave-indicator";
  }
}

// ── 工作環境還原（從 layout.json 的 remember 欄位）────────────────
async function loadSession() {
  // 工作環境已合併進 layout.json，由 loadLayout() 載入後在此還原
  try {
    const l = state.layout;
    if (!l) return;

    // 還原「記住設定」開關（預設 true）
    const remember = l.remember !== undefined ? l.remember : true;
    dom.sessionToggle.checked = remember;

    if (!remember) return;   // remember=false 代表後端已套用 default，不還原路徑

    // 還原工作環境
    if (l.base_dir)       { state.baseDir = l.base_dir; dom.baseDir.value = l.base_dir; }
    if (l.player_count)   { state.playerCount = l.player_count; dom.playerCount.value = l.player_count; }
    if (l.player_folders && l.player_folders.length > 0) {
      state.playerFolders = l.player_folders;
    }
  } catch (e) {
    console.warn("還原工作環境失敗", e);
  }
}

// ── Step2 上傳狀態還原 ────────────────────────
async function loadUploadsStatus() {
  try {
    const res = await fetch(`/api/uploads/status?player_count=${state.playerCount}`);
    const data = await res.json();
    if (!data.ok) return;

    const ts = Date.now();   // 防快取

    // 背景圖：只顯示文字狀態（縮圖在右側預覽區顯示）
    if (data.background) {
      setStatus(dom.bgStatus, "✓ 已上傳", "ok");
    }

    // 全局缺圖：顯示縮圖（小圖，換行）
    if (data.default_image) {
      setStatus(dom.defaultStatus,
        `✓ 已上傳<br><img src="/static/uploads/default_image.png?t=${ts}"
              style="height:48px;border-radius:3px;margin-top:4px;display:block">`, "ok");
    }

    // 名稱對照表：顯示筆數
    if (data.namemap_count > 0) {
      setStatus(dom.namemapStatus, `✓ 已載入 ${data.namemap_count} 筆`, "ok");
    }

    // 個別玩家缺圖預設：顯示縮圖
    const container = document.getElementById("player-default-list");
    if (container && data.player_defaults) {
      data.player_defaults.forEach((exists, i) => {
        const el = container.querySelector(`.player-default-status[data-i="${i}"]`);
        if (el && exists) {
          el.innerHTML =
            `<img src="/static/uploads/default_${i}.png?t=${ts}"
                  style="height:28px;vertical-align:middle;border-radius:2px"> ✓`;
          el.className = "player-default-status status-inline ok";
        }
      });
    }
  } catch (e) {
    console.warn("載入上傳狀態失敗", e);
  }
}

// ── 將工作環境寫入 state.layout，再由 autoSave 一起存入 layout.json ──
function syncEnvToLayout() {
  if (!state.layout) return;
  collectPlayerFolders();
  state.layout.remember      = dom.sessionToggle.checked;
  state.layout.base_dir      = state.baseDir;
  state.layout.player_folders = state.playerFolders;
  state.layout.player_count  = state.playerCount;
}

async function persistSession() {
  // 不再呼叫 /api/session，改由 autoSaveLayout 統一儲存
  // 此函式保留供舊呼叫點相容，實際由 syncEnvToLayout 注入資料
  syncEnvToLayout();
}

// ── 自動儲存版面（供 layoutEditor 呼叫）─────────
async function autoSaveLayout() {
  const indicator = dom.autosaveIndicator;
  indicator.textContent = "⟳ 儲存中...";
  indicator.className = "autosave-indicator saving";

  collectLayoutFromForm();
  layoutEditor.collectSlotInputs();
  syncEnvToLayout();            // ← 先注入工作環境，再儲存

  try {
    const res = await fetch("/api/layout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state.layout),
    });
    const data = await res.json();
    if (data.ok) {
      indicator.textContent = "✓ 已自動儲存";
      indicator.className = "autosave-indicator saved";
      setTimeout(() => {
        indicator.textContent = "";
        indicator.className = "autosave-indicator";
      }, 2000);
      // 工作環境已在儲存前由 syncEnvToLayout() 注入，此處無需重複
    }
  } catch (e) {
    indicator.textContent = "";
    indicator.className = "autosave-indicator";
  }
}

// ── Step Bar（Tab 切換）────────────────────────
function setStepActive(step) {
  // 切換 step-btn 高亮
  document.querySelectorAll(".step-btn").forEach((btn) => {
    const s = parseInt(btn.dataset.target?.replace("panel-", "") || 0);
    btn.classList.toggle("active", s === step);
    btn.classList.remove("done");
  });
  // 切換 panel 顯示
  document.querySelectorAll(".panel").forEach((panel) => {
    const s = parseInt(panel.id.replace("panel-", "") || 0);
    panel.classList.toggle("active", s === step);
  });
}

function bindStepBar() {
  document.querySelectorAll(".step-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      // 離開前先把目前表單值存進 state.layout，避免切換後被舊值覆蓋
      collectLayoutFromForm();
      layoutEditor.collectSlotInputs();
      const s = parseInt(btn.dataset.target.replace("panel-", ""));
      setStepActive(s);
    });
  });
}

// ── 工具 ──────────────────────────────────────
export function setStatus(el, msg, type) {
  el.innerHTML = msg;
  el.className = "status-msg" + (type ? ` ${type}` : "");
}

init();
