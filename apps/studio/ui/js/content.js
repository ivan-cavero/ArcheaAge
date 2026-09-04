import { $, el, emit, on, state } from "./state.js";

export function renderContent() {
  const root = $("#content");
  root.replaceChildren();
  root.append(el("div", { class: "tgroup", text: "Worlds" }));

  const worlds = state.catalog.worlds || [];
  if (!worlds.length) {
    root.append(
      el("div", { class: "kv", text: "No worlds.json catalog." }),
    );
    return;
  }

  for (const w of worlds) {
    const open = state.world.id === w.id;
    const row = el("div", { class: "citem" + (open ? " sel" : "") });
    row.append(
      el("span", { class: "cdot" }),
      el("span", { text: w.label || w.id }),
    );
    row.onclick = () => emit("open-world", w.id);
    root.append(row);
    if (open) {
      for (const cell of w.cells || []) {
        const cr = el("div", {
          class:
            "citem" +
            (state.world.cells.some((c) => c.id === cell) ? " sel" : ""),
          style: "padding-left:28px",
        });
        cr.append(el("span", { text: cell }));
        cr.onclick = (ev) => {
          ev.stopPropagation();
          emit("open-cell", { world: w.id, cell });
        };
        root.append(cr);
      }
    }
  }

  root.append(el("div", { class: "tgroup", text: "Pak" }));
  root.append(
    el("div", {
      class: "kv",
      text: "Live game_pak browser comes after the pak library is wired into the editor. Cells load from ui/cells/ for now.",
    }),
  );

  /* Named regions (Nuia / Epherus / Sea / Open Sea) straight from the client's
   * zone_groups — clicking flies the camera there and streaming loads the
   * baked cells around it. This is how you reach Haranya, Aurora, the sea
   * islands, etc. without hunting cell ids by hand. */
  const regions = state.catalog.regions || [];
  if (regions.length) {
    const byCont = {};
    for (const r of regions) (byCont[r.continent] || (byCont[r.continent] = [])).push(r);
    const order = ["Nuia", "Epherus", "Sea/Islands", "Open Sea", "Other"];
    for (const cont of order) {
      const list = byCont[cont];
      if (!list || !list.length) continue;
      root.append(el("div", { class: "tgroup", text: cont + " (" + list.length + ")" }));
      list.sort((a, b) => b.cells.length - a.cells.length);
      for (const r of list) {
        const row = el("div", { class: "citem" });
        const badge = r.cells.length ? r.cells.length + "⬚" : "—";
        row.append(
          el("span", { class: "cdot" }),
          el("span", { text: r.label }),
          el("span", {
            style: "margin-left:auto;opacity:.55;font-size:11px",
            text: badge,
          }),
        );
        row.title = r.cells.length
          ? "Fly to " + r.label
          : r.label + " (not baked yet — shows ocean relief)";
        row.onclick = () => emit("goto-region", r);
        root.append(row);
      }
    }
  }
}

export function bindContent() {
  on("catalog", renderContent);
  on("world-loaded", renderContent);
  renderContent();
}
