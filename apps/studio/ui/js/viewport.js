/* World viewport — CryEngine Z-up (x,y,z) → three.js Y-up (x, z, y).
 * Terrain is built in metres at the cell origin. No vertical exaggeration.
 *
 * Scene modules mix methods onto WorldViewport (same `this`):
 *   environment.js  sky / sun / weather
 *   assets.js       texture + mesh cache
 *   terrain.js      heightmap / water / overview
 *   entities.js     brushes, veg, NPCs, picking
 */
import * as THREE from "three";
import { OrbitControls } from "../vendor/OrbitControls.js";
import { TransformControls } from "../vendor/TransformControls.js";
import { CELL_METERS, cellOrigin, emit, on, state } from "./state.js";
import { assetMethods } from "./assets.js";
import { entityMethods } from "./entities.js";
import { environmentMethods, installLightsAndSky } from "./environment.js";
import { makeGroundTexture, terrainMethods } from "./terrain.js";

const FORWARD = new THREE.Vector3();
const RIGHT = new THREE.Vector3();
const UP = new THREE.Vector3(0, 1, 0);

export const WorldViewport = {
  renderer: null,
  scene: null,
  camera: null,
  controls: null,
  transform: null,
  container: null,
  worldGroup: null,
  entityMeshes: [],
  cellGroups: new Map(),
  grid: null,
  groundTex: null,
  keys: new Set(),
  flying: false,
  lastT: 0,
  fps: 0,
  frames: 0,
  fpsT: 0,
  running: false,
  meshLib: null,
  texLib: null,
  terrainMaps: null,
  lodMap: null,
  lodT: 0,

  init(container) {
    this.container = container;
    const w = container.clientWidth || 800;
    const h = container.clientHeight || 600;

    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
      powerPreference: "high-performance",
    });
    this.renderer.setSize(w, h);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setClearColor(0x9cc0d6, 1);
    this.renderer.outputEncoding = THREE.sRGBEncoding;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.05;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    this.maxAniso = this.renderer.capabilities.getMaxAnisotropy
      ? Math.min(16, this.renderer.capabilities.getMaxAnisotropy())
      : 8;
    container.appendChild(this.renderer.domElement);
    this.renderer.domElement.addEventListener("contextmenu", (e) =>
      e.preventDefault(),
    );

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x9cc0d6);
    this.scene.fog = new THREE.FogExp2(0xaacbe2, 0.00006);

    this.camera = new THREE.PerspectiveCamera(60, w / h, 0.6, 24000);
    this.camera.position.set(800, 120, 800);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.1;
    this.controls.screenSpacePanning = true;
    this.controls.mouseButtons = {
      LEFT: -1,
      MIDDLE: THREE.MOUSE.PAN,
      RIGHT: THREE.MOUSE.ROTATE,
    };
    this.controls.touches = { ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_ROTATE };
    this.controls.maxPolarAngle = Math.PI * 0.9;
    this.controls.minDistance = 1.5;
    this.controls.maxDistance = 60000;

    this.transform = new TransformControls(this.camera, this.renderer.domElement);
    this.transform.setSize(0.9);
    this.transform.visible = false;
    this.transform.addEventListener("dragging-changed", (e) => {
      this.controls.enabled = !e.value;
    });
    this.transform.addEventListener("objectChange", () => this.syncSelectedFromMesh());
    this.scene.add(this.transform);

    installLightsAndSky(this);

    this.grid = new THREE.GridHelper(CELL_METERS * 4, 64, 0x6a7a4a, 0x3a4a38);
    this.grid.visible = false;
    this.scene.add(this.grid);

    this.groundTex = makeGroundTexture();
    this._camUniform = { value: new THREE.Vector3() };
    this.meshLib = new Map();
    this.texLib = new Map();
    this.hmaps = new Map();
    this.ovmaps = new Map();
    this.terrainMaps = {};
    this.worldGroup = new THREE.Group();
    this.scene.add(this.worldGroup);

    window.addEventListener("resize", () => this.resize());
    this.resize();

    const canvas = this.renderer.domElement;
    canvas.addEventListener("pointerdown", (e) => this.onPointerDown(e));
    window.addEventListener("keydown", (e) => this.onKey(e, true));
    window.addEventListener("keyup", (e) => this.onKey(e, false));
    canvas.addEventListener("pointerdown", (e) => {
      if (e.button === 2) this.flying = true;
    });
    window.addEventListener("pointerup", (e) => {
      if (e.button === 2) this.flying = false;
    });

    on("gizmo", (mode) => this.transform.setMode(mode));
    on("view-flags", () => this.applyFlags());
    on("env", () => this.applyEnvironment());
    this.bindMinimap(document.getElementById("minimap"));

    this.applyEnvironment();
    this.running = true;
    this.lastT = performance.now();
    this.animate();
  },

  resize() {
    const w = this.container.clientWidth || 800;
    const h = this.container.clientHeight || 600;
    this.renderer.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  },
  clearWorld() {
    this.transform.detach();
    if (this._brushProxy) {
      this.scene.remove(this._brushProxy);
      this._brushProxy = null;
    }
    if (this.worldGroup) this.scene.remove(this.worldGroup);
    this.worldGroup = new THREE.Group();
    this.scene.add(this.worldGroup);
    this.entityMeshes = [];
    this.cellGroups.clear();
    this.lodMap = new Map();
    this.waterMeshes = [];
    this.waterMats = [];
    this.hmaps = new Map();
    this.ovmaps = new Map();
    this.overviewGroup = null;
  },
  loadCell(data, worldId, opts) {
    const cellId = data.cell || "000_000";
    const origin = cellOrigin(cellId);
    const group = new THREE.Group();
    group.name = cellId;
    group.userData = { cellId, origin, worldId, data };

    const hm = data.heightmap;
    if (hm && hm.heights) {
      this.hmaps.set(cellId, hm);
      group.add(this.buildTerrain(hm, origin, cellId, null, false, opts && opts.cover));
      group.add(this.buildWater(hm, origin, cellId));
    }

    const skipEnt = opts && opts.skipEntities;
    if (!skipEnt) {
      for (const ent of data.entities || []) {
        if (!ent.name && !ent.class) continue;
        group.add(this.buildEntity(ent, origin, cellId));
      }
    }

    this.worldGroup.add(group);
    this.cellGroups.set(cellId, group);
    this._ovDirty = true;
    this.applyFlags();
    if (!opts || opts.fit !== false) this.fitCell(origin, hm);
    return { cellId, origin, data };
  },
  fitWorld() {
    this.overview();
  },
  fitGround(origin, hm) {
    const size = (hm?.width || 512) * (hm?.unit_size || 2);
    const cx = origin.x + size * 0.5;
    const cz = origin.y + size * 0.5;
    const h = this.terrainHeight(hm, 0.5, 0.5);
    this.controls.target.set(cx, h + 3.5, cz);
    this.camera.position.set(cx - 22, h + 11, cz + 34);
    this.controls.update();
    if (this.sun) {
      this.sun.target.position.set(cx, h, cz);
      this.sun.position.set(cx + 420, h + 780, cz + 240);
      this.sun.target.updateMatrixWorld();
    }
  },
  fitCell(origin, hm) {
    this.fitGround(origin, hm);
  },
  focus(mesh) {
    if (!mesh) return;
    const p = mesh.position;
    this.controls.target.copy(p);
    const dist = 48;
    const dir = this.camera.position.clone().sub(this.controls.target);
    if (dir.lengthSq() < 1) dir.set(1, 0.6, 1);
    dir.setLength(dist);
    this.camera.position.copy(p).add(dir);
    this.controls.update();
  },
  onKey(e, down) {
    const tag = (e.target && e.target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA") return;
    const k = e.key.toLowerCase();
    if (down) this.keys.add(k);
    else this.keys.delete(k);

    if (!down) return;
    if (k === "1") emit("gizmo", "translate");
    else if (k === "2") emit("gizmo", "rotate");
    else if (k === "3") emit("gizmo", "scale");
    else if (k === "f" && state.selected?.mesh) this.focus(state.selected.mesh);
    else if (k === "home" || k === "h") this.overview();
    else if (k === "escape") this.selectMesh(null);
    else if (k === "g") {
      state.showGrid = !state.showGrid;
      emit("view-flags");
    }
  },
  fly(dt) {
    if (state.mode !== "world") return;
    if (this.transform && this.transform.dragging) return;
    const boost = this.keys.has("shift") ? 3.4 : this.keys.has("control") ? 0.28 : 1;
    const alt = Math.max(1, this.camera.position.y / 70);
    const speed = 110 * boost * Math.min(18, alt) * dt;
    const look = new THREE.Vector3();
    this.camera.getWorldDirection(look);
    FORWARD.copy(look);
    FORWARD.y = 0;
    if (FORWARD.lengthSq() < 1e-6) FORWARD.set(0, 0, 1);
    else FORWARD.normalize();
    RIGHT.crossVectors(FORWARD, UP).normalize();
    const move = new THREE.Vector3();
    const fwd = this.flying ? look : FORWARD;
    if (this.keys.has("w")) move.add(fwd);
    if (this.keys.has("s")) move.sub(fwd);
    if (this.keys.has("d")) move.add(RIGHT);
    if (this.keys.has("a")) move.sub(RIGHT);
    if (this.keys.has("e") || this.keys.has("pageup")) move.add(UP);
    if (this.keys.has("q") || this.keys.has("pagedown")) move.sub(UP);
    if (move.lengthSq() === 0) return;
    move.normalize().multiplyScalar(speed);
    this.camera.position.add(move);
    this.controls.target.add(move);
  },
  worldBounds() {
    let minx = Infinity;
    let minz = Infinity;
    let maxx = -Infinity;
    let maxz = -Infinity;
    const add = (id) => {
      const o = cellOrigin(id);
      minx = Math.min(minx, o.x);
      minz = Math.min(minz, o.y);
      maxx = Math.max(maxx, o.x + CELL_METERS);
      maxz = Math.max(maxz, o.y + CELL_METERS);
    };
    this.cellGroups.forEach((_g, id) => add(id));
    if (this.overviewGroup) {
      this.overviewGroup.children.forEach((m) => {
        if (m.userData?.cellId) add(m.userData.cellId);
      });
    }
    return { minx, minz, maxx, maxz };
  },
  overview() {
    if (!this.cellGroups.size) return;
    const b = this.worldBounds();
    if (!Number.isFinite(b.minx)) return;
    const cx = (b.minx + b.maxx) / 2;
    const cz = (b.minz + b.maxz) / 2;
    const span = Math.max(b.maxx - b.minx, b.maxz - b.minz);
    this.controls.target.set(cx, 80, cz);
    this.camera.position.set(cx - span * 0.08, Math.max(180, span * 0.22), cz + span * 0.42);
    this.controls.update();
    if (this.sun) {
      this.sun.target.position.set(cx, 0, cz);
      this.sun.position.set(cx + 700, 1100, cz + 350);
      this.sun.target.updateMatrixWorld();
    }
  },
  bindMinimap(canvas) {
    this.minimap = canvas;
    if (!canvas) return;
    canvas.addEventListener("pointerdown", (e) => this.minimapClick(e));
  },
  minimapClick(e) {
    if (!this.cellGroups.size) return;
    const b = this.worldBounds();
    const rect = this.minimap.getBoundingClientRect();
    const u = (e.clientX - rect.left) / rect.width;
    const v = 1 - (e.clientY - rect.top) / rect.height;
    const x = b.minx + u * (b.maxx - b.minx);
    const z = b.minz + v * (b.maxz - b.minz);
    const dx = x - this.controls.target.x;
    const dz = z - this.controls.target.z;
    this.controls.target.x = x;
    this.controls.target.z = z;
    this.camera.position.x += dx;
    this.camera.position.z += dz;
    this.controls.update();
  },
  drawMinimap() {
    const canvas = this.minimap;
    if (!canvas || !this.cellGroups.size) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    const b = this.worldBounds();
    const bw = b.maxx - b.minx || 1;
    const bh = b.maxz - b.minz || 1;
    ctx.fillStyle = "#08110e";
    ctx.fillRect(0, 0, w, h);
    const drawCell = (id, fill, stroke, label) => {
      const o = cellOrigin(id);
      const x = ((o.x - b.minx) / bw) * w;
      const y = h - ((o.y - b.minz + CELL_METERS) / bh) * h;
      const cw = (CELL_METERS / bw) * w;
      const ch = (CELL_METERS / bh) * h;
      ctx.fillStyle = fill;
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 1;
      ctx.fillRect(x, y, cw, ch);
      ctx.strokeRect(x, y, cw, ch);
      if (label && cw > 18) {
        ctx.fillStyle = "#d3c58a";
        ctx.font = "9px sans-serif";
        ctx.fillText(id, x + 2, y + 11);
      }
    };
    if (this.overviewGroup) {
      this.overviewGroup.children.forEach((m) => {
        if (m.userData?.cellId) drawCell(m.userData.cellId, "#15241c", "#2f4a38", false);
      });
    }
    this.cellGroups.forEach((_g, id) => {
      drawCell(id, "#1d3328", "#6d9a3a", true);
    });
    const p = this.camera.position;
    const cx = ((p.x - b.minx) / bw) * w;
    const cy = h - ((p.z - b.minz) / bh) * h;
    this.camera.getWorldDirection(FORWARD);
    ctx.strokeStyle = "#ffcc44";
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + FORWARD.x * 16, cy - FORWARD.z * 16);
    ctx.stroke();
    ctx.fillStyle = "#ffcc44";
    ctx.beginPath();
    ctx.arc(cx, cy, 3.5, 0, Math.PI * 2);
    ctx.fill();
  },
  updateClip() {
    const alt = Math.max(1, this.camera.position.y);
    const near = Math.min(6, Math.max(0.35, alt * 0.0025));
    const far = Math.min(120000, Math.max(12000, alt * 14 + 9000));
    if (Math.abs(this.camera.near - near) > 0.05 || Math.abs(this.camera.far - far) > 50) {
      this.camera.near = near;
      this.camera.far = far;
      this.camera.updateProjectionMatrix();
    }
    if (this.sky) this.sky.position.copy(this.camera.position);
    /* refresh the (expensive) shadow map only when the camera has moved far
     * enough that the shadow texel alignment changed */
    const sp = this._lastShadowPos || (this._lastShadowPos = new THREE.Vector3(1e9, 0, 0));
    const t = this.controls.target;
    if (sp.distanceToSquared(t) > 90 * 90) {
      sp.copy(t);
      this.renderer.shadowMap.needsUpdate = true;
    }
    /* fog is ground-level atmosphere; fade it out as we climb so the continent
     * overview stays readable instead of washing to white */
    if (this.scene.fog) {
      const alt2 = Math.max(0, this.camera.position.y - 150);
      const k = Math.max(0, 1 - alt2 / 700);
      this.scene.fog.density = (this._fogBase || 0.00006) * Math.max(k, 0.15);
    }
    /* The continent overview fills the far horizon (so flying around never
     * shows empty sky where terrain should be). It's sunk below the detailed
     * surface so coarse triangles can't poke through loaded cells; detail
     * terrain (drawn after) covers it exactly where high-res data exists. */
    if (this.overviewGroup) {
      if (!this.overviewGroup.visible) this.overviewGroup.visible = true;
    }
    if (this.sun) {
      const t = this.controls.target;
      this.sun.target.position.set(t.x, t.y, t.z);
      this.sun.position.set(t.x + 480, t.y + 820, t.z + 260);
      this.sun.target.updateMatrixWorld();
    }
  },
  emitCam() {
    const p = this.camera.position;
    const gx = p.x;
    const gy = p.z;
    const gz = p.y;
    const cx = Math.floor(gx / CELL_METERS);
    const cy = Math.floor(gy / CELL_METERS);
    const cell =
      String(Math.max(0, cx)).padStart(3, "0") +
      "_" +
      String(Math.max(0, cy)).padStart(3, "0");
    emit("cam", { x: gx, y: gy, z: gz, cell });
  },
  animate() {
    if (!this.running) return;
    requestAnimationFrame(() => this.animate());
    const now = performance.now();
    const dt = Math.min(0.05, (now - this.lastT) / 1000);
    this.lastT = now;
    this.fly(dt);
    this.controls.update();
    this.updateClip();
    if (this._camUniform) this._camUniform.value.copy(this.camera.position);
    this.updatePrecip(dt);
    if (this._envDirty && now - (this._envT || 0) > 400) {
      this._envT = now;
      this.updateEnvMap();
    }
    if (now - (this._lodT || 0) > 250) {
      this._lodT = now;
      this.refreshLod();
    }
    if (this._ovDirty) this._rebuildOverview();
    this.animateWater(now * 0.02);
    this.renderer.render(this.scene, this.camera);
    this.frames += 1;
    if (now - this.fpsT > 200) {
      this.fps = Math.round((this.frames * 1000) / (now - this.fpsT));
      this.frames = 0;
      this.fpsT = now;
      emit("fps", this.fps);
      this.drawMinimap();
      this.emitCam();
    }
  },
  refreshLod() {
    const cam = this.camera.position;
    /* Per-cluster distance LOD. Vegetation/buildings live in spatial buckets
     * (see _bucketize) whose object position IS the bucket centre, so we can
     * cull individual 512 m clusters instead of whole cells. Terrain always
     * renders; only props fade. Far props are sub-pixel (fog hides the cut). */
    const alt = Math.max(0, cam.y - 120);
    const climb = Math.min(2.2, 1 + alt / 900); // climb higher -> see more props
    const VEG = 430 * climb;
    const BRUSH = 760 * climb;
    const ACTOR = 420 * climb;
    const CELL = 3600;
    const camY = cam.y;
    let changed = false;
    this.cellGroups.forEach((g, id) => {
      const o = g.userData.origin || cellOrigin(id);
      const dx = Math.max(o.x - cam.x, 0, cam.x - (o.x + CELL_METERS));
      const dz = Math.max(o.y - cam.z, 0, cam.z - (o.y + CELL_METERS));
      const cellDist = Math.hypot(dx, dz);
      const showCell = cellDist < CELL;
      if (g.visible !== showCell) g.visible = showCell;
      if (!showCell) return;
      for (const ch of g.children) {
        const k = ch.userData?.kind;
        if (k !== "veg" && k !== "brush-group" && k !== "npc-group" && k !== "doodad-group")
          continue;
        let limit = k === "veg" ? VEG : k === "brush-group" ? BRUSH : ACTOR;
        const p = ch.position; // bucket centre (world x,z; y unused)
        const d = Math.hypot(p.x - cam.x, p.z - cam.z);
        const vis = d < limit;
        if (ch.visible !== vis) { ch.visible = vis; changed = true; }
        /* only near buildings cast shadows — the shadow pass re-renders every
         * caster, and 4 M tris of far rooftops was the single biggest cost */
        if (k === "brush-group") {
          const cast = d < 170;
          if (ch.castShadow !== cast) { ch.castShadow = cast; changed = true; }
        }
      }
      void camY;
    });
  },
};

Object.assign(WorldViewport, environmentMethods, assetMethods, terrainMethods, entityMethods);
