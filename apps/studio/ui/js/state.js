/** Shared editor state + tiny event bus. */

export const CELL_METERS = 1024;

export const HIDDEN_CLASSES_DEFAULT = [
  "AmbientVolume",
  "ReverbVolume",
  "AreaShape",
];

const bus = new EventTarget();

export function on(name, fn) {
  bus.addEventListener(name, (e) => fn(e.detail));
}

export function emit(name, detail) {
  bus.dispatchEvent(new CustomEvent(name, { detail }));
}

export const state = {
  mode: "world",
  gizmo: "translate",
  showGrid: false,
  showWater: true,
  showVolumes: false,
  timeOfDay: 13, // hours 0..24 (matches the game's SCDetailedTimeOfDayPacket)
  weather: "clear", // clear | overcast | rain | snow | fog
  catalog: { worlds: [] },
  world: {
    id: "",
    cells: [], // { id, origin, data, entityCount }
  },
  selected: null, // { kind, cellId, entity, mesh }
  ui: {
    screens: {},
    order: [],
    active: null,
    sel: null,
  },
  status: "Ready",
};

export function parseCellId(id) {
  const m = String(id || "").match(/(\d+)_(\d+)/);
  if (!m) return { cx: 0, cy: 0 };
  return { cx: Number(m[1]), cy: Number(m[2]) };
}

export function cellOrigin(cellId) {
  const { cx, cy } = parseCellId(cellId);
  return { x: cx * CELL_METERS, y: cy * CELL_METERS };
}

/** Map entity Pos to world metres. Cell-local (0..1024) gets the cell origin. */
export function toWorldPos(pos, origin) {
  const [x, y, z] = pos || [0, 0, 0];
  const inWorldX = x >= origin.x - 1 && x <= origin.x + CELL_METERS + 1;
  const inWorldY = y >= origin.y - 1 && y <= origin.y + CELL_METERS + 1;
  if (inWorldX && inWorldY) return [x, y, z];
  return [x + origin.x, y + origin.y, z];
}

/** three.js (x, y, z) with Y-up → game (x, y, z) with Z-up. */
export function threeToGame(tx, ty, tz, origin) {
  return [tx - origin.x, tz - origin.y, ty];
}

export function isVolumeClass(cls) {
  const c = (cls || "").toLowerCase();
  return (
    c.includes("volume") ||
    c.includes("areashape") ||
    c.includes("reverb")
  );
}

export function setStatus(msg) {
  state.status = msg || "";
  emit("status", state.status);
}

export function setMode(mode) {
  if (mode !== "world" && mode !== "ui") return;
  state.mode = mode;
  emit("mode", mode);
}

export async function winAction(action) {
  try {
    if (window.__TAURI__) {
      await window.__TAURI__.window.getCurrentWindow()[action]();
    }
  } catch {
    /* browser preview */
  }
}

export function $(sel, root = document) {
  return root.querySelector(sel);
}

export function el(tag, attrs = {}, kids = []) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on") && typeof v === "function") n[k] = v;
    else if (v === false || v == null) continue;
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids) if (c) n.append(c);
  return n;
}
