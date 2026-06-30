/**
 * 版面編輯器 — 圖片框 / 頭像 / 名字 輸入 + 拖拉調整 + 同步
 */
export class LayoutEditor {
  constructor(state, dom, onChangedCallback, autoSaveCallback) {
    this.state = state;
    this.dom = dom;
    this.onChanged = onChangedCallback;
    this.autoSave = autoSaveCallback;
    this._scale = 1;
    this._autoSaveTimer = null;
  }

  // ── 自動儲存 debounce ─────────────────────────
  _triggerAutoSave() {
    clearTimeout(this._autoSaveTimer);
    this._autoSaveTimer = setTimeout(() => {
      if (this.autoSave) this.autoSave();
    }, 800);
  }

  get _lockRatio() {
    const el = document.getElementById("lock-ratio");
    return el ? el.checked : false;
  }

  // ── 渲染每個玩家的完整設定區塊 ───────────────
  renderSlotInputs() {
    const { layout } = this.state;
    if (!layout) return;

    // 記憶目前哪些 slot 是展開的
    const openSet = new Set();
    this.dom.slotInputs.querySelectorAll(".slot-section.open").forEach((el) => {
      openSet.add(parseInt(el.dataset.i));
    });

    // 記錄本次 render 時的 W/H，作為等比例計算的基準
    this._baseSlotW = {};
    this._baseSlotH = {};
    layout.image_slots.forEach((slot, i) => {
      this._baseSlotW[i] = slot.width;
      this._baseSlotH[i] = slot.height;
    });
    this.dom.slotInputs.innerHTML = "";

    layout.image_slots.forEach((slot, i) => {
      const sec = document.createElement("div");
      sec.className = "slot-section";  // 預設收合
      sec.dataset.i = i;

      // ── 標題列（點擊展開/收合）──
      const header = document.createElement("div");
      header.className = "slot-header";
      header.innerHTML = `
        <span class="player-num">玩家 ${slot.player_index + 1}</span>
        <div class="slot-header-badges">
          <button class="slot-toggle av-toggle" data-i="${i}" title="切換頭像">
            ${slot.avatar.enabled ? "頭像 ✓" : "頭像 ○"}
          </button>
          <button class="slot-toggle lb-toggle" data-i="${i}" title="切換名字">
            ${slot.label.enabled ? "名字 ✓" : "名字 ○"}
          </button>
          <button class="slot-toggle dt-toggle" data-i="${i}" title="切換入職日">
            ${slot.date.enabled ? "入職日 ✓" : "入職日 ○"}
          </button>
        </div>
        <span class="slot-chevron">▼</span>
      `;
      sec.appendChild(header);

      // ── 展開內容 ──
      const body = document.createElement("div");
      body.className = "slot-body";

      // 圖片框 X/Y/W/H
      const imgGrid = document.createElement("div");
      imgGrid.className = "form-grid";
      imgGrid.style.gridTemplateColumns = "20px 1fr 20px 1fr";
      imgGrid.innerHTML = `
        <span>X</span><input type="number" class="slot-x" data-i="${i}" value="${slot.x}" />
        <span>Y</span><input type="number" class="slot-y" data-i="${i}" value="${slot.y}" />
        <span>寬</span><input type="number" class="slot-w" data-i="${i}" value="${slot.width}" />
        <span>高</span><input type="number" class="slot-h" data-i="${i}" value="${slot.height}" />
      `;
      body.appendChild(imgGrid);

      // 頭像設定
      const avSub = document.createElement("div");
      avSub.className = "slot-sub";
      avSub.id = `av-sub-${i}`;
      avSub.style.display = slot.avatar.enabled ? "" : "none";
      avSub.innerHTML = `
        <div class="slot-sub-title">🖼 頭像</div>
        <div class="slot-avatar-upload">
          <img class="avatar-thumb" id="av-thumb-${i}"
               src="${this._avatarUrl(i)}"
               onerror="this.style.display='none'" />
          <label class="btn-secondary" style="padding:3px 8px;font-size:11px;cursor:pointer">
            上傳
            <input type="file" accept="image/*" class="av-upload" data-i="${i}" style="display:none" />
          </label>
        </div>
        <div class="form-grid" style="grid-template-columns:30px 1fr 30px 1fr">
          <span>X</span><input type="number" class="av-x" data-i="${i}" value="${slot.avatar.x}" />
          <span>Y</span><input type="number" class="av-y" data-i="${i}" value="${slot.avatar.y}" />
          <span>高</span><input type="number" class="av-h" data-i="${i}" value="${slot.avatar.height}" />
          <span>背景色</span><input type="color" class="av-bg" data-i="${i}"
            value="${slot.avatar.bg_color || "#000000"}"
            style="width:44px;height:28px" />
        </div>
        <div class="av-width-info" style="margin-top:4px;font-size:11px;color:var(--text-muted)">
          寬度依比例自動計算（目前：${slot.avatar.width}px）
        </div>
        <div style="margin-top:4px">
          <label style="font-size:11px;color:var(--text-muted)">
            <input type="checkbox" class="av-transparent" data-i="${i}"
              ${!slot.avatar.bg_color ? "checked" : ""} style="width:auto" />
            背景透明
          </label>
        </div>
      `;
      body.appendChild(avSub);

      // 名字設定（可收合）
      const lbSub = document.createElement("div");
      lbSub.className = "slot-sub slot-collapsible";
      lbSub.id = `lb-sub-${i}`;
      lbSub.style.display = slot.label.enabled ? "" : "none";
      lbSub.innerHTML = `
        <div class="slot-sub-title slot-sub-toggle" data-target="lb-body-${i}">
          🔤 名字 <span class="sub-chevron">▶</span>
        </div>
        <div class="slot-sub-body" id="lb-body-${i}" style="display:none">
          <div class="form-grid" style="grid-template-columns:30px 1fr 30px 1fr;margin-top:4px">
            <span>X</span><input type="number" class="lb-x" data-i="${i}" value="${slot.label.x}" />
            <span>Y</span><input type="number" class="lb-y" data-i="${i}" value="${slot.label.y}" />
            <span>W</span><input type="number" class="lb-w" data-i="${i}" value="${slot.label.width}" />
            <span>H</span><input type="number" class="lb-h" data-i="${i}" value="${slot.label.height}" />
          </div>
          <div class="form-grid" style="margin-top:4px">
            <span>名字</span>
            <input type="text" class="lb-text" data-i="${i}" value="${slot.label.text}" placeholder="玩家名字" />
          </div>
          <div style="margin-top:4px">
            <label style="font-size:11px;color:var(--text-muted)">
              <input type="checkbox" class="lb-transparent" data-i="${i}"
                ${!slot.label.bg_color ? "checked" : ""} style="width:auto" />
              背景透明
            </label>
            <input type="color" class="lb-bg" data-i="${i}"
              value="${slot.label.bg_color || "#000000"}"
              style="width:44px;height:28px;margin-left:8px;${!slot.label.bg_color ? "display:none" : ""}" />
          </div>
        </div>
      `;
      body.appendChild(lbSub);

      // 入職日設定（可收合）
      const dtSub = document.createElement("div");
      dtSub.className = "slot-sub slot-collapsible";
      dtSub.id = `dt-sub-${i}`;
      dtSub.style.display = slot.date.enabled ? "" : "none";
      dtSub.innerHTML = `
        <div class="slot-sub-title slot-sub-toggle" data-target="dt-body-${i}">
          📅 入職日 <span class="sub-chevron">▶</span>
        </div>
        <div class="slot-sub-body" id="dt-body-${i}" style="display:none">
          <div class="form-grid" style="grid-template-columns:30px 1fr 30px 1fr;margin-top:4px">
            <span>X</span><input type="number" class="dt-x" data-i="${i}" value="${slot.date.x}" />
            <span>Y</span><input type="number" class="dt-y" data-i="${i}" value="${slot.date.y}" />
          </div>
          <div class="form-grid" style="margin-top:4px">
            <span>日期</span>
            <input type="text" class="dt-text" data-i="${i}" value="${slot.date.date_text}"
              placeholder="2024-01-15" />
          </div>
        </div>
      `;
      body.appendChild(dtSub);

      sec.appendChild(body);
      if (openSet.has(i)) sec.classList.add("open");
      this.dom.slotInputs.appendChild(sec);
    });

    this._bindSlotEvents();
    this._bindSyncButton();
    this._refreshAvatarThumbs();
  }

  // ── 綁定所有 slot 事件 ────────────────────────
  _bindSlotEvents() {
    const { layout } = this.state;

    // accordion 展開/收合（點 header，但不含 toggle 按鈕）
    this.dom.slotInputs.querySelectorAll(".slot-header").forEach((header) => {
      header.addEventListener("click", (e) => {
        if (e.target.closest(".slot-toggle")) return;  // toggle 按鈕不觸發展開
        const sec = header.closest(".slot-section");
        sec.classList.toggle("open");
      });
    });

    // 名字框 / 入職日框子區塊收合
    this.dom.slotInputs.querySelectorAll(".slot-sub-toggle").forEach((title) => {
      title.addEventListener("click", () => {
        const bodyId = title.dataset.target;
        const body = document.getElementById(bodyId);
        const chevron = title.querySelector(".sub-chevron");
        if (!body) return;
        const isOpen = body.style.display !== "none";
        body.style.display = isOpen ? "none" : "";
        if (chevron) chevron.textContent = isOpen ? "▶" : "▼";
      });
    });

    // 頭像/名字 toggle（切換 enabled，重新 render；展開狀態由 renderSlotInputs 自動還原）
    this.dom.slotInputs.querySelectorAll(".av-toggle").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const i = parseInt(btn.dataset.i);
        layout.image_slots[i].avatar.enabled = !layout.image_slots[i].avatar.enabled;
        this.renderSlotInputs();
        this.renderDragBoxes();
        this._triggerAutoSave();
      });
    });
    this.dom.slotInputs.querySelectorAll(".lb-toggle").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const i = parseInt(btn.dataset.i);
        layout.image_slots[i].label.enabled = !layout.image_slots[i].label.enabled;
        this.renderSlotInputs();
        this.renderDragBoxes();
        this._triggerAutoSave();
      });
    });
    this.dom.slotInputs.querySelectorAll(".dt-toggle").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const i = parseInt(btn.dataset.i);
        layout.image_slots[i].date.enabled = !layout.image_slots[i].date.enabled;
        this.renderSlotInputs();
        this.renderDragBoxes();
        this._triggerAutoSave();
      });
    });

    // 頭像上傳
    this.dom.slotInputs.querySelectorAll(".av-upload").forEach((input) => {
      input.addEventListener("change", async () => {
        const i = parseInt(input.dataset.i);
        const file = input.files[0];
        if (!file) return;
        const formData = new FormData();
        formData.append("file", file);
        const res = await fetch(`/api/upload/avatar/${i}`, { method: "POST", body: formData });
        const data = await res.json();
        if (data.ok) {
          const thumb = document.getElementById(`av-thumb-${i}`);
          if (thumb) {
            thumb.src = data.url + "?t=" + Date.now();
            thumb.style.display = "";
          }
          // 根據圖片實際比例更新 avatar.width/height（保持目前高度，等比例算寬度）
          if (data.img_w && data.img_h) {
            const slot = this.state.layout?.image_slots[i];
            if (slot) {
              const curH = slot.avatar.height || 60;
              slot.avatar.width  = Math.round(curH * data.img_w / data.img_h);
              slot.avatar.height = curH;
              // 更新顯示文字
              const info = document.querySelector(`#av-sub-${i} .av-width-info`);
              if (info) info.textContent = `寬度依比例自動計算（目前：${slot.avatar.width}px）`;
              this.renderDragBoxes();
              this._triggerAutoSave();
            }
          }
        }
      });
    });

    // 頭像透明勾選
    this.dom.slotInputs.querySelectorAll(".av-transparent").forEach((cb) => {
      cb.addEventListener("change", () => {
        const i = parseInt(cb.dataset.i);
        layout.image_slots[i].avatar.bg_color = cb.checked ? "" : "#000000";
        this.collectSlotInputs();
        this._triggerAutoSave();
      });
    });

    // 名字背景透明勾選
    this.dom.slotInputs.querySelectorAll(".lb-transparent").forEach((cb) => {
      cb.addEventListener("change", () => {
        const i = parseInt(cb.dataset.i);
        const bgInput = document.querySelector(`.lb-bg[data-i="${i}"]`);
        layout.image_slots[i].label.bg_color = cb.checked ? "" : "#000000";
        if (bgInput) bgInput.style.display = cb.checked ? "none" : "";
        this.collectSlotInputs();
        this._triggerAutoSave();
      });
    });

    // 所有數值輸入
    this.dom.slotInputs.querySelectorAll("input[type=number], input[type=text], input[type=color], select").forEach((el) => {
      const evt = el.tagName === "SELECT" ? "change" : "input";
      el.addEventListener(evt, () => {
        const i = parseInt(el.dataset.i);
        // 角色框等比例鎖定
        if (this._lockRatio && el.classList.contains("slot-w")) {
          const newW = parseInt(el.value);
          if (!newW) return;
          const baseW = this._baseSlotW?.[i] || newW;
          const baseH = this._baseSlotH?.[i] || 1;
          const ratio = baseH / baseW;
          const hEl = document.querySelector(`.slot-h[data-i="${i}"]`);
          if (hEl) hEl.value = Math.round(newW * ratio);
        } else if (this._lockRatio && el.classList.contains("slot-h")) {
          const newH = parseInt(el.value);
          if (!newH) return;
          const baseW = this._baseSlotW?.[i] || 1;
          const baseH = this._baseSlotH?.[i] || newH;
          const ratio = baseW / baseH;
          const wEl = document.querySelector(`.slot-w[data-i="${i}"]`);
          if (wEl) wEl.value = Math.round(newH * ratio);
        }
        // 頭像框：改高度時等比例算寬度（必須在 collectSlotInputs 之前執行）
        if (el.classList.contains("av-h")) {
          const newH = parseInt(el.value);
          if (newH > 0) {
            const slot = this.state.layout?.image_slots[i];
            if (slot && slot.avatar.height > 0) {
              const oldH = slot.avatar.height;
              const oldW = slot.avatar.width;
              slot.avatar.width  = Math.round(newH * oldW / oldH);
              slot.avatar.height = newH;   // 先更新 height，collectSlotInputs 不會再覆蓋 width
              const info = document.querySelector(`#av-sub-${i} .av-width-info`);
              if (info) info.textContent = `寬度依比例自動計算（目前：${slot.avatar.width}px）`;
            }
          }
        }
        this.collectSlotInputs();
        this.renderDragBoxes();
        this._triggerAutoSave();
      });
    });
  }

  // ── 同步按鈕 ─────────────────────────────────
  _bindSyncButton() {
    const btn = document.getElementById("btn-sync");
    if (btn) btn.onclick = () => this._applySyncSlot();

    const btnSub = document.getElementById("btn-sync-sub");
    if (btnSub) btnSub.onclick = () => this._applySyncSub();
  }

  // 同步角色框大小 / 位置
  _applySyncSlot() {
    const { layout } = this.state;
    if (layout.image_slots.length < 2) return;

    const syncSize   = document.getElementById("sync-size")?.checked;
    const syncAlignX = document.getElementById("sync-align-x")?.checked;
    const syncAlignY = document.getElementById("sync-align-y")?.checked;

    const p1 = layout.image_slots[0];
    layout.image_slots.slice(1).forEach((slot) => {
      if (syncSize)   { slot.width = p1.width; slot.height = p1.height; }
      if (syncAlignX) slot.x = p1.x;
      if (syncAlignY) slot.y = p1.y;
    });

    this.renderSlotInputs();
    this.renderDragBoxes();
    this._triggerAutoSave();
  }

  // 同步頭像框 / 名字框的相對位置、大小、enabled（各自圖片與名字文字保留）
  _applySyncSub() {
    const { layout } = this.state;
    if (layout.image_slots.length < 2) return;

    const p1 = layout.image_slots[0];
    layout.image_slots.slice(1).forEach((slot) => {
      // 頭像框：同步相對位置、大小、樣式
      const avRelX = p1.avatar.x - p1.x;
      const avRelY = p1.avatar.y - p1.y;
      slot.avatar.x        = slot.x + avRelX;
      slot.avatar.y        = slot.y + avRelY;
      slot.avatar.size     = p1.avatar.size;
      slot.avatar.bg_color = p1.avatar.bg_color;
      slot.avatar.enabled  = p1.avatar.enabled;

      // 名字框：同步相對位置、大小、背景色、enabled（保留各自名字文字）
      const lbRelX = p1.label.x - p1.x;
      const lbRelY = p1.label.y - p1.y;
      const savedText    = slot.label.text;
      slot.label.x       = slot.x + lbRelX;
      slot.label.y       = slot.y + lbRelY;
      slot.label.width   = p1.label.width;
      slot.label.height  = p1.label.height;
      slot.label.bg_color= p1.label.bg_color;
      slot.label.enabled = p1.label.enabled;
      slot.label.text    = savedText;

      // 入職日框：同步相對位置、大小、enabled（保留各自日期文字）
      const dtRelX = p1.date.x - p1.x;
      const dtRelY = p1.date.y - p1.y;
      const savedDate    = slot.date.date_text;
      slot.date.x        = slot.x + dtRelX;
      slot.date.y        = slot.y + dtRelY;
      slot.date.width    = p1.date.width;
      slot.date.height   = p1.date.height;
      slot.date.enabled  = p1.date.enabled;
      slot.date.date_text = savedDate;
    });

    this.renderSlotInputs();
    this.renderDragBoxes();
    this._triggerAutoSave();
  }

  // ── 收集所有 slot 數值 ────────────────────────
  collectSlotInputs() {
    const { layout } = this.state;
    if (!layout) return;
    layout.image_slots.forEach((slot, i) => {
      const v = (cls) => {
        const el = document.querySelector(`.${cls}[data-i="${i}"]`);
        return el ? el.value : null;
      };
      const vi = (cls) => parseInt(v(cls)) || 0;

      if (v("slot-x") !== null) slot.x = vi("slot-x");
      if (v("slot-y") !== null) slot.y = vi("slot-y");
      if (v("slot-w") !== null) slot.width  = parseInt(v("slot-w")) || 200;
      if (v("slot-h") !== null) slot.height = parseInt(v("slot-h")) || 400;

      // avatar（寬度由 _bindSlotEvents av-h 分支維護，這裡直接讀已算好的值）
      if (v("av-x") !== null) {
        slot.avatar.x      = vi("av-x");
        slot.avatar.y      = vi("av-y");
        slot.avatar.height = parseInt(v("av-h")) || slot.avatar.height;
        // width 已由 _bindSlotEvents 等比例算好，不在此覆蓋
        const avTrans = document.querySelector(`.av-transparent[data-i="${i}"]`);
        slot.avatar.bg_color = avTrans?.checked ? "" : (v("av-bg") || "");
      }

      // label
      if (v("lb-x") !== null) {
        slot.label.x      = vi("lb-x");
        slot.label.y      = vi("lb-y");
        slot.label.width  = parseInt(v("lb-w")) || 200;
        slot.label.height = parseInt(v("lb-h")) || 40;
        slot.label.text   = v("lb-text") || "";
        const lbTrans = document.querySelector(`.lb-transparent[data-i="${i}"]`);
        slot.label.bg_color = lbTrans?.checked ? "" : (v("lb-bg") || "");
      }

      // date（width/height 為全局，不在此讀取）
      if (v("dt-x") !== null) {
        slot.date.x         = vi("dt-x");
        slot.date.y         = vi("dt-y");
        slot.date.date_text = v("dt-text") || "";
      }
    });
  }

  // ── 拖拉覆蓋層 ───────────────────────────────
  renderDragBoxes() {
    const { layout } = this.state;
    if (!layout) return;

    this.dom.dragOverlay.innerHTML = "";
    this._updateScale();
    const s = this._scale;

    // 標題框（只在啟用時顯示）
    if (layout.title_enabled !== false) {
      this._createDragBox({
        label: "標題",
        x: layout.title.x * s, y: layout.title.y * s,
        w: layout.title.width * s, h: layout.title.height * s,
        className: "drag-box title-box",
        onMove: (dx, dy) => {
          layout.title.x = Math.round(layout.title.x + dx / s);
          layout.title.y = Math.round(layout.title.y + dy / s);
          this.onChanged(); this.renderDragBoxes(); this._triggerAutoSave();
        },
      });
    }

    // 圖片框 + 頭像框 + 名字框
    layout.image_slots.forEach((slot) => {
      // 圖片框
      this._createDragBox({
        label: `P${slot.player_index + 1}`,
        x: slot.x * s, y: slot.y * s,
        w: slot.width * s, h: slot.height * s,
        className: "drag-box",
        onMove: (dx, dy) => {
          slot.x = Math.round(slot.x + dx / s);
          slot.y = Math.round(slot.y + dy / s);
          this.onChanged(); this.renderDragBoxes(); this._triggerAutoSave();
        },
      });

      // 頭像框
      if (slot.avatar.enabled) {
        this._createDragBox({
          label: `A${slot.player_index + 1}`,
          x: slot.avatar.x * s, y: slot.avatar.y * s,
          w: slot.avatar.width * s, h: slot.avatar.height * s,
          className: "drag-box avatar-box",
          onMove: (dx, dy) => {
            slot.avatar.x = Math.round(slot.avatar.x + dx / s);
            slot.avatar.y = Math.round(slot.avatar.y + dy / s);
            this._syncFormFromSlot(layout.image_slots.indexOf(slot));
            this.renderDragBoxes(); this._triggerAutoSave();
          },
        });
      }

      // 名字框
      if (slot.label.enabled) {
        this._createDragBox({
          label: `L${slot.player_index + 1}`,
          x: slot.label.x * s, y: slot.label.y * s,
          w: slot.label.width * s, h: slot.label.height * s,
          className: "drag-box label-box",
          onMove: (dx, dy) => {
            slot.label.x = Math.round(slot.label.x + dx / s);
            slot.label.y = Math.round(slot.label.y + dy / s);
            this._syncFormFromSlot(layout.image_slots.indexOf(slot));
            this.renderDragBoxes(); this._triggerAutoSave();
          },
        });
      }

      // 入職日框
      if (slot.date.enabled) {
        const dw = layout.date_width || 260;
        const dh = layout.date_height || 36;
        this._createDragBox({
          label: `D${slot.player_index + 1}`,
          x: slot.date.x * s, y: slot.date.y * s,
          w: dw * s, h: dh * s,
          className: "drag-box date-box",
          onMove: (dx, dy) => {
            slot.date.x = Math.round(slot.date.x + dx / s);
            slot.date.y = Math.round(slot.date.y + dy / s);
            this._syncFormFromSlot(layout.image_slots.indexOf(slot));
            this.renderDragBoxes(); this._triggerAutoSave();
          },
        });
      }
    });
  }

  // 拖拉後同步數值到表單
  _syncFormFromSlot(i) {
    const slot = this.state.layout?.image_slots[i];
    if (!slot) return;
    const set = (cls, val) => {
      const el = document.querySelector(`.${cls}[data-i="${i}"]`);
      if (el) el.value = val;
    };
    set("slot-x", slot.x); set("slot-y", slot.y);
    set("av-x", slot.avatar.x); set("av-y", slot.avatar.y);
    set("lb-x", slot.label.x);  set("lb-y", slot.label.y);
    set("dt-x", slot.date.x);   set("dt-y", slot.date.y);
    this.onChanged();
  }

  _createDragBox({ label, x, y, w, h, className, onMove }) {
    const box = document.createElement("div");
    box.className = className;
    box.textContent = label;

    // 計算圖片相對於 drag-overlay（兩者都在 preview-wrapper 內）的偏移
    // 用 offsetLeft/offsetTop 避免 getBoundingClientRect 受 scroll 影響
    const img = this.dom.previewImg;
    const wrapper = this.dom.previewWrapper;
    // img 的 offsetParent 是 wrapper（因為 wrapper 是 position:relative 的祖先）
    const offsetX = img.offsetLeft - wrapper.scrollLeft;
    const offsetY = img.offsetTop  - wrapper.scrollTop;

    box.style.left   = `${offsetX + x}px`;
    box.style.top    = `${offsetY + y}px`;
    box.style.width  = `${Math.max(w, 8)}px`;
    box.style.height = `${Math.max(h, 8)}px`;

    let startX, startY;
    box.addEventListener("mousedown", (e) => {
      e.preventDefault();
      startX = e.clientX; startY = e.clientY;
      const onMove_ = (e2) => {
        const dx = e2.clientX - startX;
        const dy = e2.clientY - startY;
        startX = e2.clientX; startY = e2.clientY;
        onMove(dx, dy);
      };
      const onUp = () => {
        document.removeEventListener("mousemove", onMove_);
        document.removeEventListener("mouseup", onUp);
      };
      document.addEventListener("mousemove", onMove_);
      document.addEventListener("mouseup", onUp);
    });

    this.dom.dragOverlay.appendChild(box);
  }

  _updateScale() {
    const { layout } = this.state;
    if (!layout) { this._scale = 1; return; }
    const img = this.dom.previewImg;
    if (!img.naturalWidth || img.style.display === "none") { this._scale = 1; return; }
    this._scale = img.clientWidth / layout.canvas.width;
  }

  _avatarUrl(i) {
    // 回傳空字串讓 img 不發出請求；上傳後由事件處理器填入實際 URL
    return "";
  }

  async _refreshAvatarThumbs() {
    const layout = this.state.layout;
    if (!layout) return;
    const count = layout.image_slots.length;
    try {
      const res = await fetch(`/api/uploads/status?player_count=${count}`);
      const data = await res.json();
      if (!data.ok) return;
      const ts = Date.now();
      data.avatars.forEach((exists, i) => {
        const slot = layout.image_slots[i];
        if (!slot || !slot.avatar.enabled) return;
        const thumb = document.getElementById(`av-thumb-${i}`);
        if (!thumb) return;
        if (exists) {
          thumb.src = `/static/uploads/avatar_${i}.png?t=${ts}`;
          thumb.style.display = "";
        } else {
          thumb.src = "";
          thumb.style.display = "none";
        }
      });
    } catch (e) {
      // 靜默失敗
    }
  }
}
