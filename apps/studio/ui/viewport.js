/* viewport.js — 3D world viewport for ArcheaAge Studio.
 * Renders a cell JSON (contract from tools/world/world_to_json.py):
 *   { cell, heightmap: {width, unit_size, max_height, water_level, heights},
 *     entities: [{name, class, pos:[x,y,z], rotate:[w,x,y,z], scale:[x,y,z], model, layer}] }
 *
 * CryEngine uses Z-up. three.js uses Y-up. We map game (x, y, z) -> three (x, z, y).
 */

import * as THREE from "./vendor/three.module.js";
import { OrbitControls } from "./vendor/OrbitControls.js";

const WorldViewport = {
  renderer: null,
  scene: null,
  camera: null,
  controls: null,
  group: null,
  entityMeshes: [],
  selEntity: null,
  raycaster: new THREE.Raycaster(),
  mouse: new THREE.Vector2(),
  dragPlane: new THREE.Plane(),
  dragging: null,
  onSelect: null, // callback(entity) when an entity is clicked

  init(container) {
    const w = container.clientWidth || 800;
    const h = container.clientHeight || 600;
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(w, h);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0b1512);

    this.camera = new THREE.PerspectiveCamera(55, w / h, 0.1, 20000);
    this.camera.position.set(800, 600, 900);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.target.set(512, 0, 512);

    // lights
    this.scene.add(new THREE.HemisphereLight(0xbfd4ff, 0x2a3028, 0.9));
    const sun = new THREE.DirectionalLight(0xffffff, 1.1);
    sun.position.set(600, 1200, 400);
    this.scene.add(sun);

    // helpers
    const grid = new THREE.GridHelper(2048, 64, 0x3a4a3a, 0x22301f);
    grid.position.y = -0.5;
    this.scene.add(grid);
    const axes = new THREE.AxesHelper(200);
    this.scene.add(axes);

    // resize
    window.addEventListener("resize", () => this.resize(container));
    this.resize(container);

    // picking + dragging
    this.renderer.domElement.addEventListener("pointerdown", (e) =>
      this.onPointerDown(e),
    );
    this.renderer.domElement.addEventListener("pointermove", (e) =>
      this.onPointerMove(e),
    );
    this.renderer.domElement.addEventListener("pointerup", () => {
      this.dragging = null;
    });

    this.animate();
  },

  resize(container) {
    const w = container.clientWidth || 800;
    const h = container.clientHeight || 600;
    this.renderer.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  },

  /* ---------- data ---------- */

  loadCell(data) {
    if (this.group) {
      this.scene.remove(this.group);
    }
    this.group = new THREE.Group();
    this.entityMeshes = [];
    this.scene.add(this.group);

    const hm = data.heightmap;
    if (hm && hm.heights) {
      this.group.add(this.buildTerrain(hm));
      this.group.add(this.buildWater(hm));
    }
    for (const ent of data.entities || []) {
      this.group.add(this.buildEntity(ent));
    }
    this.fitCamera(data);
  },

  buildTerrain(hm) {
    const n = hm.width; // 512
    const unit = hm.unit_size || 2; // meters per height sample
    const heights = hm.heights; // rows of n floats (meters)
    const ZS = 3; // vertical exaggeration so relief is visible

    // normalize color by the cell's REAL height range, not maxH
    let lo = Infinity,
      hi = -Infinity;
    for (const row of heights)
      for (const v of row) {
        if (v < lo) lo = v;
        if (v > hi) hi = v;
      }
    const span = Math.max(1, hi - lo);

    const geo = new THREE.PlaneGeometry(n * unit, n * unit, n - 1, n - 1);
    geo.rotateX(-Math.PI / 2); // XY plane -> XZ, +Y up
    const pos = geo.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);
      // grid row/col from world coords (origin at corner, unit spacing)
      const col = Math.min(n - 1, Math.max(0, Math.round(x / unit)));
      const row = Math.min(n - 1, Math.max(0, Math.round(z / unit)));
      const h = heights[row][col];
      pos.setY(i, (Number.isFinite(h) ? h : 0) * ZS);
    }
    geo.computeVertexNormals();

    // color by height within the cell's real range: sand -> grass -> rock
    const colors = new Float32Array(pos.count * 3);
    const c = new THREE.Color();
    for (let i = 0; i < pos.count; i++) {
      const h = pos.getY(i);
      const t = Math.min(1, Math.max(0, (h / ZS - lo) / span));
      if (h < 0) c.setRGB(0.16, 0.22, 0.3);
      else if (t < 0.2) c.setRGB(0.55, 0.62, 0.4); // sand/shallow
      else if (t < 0.55) c.setRGB(0.35, 0.5, 0.28); // grass
      else if (t < 0.8) c.setRGB(0.5, 0.47, 0.36); // rock
      else c.setRGB(0.62, 0.6, 0.58); // peak
      colors[i * 3] = c.r;
      colors[i * 3 + 1] = c.g;
      colors[i * 3 + 2] = c.b;
    }
    geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));

    const mat = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 1,
      metalness: 0,
    });
    return new THREE.Mesh(geo, mat);
  },

  buildWater(hm) {
    const n = hm.width * (hm.unit_size || 2);
    const geo = new THREE.PlaneGeometry(n, n);
    geo.rotateX(-Math.PI / 2);
    const mat = new THREE.MeshStandardMaterial({
      color: 0x1e5f8a,
      transparent: true,
      opacity: 0.45,
      roughness: 0.2,
    });
    const water = new THREE.Mesh(geo, mat);
    water.position.y = (hm.water_level || 0) * 3; // match terrain Z_SCALE
    return water;
  },

  buildEntity(ent) {
    const [x, y, z] = ent.pos || [0, 0, 0];
    const [sx, sy, sz] = ent.scale || [1, 1, 1];
    const cls = (ent.class || "Entity").toLowerCase();

    // placeholder geometry by class
    let geo;
    if (cls.includes("light")) geo = new THREE.SphereGeometry(3, 8, 8);
    else if (cls.includes("fish") || cls.includes("animal"))
      geo = new THREE.ConeGeometry(4, 10, 6);
    else if (cls.includes("area")) geo = new THREE.BoxGeometry(20, 2, 20);
    else if (cls.includes("npc") || cls.includes("character"))
      geo = new THREE.CylinderGeometry(4, 4, 18, 8);
    else geo = new THREE.BoxGeometry(6, 6, 6);

    const hue = this.classHue(cls);
    const mat = new THREE.MeshStandardMaterial({
      color: new THREE.Color().setHSL(hue, 0.7, 0.55),
      emissive: new THREE.Color().setHSL(hue, 0.8, 0.15),
      roughness: 0.6,
    });
    const mesh = new THREE.Mesh(geo, mat);
    // game (x, y, z) -> three (x, z*3, y); scale applies per-axis
    mesh.position.set(x, z * 3, y);
    mesh.scale.set(sx, sz, sy);
    mesh.userData = { entity: ent };

    // name label
    if (ent.name) {
      const canvas = document.createElement("canvas");
      canvas.width = 512;
      canvas.height = 64;
      const ctx = canvas.getContext("2d");
      ctx.font = "28px Inter, system-ui, sans-serif";
      ctx.fillStyle = "#e7e5d9";
      ctx.textBaseline = "middle";
      ctx.fillText(ent.name, 8, 32);
      const tex = new THREE.CanvasTexture(canvas);
      const sprite = new THREE.Sprite(
        new THREE.SpriteMaterial({ map: tex, depthTest: false }),
      );
      sprite.scale.set(80, 10, 1);
      sprite.position.y = 14;
      mesh.add(sprite);
    }

    this.entityMeshes.push(mesh);
    return mesh;
  },

  classHue(cls) {
    if (cls.includes("light")) return 0.12; // yellow
    if (cls.includes("fish")) return 0.55; // cyan
    if (cls.includes("area")) return 0.75; // purple
    if (cls.includes("npc") || cls.includes("character")) return 0.0; // red
    if (cls.includes("anim")) return 0.33; // green
    return 0.6; // blue
  },

  fitCamera(data) {
    const hm = data.heightmap;
    if (!hm) return;
    const size = hm.width * (hm.unit_size || 2);
    this.controls.target.set(size / 2, 0, size / 2);
    this.camera.position.set(size * 0.9, size * 0.7, size * 0.9);
    this.controls.update();
  },

  /* ---------- picking / dragging ---------- */

  onPointerDown(e) {
    this.updateMouse(e);
    const hits = this.raycaster.intersectObjects(this.entityMeshes, true);
    if (hits.length) {
      let m = hits[0].object;
      while (m && !m.userData.entity) m = m.parent;
      if (m && m.userData.entity) {
        this.selEntity = m;
        this.dragging = m;
        this.dragPlane.setFromNormalAndCoplanarPoint(
          new THREE.Vector3(0, 1, 0),
          m.position,
        );
        this.controls.enabled = false;
        if (this.onSelect) this.onSelect(m.userData.entity);
        return;
      }
    }
    this.selEntity = null;
    if (this.onSelect) this.onSelect(null);
  },

  onPointerMove(e) {
    this.updateMouse(e);
    if (this.dragging) {
      const ray = this.raycaster.ray;
      const pt = new THREE.Vector3();
      ray.intersectPlane(this.dragPlane, pt);
      if (pt) {
        this.dragging.position.x = pt.x;
        this.dragging.position.z = pt.z;
        // keep height; undo the game->three mapping (three.y = game.z*3)
        if (this.dragging.userData.entity) {
          this.dragging.userData.entity.pos = [
            pt.x,
            pt.z,
            this.dragging.position.y / 3,
          ];
        }
      }
    }
  },

  updateMouse(e) {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.mouse, this.camera);
  },

  animate() {
    requestAnimationFrame(() => this.animate());
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  },
};

window.WorldViewport = WorldViewport;
