/**
 * 預覽管理器 — 向後端請求預覽圖，載入後更新拖拉覆蓋層
 */
export class PreviewManager {
  constructor(state, dom, layoutEditor) {
    this.state = state;
    this.dom = dom;
    this.layoutEditor = layoutEditor;
  }

  async requestBlankPreview() {
    // 預覽空版面（無角色圖片，只顯示背景 + 框框位置）
    const { state } = this;
    try {
      const res = await fetch("/api/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          base_dir: state.baseDir || "",
          player_folders: state.playerFolders.length > 0 ? state.playerFolders : ["_"],
          file_stem: "__blank__",
          display_name: "預覽",
        }),
      });
      if (!res.ok) return;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      if (this.dom.previewImg.src.startsWith("blob:")) URL.revokeObjectURL(this.dom.previewImg.src);
      this.dom.previewImg.onload = () => this.layoutEditor.renderDragBoxes();
      this.dom.previewPlaceholder.style.display = "none";
      this.dom.previewImg.style.display = "block";
      this.dom.previewImg.src = url;
    } catch (e) {
      console.error("空版面預覽失敗", e);
    }
  }

  async requestPreview() {
    const { state, dom } = this;
    const char = state.characters[state.selectedCharIndex];
    if (!char) return;

    try {
      // 自訂角色（全缺圖）傳 __blank__ 讓後端全部用缺圖預設
      const file_stem = char._custom ? "__blank__" : char.file_stem;
      const res = await fetch("/api/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          base_dir: state.baseDir,
          player_folders: state.playerFolders,
          file_stem: file_stem,
          display_name: char.display_name,
        }),
      });

      if (!res.ok) {
        console.error("預覽失敗", res.status);
        return;
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);

      if (dom.previewImg.src.startsWith("blob:")) {
        URL.revokeObjectURL(dom.previewImg.src);
      }

      dom.previewImg.onload = () => {
        this.layoutEditor.renderDragBoxes();
      };

      dom.previewPlaceholder.style.display = "none";
      dom.previewImg.style.display = "block";
      dom.previewImg.src = url;
    } catch (e) {
      console.error("預覽請求失敗", e);
    }
  }
}
