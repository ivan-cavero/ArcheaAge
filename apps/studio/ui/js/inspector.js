import { $, el, emit, on, state } from "./state.js";

function field(label, node) {
  const wrap = el("div");
  wrap.append(el("label", { text: label }), node);
  return wrap;
}

function num(id, val, step = 0.1) {
  return el("input", {
    type: "number",
    id,
    value: val ?? 0,
    step: String(step),
  });
}

function empty(title, msg) {
  return [
    el("div", { class: "h3", text: title }),
    el("p", { class: "kv", text: msg }),
  ];
}

export function renderInspector() {
  const root = $("#inspector");
  root.replaceChildren();

  if (state.mode === "ui") {
    emit("ui-inspector", root);
    return;
  }

  const sel = state.selected;
  if (!sel) {
    root.append(
      ...empty(
        "World",
        "Select terrain, water, or an entity in the viewport or outliner.",
      ),
    );
    const cell = state.world.cells[0];
    if (cell) {
      const hm = cell.data.heightmap || {};
      root.append(
        el("p", { class: "kv", text: "World: " + (state.world.id || "—") }),
        el("p", { class: "kv", text: "Cell: " + cell.id }),
        el("p", {
          class: "kv",
          text:
            "Size: " +
            (hm.width || 0) +
            " × " +
            (hm.width || 0) +
            " @ " +
            (hm.unit_size || 2) +
            " m",
        }),
        el("p", {
          class: "kv",
          text:
            "Entities: " +
            (cell.data.entities || []).filter((e) => e.name || e.class).length,
        }),
      );
    }
    return;
  }

  if (sel.kind === "brush") {
    root.append(el("div", { class: "h3", text: "Brush" }));
    root.append(el("p", { class: "kv", text: sel.model || "" }));
    root.append(el("p", { class: "kv", text: "Cell: " + sel.cellId }));
    return;
  }

  if (sel.kind === "npc" || sel.kind === "doodad") {
    const ent = sel.entity || {};
    root.append(el("div", { class: "h3", text: sel.kind === "npc" ? "NPC" : "Doodad" }));
    root.append(el("p", { class: "kv", text: "UnitId: " + (ent.unitId || sel.mesh?.userData?.unitId || "") }));
    if (ent.title) root.append(el("p", { class: "kv", text: ent.title }));
    root.append(el("p", { class: "kv", text: "Cell: " + sel.cellId }));
    if (ent.pos) {
      root.append(
        el("p", {
          class: "kv",
          text: "Pos: " + ent.pos.map((n) => Math.round(n)).join(", "),
        }),
      );
    }
    return;
  }

  if (sel.kind === "terrain" || sel.kind === "water") {
    const cell = state.world.cells.find((c) => c.id === sel.cellId);
    const hm = cell?.data.heightmap || {};
    root.append(el("div", { class: "h3", text: sel.kind === "water" ? "Water" : "Terrain" }));
    root.append(el("p", { class: "kv", text: "Cell " + sel.cellId }));
    if (hm.width) {
      root.append(
        el("p", { class: "kv", text: "Resolution: " + hm.width + "²" }),
        el("p", { class: "kv", text: "Unit size: " + hm.unit_size + " m" }),
        el("p", { class: "kv", text: "Water level: " + hm.water_level + " m" }),
      );
    }
    root.append(
      el("p", {
        class: "kv",
        text:
          "Splat textures from game_pak are not wired yet — ground uses a tiled albedo until the cell tile format is parsed.",
      }),
    );
    return;
  }

  const ent = sel.entity;
  if (!ent) {
    root.append(...empty("Inspector", "Nothing selected."));
    return;
  }
  const p = ent.pos || [0, 0, 0];
  const s = ent.scale || [1, 1, 1];
  root.append(el("div", { class: "h3", text: "Entity" }));
  root.append(el("p", { class: "kv", text: ent.name || "(unnamed)" }));
  root.append(el("p", { class: "kv", text: "Class: " + (ent.class || "—") }));
  root.append(el("p", { class: "kv", text: "Layer: " + (ent.layer || "—") }));
  root.append(el("p", { class: "kv", text: "Cell: " + sel.cellId }));

  root.append(field("Position X", num("ie_x", p[0])));
  root.append(field("Position Y", num("ie_y", p[1])));
  root.append(field("Position Z", num("ie_z", p[2])));
  root.append(field("Scale X", num("ie_sx", s[0])));
  root.append(field("Scale Y", num("ie_sy", s[1])));
  root.append(field("Scale Z", num("ie_sz", s[2])));

  const model = el("input", {
    type: "text",
    value: ent.model || "",
    disabled: "true",
  });
  root.append(field("Model", model));
  if (ent.model) {
    root.append(
      el("p", {
        class: "kv",
        text: "CryEngine .cgf/.chr/.cga loading is the next renderer milestone. Marker is a stand-in.",
      }),
    );
  }

  const apply = el("button", { class: "act primary", text: "Apply transform" });
  apply.onclick = () => {
    const g = (id) => document.getElementById(id);
    ent.pos = [+g("ie_x").value, +g("ie_y").value, +g("ie_z").value];
    ent.scale = [+g("ie_sx").value, +g("ie_sy").value, +g("ie_sz").value];
    emit("apply-entity", { entity: ent, cellId: sel.cellId });
  };
  root.append(apply);
}

export function bindInspector() {
  on("select", renderInspector);
  on("mode", renderInspector);
  on("world-loaded", renderInspector);
  on("entity-moved", renderInspector);
  on("ui-tree", renderInspector);
  renderInspector();
}
