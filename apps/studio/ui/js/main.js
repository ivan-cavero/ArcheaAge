import { bindContent } from "./content.js";
import { bindInspector } from "./inspector.js";
import { bindOutliner } from "./outliner.js";
import {
  $,
  cellOrigin,
  emit,
  on,
  setMode,
  setStatus,
  state,
  toWorldPos,
  winAction,
} from "./state.js";
import { bindUiMode } from "./ui-mode.js";
import { WorldViewport } from "./viewport.js";

function setLoad(msg) {
  const ov = $("#loadOverlay");
  const t = $("#loadMsg");
  if (!msg) {
    /* fade the veil out instead of snapping — hard world-load cuts looked broken */
    ov.classList.add("fading");
    setTimeout(() => {
      ov.hidden = true;
      ov.classList.remove("fading");
    }, 550);
    return;
  }
  t.textContent = msg;
  ov.hidden = false;
  ov.classList.remove("fading");
}

function applyMode() {
  const isWorld = state.mode === "world";
  $("#worldWrap").hidden = !isWorld;
  $("#uiWrap").hidden = isWorld;
  $("#gizmoBar").style.visibility = isWorld ? "visible" : "hidden";
  $("#camHint").style.visibility = isWorld ? "visible" : "hidden";
  for (const b of document.querySelectorAll("#modeBar [data-mode]")) {
    b.classList.toggle("on", b.dataset.mode === state.mode);
  }
  $("#hudHelp").textContent = isWorld
    ? "WASD fly · RMB look · Q/E up/down · Shift fast · Home overview"
    : "UI layout editor — native windows over a reconstructed screen";
  $("#viewHud").hidden = !isWorld;
  const mm = $("#minimapWrap");
  if (mm) mm.hidden = !isWorld;
  if (isWorld) WorldViewport.resize();
  else fitUiStage();
}

function fitUiStage() {
  const wrap = $("#uiWrap");
  const stage = $("#uiStage");
  if (!wrap || !stage) return;
  const s = Math.min(wrap.clientWidth / 1920, wrap.clientHeight / 1080);
  stage.style.transform = "scale(" + Math.max(0.1, s) + ")";
}

function bindChrome() {
  document.querySelectorAll("[data-win]").forEach((b) => {
    b.addEventListener("click", () => winAction(b.dataset.win));
  });
  document.querySelectorAll("[data-mode]").forEach((b) => {
    b.addEventListener("click", () => setMode(b.dataset.mode));
  });
  document.querySelectorAll("[data-gizmo]").forEach((b) => {
    b.addEventListener("click", () => emit("gizmo", b.dataset.gizmo));
  });
  document.querySelectorAll("[data-cmd]").forEach((b) => {
    b.addEventListener("click", () => emit("cmd", b.dataset.cmd));
  });

  $("#chkGrid").onchange = (e) => {
    state.showGrid = e.target.checked;
    emit("view-flags");
  };
  $("#chkWater").onchange = (e) => {
    state.showWater = e.target.checked;
    emit("view-flags");
  };
  $("#chkVolumes").onchange = (e) => {
    state.showVolumes = e.target.checked;
    emit("view-flags");
  };

  const ts = $("#timeSlider");
  const tl = $("#todLabel");
  const fmtTod = (h) => {
    const hh = Math.floor(h) % 24;
    const mm = Math.floor((h - Math.floor(h)) * 60);
    return String(hh).padStart(2, "0") + ":" + String(mm).padStart(2, "0");
  };
  const markTod = (h) => {
    document.querySelectorAll("#todPresets [data-tod]").forEach((b) => {
      b.classList.toggle("on", Math.abs(parseFloat(b.dataset.tod) - h) < 0.01);
    });
  };
  const setTod = (h) => {
    state.timeOfDay = h;
    if (ts) ts.value = String(h);
    if (tl) tl.textContent = fmtTod(h);
    markTod(h);
    emit("env");
  };
  if (ts) {
    ts.oninput = () => {
      state.timeOfDay = parseFloat(ts.value);
      if (tl) tl.textContent = fmtTod(state.timeOfDay);
      markTod(state.timeOfDay);
      emit("env");
    };
  }
  const ws = $("#weatherSel");
  if (ws) {
    ws.onchange = () => {
      state.weather = ws.value;
      emit("env");
    };
  }
  if (tl) tl.textContent = fmtTod(state.timeOfDay);
  markTod(state.timeOfDay);

  document.querySelectorAll("#todPresets [data-tod]").forEach((b) => {
    b.addEventListener("click", () => setTod(parseFloat(b.dataset.tod)));
  });

  const envBtn = $("#envToggle");
  const envFlyout = $("#envFlyout");
  const setFlyout = (open) => {
    if (!envBtn || !envFlyout) return;
    envFlyout.hidden = !open;
    envBtn.classList.toggle("on", open);
  };
  if (envBtn && envFlyout) {
    envBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      setFlyout(envFlyout.hidden);
    });
    document.addEventListener("click", (e) => {
      if (!envFlyout.hidden && !e.target.closest("#envWrap")) setFlyout(false);
    });
  }

  const legendBtn = $("#legendBtn");
  const legendOv = $("#legendOverlay");
  const setLegend = (open) => {
    if (!legendBtn || !legendOv) return;
    legendOv.hidden = !open;
    legendBtn.classList.toggle("on", open);
  };
  if (legendBtn && legendOv) {
    legendBtn.addEventListener("click", () => setLegend(legendOv.hidden));
  }

  const TOD_KEYS = { F5: 6, F6: 13, F7: 18, F8: 22 };
  window.addEventListener("keydown", (e) => {
    const tag = (e.target && e.target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (TOD_KEYS[e.key]) {
      e.preventDefault();
      setTod(TOD_KEYS[e.key]);
    } else if (e.key === "?") {
      e.preventDefault();
      setLegend(!!legendOv && legendOv.hidden);
    } else if (e.key === "Escape") {
      if (envFlyout && !envFlyout.hidden) setFlyout(false);
      if (legendOv && !legendOv.hidden) setLegend(false);
    }
  });

  on("gizmo", (mode) => {
    state.gizmo = mode;
    document.querySelectorAll("#gizmoBar [data-gizmo]").forEach((b) => {
      b.classList.toggle("on", b.dataset.gizmo === mode);
    });
  });
  on("view-flags", () => {
    $("#chkGrid").checked = state.showGrid;
    $("#chkWater").checked = state.showWater;
    $("#chkVolumes").checked = state.showVolumes;
  });
  on("mode", applyMode);
  on("status", (m) => {
    $("#statLeft").textContent = m || "Ready";
  });
  on("fps", (fps) => {
    $("#statRight").textContent = fps + " fps";
  });
  on("cam", (c) => {
    const loc = $("#hudLoc");
    if (loc) {
      loc.innerHTML =
        "Cell <b>" +
        c.cell +
        "</b><br>X " +
        Math.round(c.x) +
        " &nbsp; Y " +
        Math.round(c.y) +
        " &nbsp; alt " +
        Math.round(c.z) +
        " m";
    }
  });

  on("cmd", (cmd) => {
    if (cmd === "reload-world") loadDefaultWorld();
    if (cmd === "toggle-grid") {
      state.showGrid = !state.showGrid;
      emit("view-flags");
    }
    if (cmd === "toggle-water") {
      state.showWater = !state.showWater;
      emit("view-flags");
    }
    if (cmd === "toggle-volumes") {
      state.showVolumes = !state.showVolumes;
      emit("view-flags");
    }
    if (cmd === "frame" && state.selected?.mesh) WorldViewport.focus(state.selected.mesh);
    if (cmd === "overview") WorldViewport.overview();
    if (cmd === "mode-world") setMode("world");
    if (cmd === "mode-ui") setMode("ui");
  });

  bindSplitters();
}

function bindSplitters() {
  const left = $("#leftPane");
  const right = $("#rightPane");
  const content = $("#contentPanel");

  const drag = (el, onMove) => {
    el.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      el.setPointerCapture(e.pointerId);
      const move = (ev) => onMove(ev);
      const up = () => {
        el.releasePointerCapture(e.pointerId);
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", up);
      };
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", up);
    });
  };

  drag($("#splitLeftV"), (e) => {
    const x = e.clientX;
    left.style.width = Math.max(180, Math.min(480, x)) + "px";
    WorldViewport.resize();
    fitUiStage();
  });
  drag($("#splitRightV"), (e) => {
    const x = window.innerWidth - e.clientX;
    right.style.width = Math.max(200, Math.min(480, x)) + "px";
    WorldViewport.resize();
    fitUiStage();
  });
  drag($("#splitLeftH"), (e) => {
    const rect = left.getBoundingClientRect();
    const fromBottom = rect.bottom - e.clientY;
    content.style.height = Math.max(80, Math.min(rect.height - 100, fromBottom)) + "px";
  });
}

async function loadCatalog() {
  try {
    const r = await fetch("worlds.json");
    if (!r.ok) throw new Error("no catalog");
    state.catalog = await r.json();
    emit("catalog");
  } catch {
    state.catalog = {
      worlds: [{ id: "arche_mall_world", label: "Arche Mall", cells: ["003_003"] }],
    };
    emit("catalog");
  }
}

async function fetchJson(url) {
  try {
    const r = await fetch(url);
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

async function loadWorld(worldId, cellIds) {
  setLoad("Loading " + worldId + "…");
  WorldViewport.clearWorld();
  const man = await fetchJson("cache/manifest.json");
  if (man && man.terrain) await WorldViewport.setTerrainMaps(man.terrain);
  state.manifest = man || null;

  const ovName =
    (man && man.overview) ||
    (man &&
      (man.worlds || []).find((w) => w.id === worldId)?.overview) ||
    "overview_" + worldId + ".json";
  const overview = await fetchJson("cache/" + ovName);
  if (overview && overview.cells) {
    setLoad("Continent overview…");
    WorldViewport.loadOverview(overview);
  }

  const loaded = [];
  let brushes = 0;
  let veg = 0;
  let npcs = 0;
  for (const cellId of cellIds) {
    setLoad("Loading " + worldId + " / " + cellId + "…");
    const baked = await fetchJson(
      "cache/cells/" + worldId + "_" + cellId + "_objects.json",
    );
    let data = await fetchJson("cells/" + worldId + "_" + cellId + ".json");
    if (!data && baked && baked.heightmap) {
      data = {
        cell: cellId,
        heightmap: baked.heightmap,
        entities: baked.entities || [],
      };
    }
    if (!data) continue;
    const cover = await WorldViewport.loadCover(worldId, cellId);
    const cell = WorldViewport.loadCell(data, worldId, {
      fit: false,
      cover,
      skipEntities: !!(baked && (baked.objects || baked.entityMeshes)),
    });
    if (baked) {
      await WorldViewport.addBaked(baked, cellId);
      brushes += (baked.objects || []).length;
      veg += (baked.vegetation || []).length;
      npcs += (baked.npcs || []).length;
    }
    loaded.push({
      id: cell.cellId,
      origin: cell.origin,
      data,
    });
  }

  state.world = { id: worldId, cells: loaded };
  state.selected = null;
  if (loaded[0]) {
    WorldViewport.fitGround(loaded[0].origin, loaded[0].data.heightmap);
  } else if (overview) {
    WorldViewport.fitWorld();
  }
  $("#hudWorld").textContent =
    worldId.replace(/_/g, " ") + "  ·  " + loaded.length + " cells";
  $("#statMid").textContent =
    loaded.length +
    " cells  ·  " +
    brushes +
    " meshes  ·  " +
    veg +
    " veg  ·  " +
    npcs +
    " npc" +
    (overview ? "  ·  continent" : "");
  if (!loaded.length && !overview) {
    setStatus(
      "No cell data — run tools/world/bake_studio.py or world_to_json.py",
    );
  } else {
    setStatus(
      "Loaded " +
        worldId +
        " (" +
        loaded.length +
        " cells, " +
        veg +
        " plants, " +
        npcs +
        " NPCs)",
    );
  }
  setLoad(null);
  emit("world-loaded");
  emit("select", null);
}

async function loadDefaultWorld() {
  const worlds = state.catalog.worlds || [];
  for (const w of worlds) {
    const probe = await fetchJson(
      "cache/cells/" + w.id + "_" + w.cells[0] + "_objects.json",
    );
    if (probe) {
      /* seed only a 3×3 block around the region centre and let streaming load
       * the rest — loading all ~200 baked cells up front stalls the boot. */
      await loadWorld(w.id, seedCells(w.cells));
      return;
    }
  }
  if (worlds[0]) await loadWorld(worlds[0].id, seedCells(worlds[0].cells));
  else setStatus("No worlds in catalog");
}

/* pick a compact seed block (3×3) near the middle of the available cells */
function seedCells(cells) {
  if (!cells || !cells.length) return [];
  const parsed = cells.map((id) => {
    const m = String(id).match(/(\d+)_(\d+)/);
    return m ? [Number(m[1]), Number(m[2])] : [0, 0];
  });
  const mx = Math.round(parsed.reduce((a, p) => a + p[0], 0) / parsed.length);
  const my = Math.round(parsed.reduce((a, p) => a + p[1], 0) / parsed.length);
  const fmt = (x, y) =>
    String(Math.max(0, x)).padStart(3, "0") + "_" + String(Math.max(0, y)).padStart(3, "0");
  const seed = [];
  for (let dx = -1; dx <= 1; dx++)
    for (let dy = -1; dy <= 1; dy++) {
      const id = fmt(mx + dx, my + dy);
      if (cells.includes(id)) seed.push(id);
    }
  return seed.length ? seed : cells.slice(0, 4);
}

function bindWorldEvents() {
  /* dynamic streaming with a radius: keep a 3×3 (extensible) block of baked
   * cells around the camera loaded, and unload far ones to bound memory */
  const loadedCells = new Set();
  const streamBusy = new Set();
  const RADIUS = 1;
  const KEEP = 2;
  let lastCell = "";

  const parseId = (id) => {
    const m = String(id).match(/(\d+)_(\d+)/);
    return m ? [Number(m[1]), Number(m[2])] : [0, 0];
  };
  const fmt = (x, y) =>
    String(Math.max(0, x)).padStart(3, "0") + "_" + String(Math.max(0, y)).padStart(3, "0");

  async function ensureCell(worldId, cellId) {
    if (loadedCells.has(cellId) || streamBusy.has(cellId)) return;
    const man = state.manifest;
    if (!man) return;
    const w = (man.worlds || []).find((x) => x.id === worldId);
    const known = new Set((w?.cells || man.cells || []).map((x) => x.id));
    if (!known.has(cellId)) return;
    streamBusy.add(cellId);
    try {
      const baked = await fetchJson("cache/cells/" + worldId + "_" + cellId + "_objects.json");
      if (!baked) return;
      let data = await fetchJson("cells/" + worldId + "_" + cellId + ".json");
      if (!data && baked.heightmap) {
        data = { cell: cellId, heightmap: baked.heightmap, entities: baked.entities || [] };
      }
      if (!data) return;
      const cover = await WorldViewport.loadCover(worldId, cellId);
      const cellObj = WorldViewport.loadCell(data, worldId, {
        fit: false,
        cover,
        skipEntities: !!(baked.objects || baked.entityMeshes),
      });
      await WorldViewport.addBaked(baked, cellId);
      state.world.cells.push({ id: cellObj.cellId, origin: cellObj.origin, data });
      loadedCells.add(cellId);
    } finally {
      streamBusy.delete(cellId);
    }
  }

  function unloadFar(worldId, cx, cy) {
    for (const cellId of [...loadedCells]) {
      const [x, y] = parseId(cellId);
      if (Math.abs(x - cx) > KEEP || Math.abs(y - cy) > KEEP) {
        WorldViewport.dropCell(cellId);
        loadedCells.delete(cellId);
        state.world.cells = state.world.cells.filter((c) => c.id !== cellId);
      }
    }
  }

  on("world-loaded", () => {
    loadedCells.clear();
    for (const c of state.world.cells) loadedCells.add(c.id);
    lastCell = "";
  });

  on("cam", async (c) => {
    if (state.mode !== "world" || !state.world.id) return;
    if (c.cell === lastCell) return;
    lastCell = c.cell;
    const [cx, cy] = parseId(c.cell);
    unloadFar(state.world.id, cx, cy);
    for (let dx = -RADIUS; dx <= RADIUS; dx++) {
      for (let dy = -RADIUS; dy <= RADIUS; dy++) {
        ensureCell(state.world.id, fmt(cx + dx, cy + dy));
      }
    }
  });

  on("open-world", (id) => {
    const w = state.catalog.worlds.find((x) => x.id === id);
    if (w) loadWorld(w.id, w.cells);
  });
  on("open-cell", ({ world, cell }) => loadWorld(world, [cell]));
  on("goto-region", (r) => {
    /* fly to a named region (Nuia/Epherus/sea). Streaming loads the baked
     * cells around it; unbaked sea regions still show the continent relief. */
    if (!r || !r.center) return;
    if (state.mode !== "world") setMode("world");
    const [gx, gz] = r.center;
    let h = 120;
    const ov = WorldViewport.ovmaps && WorldViewport.ovmaps.get(
      String(Math.floor(gx / 1024)).padStart(3, "0") +
        "_" + String(Math.floor(gz / 1024)).padStart(3, "0"),
    );
    if (ov && ov.heights) {
      const n = ov.heights.length;
      const row = ov.heights[Math.floor(n / 2)];
      if (row) h = row[Math.floor(row.length / 2)] || h;
    }
    WorldViewport.controls.target.set(gx, h + 8, gz);
    WorldViewport.camera.position.set(gx - 260, h + 150, gz - 260);
    WorldViewport.controls.update();
    setStatus("Fly to " + (r.label || r.name));
  });
  on("select-entity", ({ entity, cellId }) => {
    WorldViewport.selectEntity(entity, cellId);
  });
  on("select-terrain", (cellId) => {
    WorldViewport.transform.detach();
    state.selected = { kind: "terrain", cellId };
    emit("select", state.selected);
  });
  on("select-water", (cellId) => {
    WorldViewport.transform.detach();
    state.selected = { kind: "water", cellId };
    emit("select", state.selected);
  });
  on("select-cell", (cellId) => {
    const cell = state.world.cells.find((c) => c.id === cellId);
    if (cell) WorldViewport.fitCell(cell.origin, cell.data.heightmap);
  });
  on("apply-entity", ({ entity, cellId }) => {
    const mesh = WorldViewport.entityMeshes.find(
      (m) => m.userData.entity === entity && m.userData.cellId === cellId,
    );
    if (!mesh) return;
    const origin = mesh.userData.origin || cellOrigin(cellId);
    const [gx, gy, gz] = toWorldPos(entity.pos, origin);
    mesh.position.set(gx, gz + (mesh.userData.volume ? 0 : 2.4), gy);
    const s = entity.scale || [1, 1, 1];
    mesh.scale.set(s[0], s[2], s[1]);
    setStatus("entity moved");
  });
}

async function boot() {
  bindChrome();
  bindOutliner();
  bindInspector();
  bindContent();
  bindUiMode();
  bindWorldEvents();
  WorldViewport.init($("#worldWrap"));
  window.addEventListener("resize", () => {
    WorldViewport.resize();
    fitUiStage();
  });
  applyMode();
  await loadCatalog();
  await loadDefaultWorld();
  const q = new URLSearchParams(location.search).get("mode");
  if (q === "ui" || q === "world") setMode(q);
  document.documentElement.dataset.ready = "1";
}

boot();
