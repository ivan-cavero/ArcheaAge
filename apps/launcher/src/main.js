// ArcheaAge Launcher — UI

// --- Window controls ---
async function setupWindowControls() {
  try {
    const { getCurrentWindow } = await import("@tauri-apps/api/window");
    const win = getCurrentWindow();
    const min = document.getElementById("win-min");
    const max = document.getElementById("win-max");
    const close = document.getElementById("win-close");
    if (min)
      min.addEventListener("click", (e) => {
        e.stopPropagation();
        win.minimize();
      });
    if (max)
      max.addEventListener("click", (e) => {
        e.stopPropagation();
        win.toggleMaximize();
      });
    if (close)
      close.addEventListener("click", (e) => {
        e.stopPropagation();
        win.close();
      });
  } catch {
    // Not in Tauri — window buttons do nothing in browser
  }
}

// --- Nav ---
document.querySelectorAll("#nav .nav-item").forEach((b) => {
  b.addEventListener("click", () => {
    document
      .querySelectorAll("#nav .nav-item")
      .forEach((n) => n.classList.remove("active"));
    b.classList.add("active");
  });
});

// --- Version chips ---
document.querySelectorAll(".v-chip:not(.disabled)").forEach((chip) => {
  chip.addEventListener("click", () => {
    document
      .querySelectorAll(".v-chip")
      .forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
  });
});

// --- Init ---
setupWindowControls();
