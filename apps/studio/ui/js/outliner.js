import { $, el, emit, isVolumeClass, on, state } from "./state.js";

function iconFor(kind, cls) {
  if (kind === "terrain") return "▣";
  if (kind === "water") return "≈";
  const c = (cls || "").toLowerCase();
  if (c.includes("light")) return "☀";
  if (c.includes("particle")) return "✦";
  if (c.includes("fish")) return "❯";
  if (isVolumeClass(cls)) return "◻";
  return "●";
}

function groupEntities(entities) {
  const groups = new Map();
  for (const e of entities || []) {
    const cls = e.class || "Entity";
    if (!groups.has(cls)) groups.set(cls, []);
    groups.get(cls).push(e);
  }
  return [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]));
}

export function renderOutliner() {
  const root = $("#outliner");
  root.replaceChildren();

  if (state.mode === "ui") {
    root.append(el("div", { class: "tgroup", text: "Screens" }));
    for (const name of state.ui.order) {
      const scr = state.ui.screens[name];
      const head = el("div", {
        class: "tnode" + (state.ui.active === name && !state.ui.sel ? " sel" : ""),
      });
      head.append(
        el("span", { class: "tw", text: "▾" }),
        el("span", { text: name }),
        el("span", { class: "k", text: Object.keys(scr.windows).length + "w" }),
      );
      head.onclick = () => emit("ui-select-screen", name);
      root.append(head);
      for (const id of Object.keys(scr.windows).sort()) {
        const row = el("div", {
          class: "tnode" + (state.ui.sel === id ? " sel" : ""),
          style: "padding-left:28px",
        });
        row.append(el("span", { text: id }));
        row.onclick = (ev) => {
          ev.stopPropagation();
          emit("ui-select-widget", { screen: name, id });
        };
        root.append(row);
      }
    }
    if (!state.ui.order.length) {
      root.append(
        el("div", {
          class: "kv",
          text: "No UI tree loaded. game_ui_tree.json is optional.",
        }),
      );
    }
    return;
  }

  const worldId = state.world.id || "world";
  root.append(el("div", { class: "tgroup", text: "World" }));
  const wrow = el("div", { class: "tnode" });
  wrow.append(
    el("span", { class: "tw", text: "▾" }),
    el("span", { text: worldId }),
    el("span", { class: "k", text: state.world.cells.length + " cells" }),
  );
  root.append(wrow);

  if (!state.world.cells.length) {
    root.append(
      el("div", {
        class: "kv",
        text: "No cells loaded. Export with tools/world/world_to_json.py",
      }),
    );
    return;
  }

  for (const cell of state.world.cells) {
    const open = true;
    const ents = (cell.data.entities || []).filter((e) => e.name || e.class);
    const crow = el("div", { class: "tnode", style: "padding-left:16px" });
    crow.append(
      el("span", { class: "tw", text: open ? "▾" : "▸" }),
      el("span", { text: cell.id }),
      el("span", { class: "k", text: String(ents.length) }),
    );
    crow.onclick = () => emit("select-cell", cell.id);
    root.append(crow);

    const trow = el("div", {
      class:
        "tnode" +
        (state.selected?.kind === "terrain" && state.selected?.cellId === cell.id
          ? " sel"
          : ""),
      style: "padding-left:32px",
    });
    trow.append(
      el("span", { text: iconFor("terrain") + "  Terrain" }),
    );
    trow.onclick = () => emit("select-terrain", cell.id);
    root.append(trow);

    const wtr = el("div", {
      class:
        "tnode" +
        (state.selected?.kind === "water" && state.selected?.cellId === cell.id
          ? " sel"
          : ""),
      style: "padding-left:32px",
    });
    wtr.append(el("span", { text: iconFor("water") + "  Water" }));
    wtr.onclick = () => emit("select-water", cell.id);
    root.append(wtr);

    for (const [cls, list] of groupEntities(ents)) {
      const vol = isVolumeClass(cls);
      const grow = el("div", {
        class: "tnode" + (vol && !state.showVolumes ? " hidden-row" : ""),
        style: "padding-left:32px",
      });
      grow.append(
        el("span", { class: "tw", text: "▾" }),
        el("span", { text: iconFor("entity", cls) + "  " + (cls || "Entity") }),
        el("span", { class: "k", text: String(list.length) }),
      );
      root.append(grow);
      if (vol && !state.showVolumes) continue;
      for (const ent of list) {
        const sel =
          state.selected?.kind === "entity" && state.selected?.entity === ent;
        const row = el("div", {
          class:
            "tnode" +
            (sel ? " sel" : "") +
            (vol && !state.showVolumes ? " hidden-row" : ""),
          style: "padding-left:48px",
          title: ent.model || "",
        });
        row.append(
          el("span", { text: ent.name || "(unnamed)" }),
        );
        row.onclick = () => emit("select-entity", { entity: ent, cellId: cell.id });
        root.append(row);
      }
    }
  }
}

export function bindOutliner() {
  on("world-loaded", renderOutliner);
  on("select", renderOutliner);
  on("mode", renderOutliner);
  on("view-flags", renderOutliner);
  on("ui-tree", renderOutliner);
  renderOutliner();
}
