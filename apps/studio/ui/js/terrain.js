/* Terrain, water, continent overview — methods mixed into WorldViewport. */
import * as THREE from "three";
import { CELL_METERS, cellOrigin, state } from "./state.js";

function hashNoise(x, y) {
  const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453;
  return s - Math.floor(s);
}

function valueNoise(x, y) {
  const xi = Math.floor(x);
  const yi = Math.floor(y);
  const xf = x - xi;
  const yf = y - yi;
  const u = xf * xf * (3 - 2 * xf);
  const v = yf * yf * (3 - 2 * yf);
  const a = hashNoise(xi, yi);
  const b = hashNoise(xi + 1, yi);
  const c = hashNoise(xi, yi + 1);
  const d = hashNoise(xi + 1, yi + 1);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}

export function makeGroundTexture() {
  const s = 256;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = s;
  const ctx = canvas.getContext("2d");
  const img = ctx.createImageData(s, s);
  for (let y = 0; y < s; y++) {
    for (let x = 0; x < s; x++) {
      const n = hashNoise(x * 0.12, y * 0.12);
      const n2 = hashNoise(x * 0.37, y * 0.29);
      const n3 = hashNoise(x * 1.7, y * 1.9);
      const i = (y * s + x) * 4;
      img.data[i] = 48 + n * 28 + n3 * 18;
      img.data[i + 1] = 78 + n * 40 + n2 * 16;
      img.data[i + 2] = 32 + n * 12;
      img.data[i + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.anisotropy = 8;
  tex.flipY = true;
  tex.repeat.set(1, 1);
  return tex;
}

export const terrainMethods = {
  makeTerrainMat(coverTex) {
    const mat = new THREE.MeshLambertMaterial({
      map: this.groundTex,
      color: 0xffffff,
      vertexColors: false,
      side: THREE.FrontSide,
      depthWrite: true,
    });
    /* Terrain shading. If the cell has its baked cover.ctc map (the game's
     * real painted biome — roads, paths, shore sand), use it as the macro
     * colour modulated by a tiled detail texture for near-camera grain.
     * Otherwise fall back to the procedural grass/dirt/sand/rock blend.
     * Geometry uv is cell-normalised (0..1); detail tiling is derived from
     * world position in the shader so cells seam perfectly. */
    const self = this;
    mat.onBeforeCompile = function (shader) {
      shader.uniforms.tGrass = { value: self.groundTex };
      shader.uniforms.tDirt = { value: self.dirtTex || self.groundTex };
      shader.uniforms.tSand = { value: self.sandTex || self.groundTex };
      shader.uniforms.tRock = { value: self.rockTex || self.groundTex };
      shader.uniforms.tCover = { value: coverTex || self.groundTex };
      shader.vertexShader =
        "attribute vec4 aBlend;\nvarying vec4 vBlend;\nvarying vec3 vWP;\n" +
        shader.vertexShader.replace(
          "#include <begin_vertex>",
          "#include <begin_vertex>\n\tvBlend = aBlend;\n\tvWP = (modelMatrix * vec4(transformed, 1.0)).xyz;",
        );
      if (coverTex) {
        shader.fragmentShader =
          "uniform sampler2D tCover, tGrass;\nvarying vec3 vWP;\n" +
          shader.fragmentShader.replace(
            "#include <map_fragment>",
            `
            vec3 covRaw = texture2D(tCover, vUv).rgb;
            vec3 det = pow(texture2D(tGrass, vWP.xz * 0.0625).rgb, vec3(2.2));
            // the game's baked cover has black voids (unpainted/water texels);
            // fall those back to the tiled grass so no black patches appear
            float covLum = dot(covRaw, vec3(0.333));
            vec3 cov = mix(det, pow(covRaw, vec3(1.45)), smoothstep(0.04, 0.12, covLum));
            diffuseColor.rgb *= cov * (0.82 + 0.55 * det);
            `,
          );
      } else {
        shader.fragmentShader =
          "uniform sampler2D tGrass, tDirt, tSand, tRock;\nvarying vec4 vBlend;\nvarying vec3 vWP;\nvec3 terrainSrgb(vec3 c){ return pow(c, vec3(2.2)); }\n" +
          shader.fragmentShader.replace(
            "#include <map_fragment>",
            `
            vec2 dUV = vWP.xz * 0.125;
            vec3 tg = terrainSrgb(texture2D(tGrass, dUV).rgb);
            vec3 td = terrainSrgb(texture2D(tDirt, dUV).rgb);
            vec3 ts = terrainSrgb(texture2D(tSand, dUV).rgb);
            vec3 tr = terrainSrgb(texture2D(tRock, dUV).rgb);
            diffuseColor.rgb *= tg*vBlend.x + td*vBlend.y + ts*vBlend.z + tr*vBlend.w;
            `,
          );
      }
    };
    mat.customProgramCacheKey = () => (coverTex ? "terraincover" : "terrain4layer");
    mat.coverUrl = coverTex ? coverTex.userData && coverTex.userData.src : null;
    return mat;
  },
  dropCell(cellId) {
    const g = this.cellGroups.get(cellId);
    if (!g) return;
    /* free the cell's 2048² cover map — keeping 25 of them resident blows the
     * texture budget and causes GC hitches */
    g.traverse((o) => {
      if (o.isMesh && o.userData?.kind === "terrain" && o.material?.coverUrl) {
        const url = o.material.coverUrl;
        const p = this.texLib.get(url + "|1");
        if (p) {
          p.then((t) => { if (t) t.dispose(); });
          this.texLib.delete(url + "|1");
        }
        o.material.map = null;
        o.material.dispose();
      }
    });
    this.worldGroup.remove(g);
    g.traverse((o) => {
      if (o.isMesh || o.isInstancedMesh) {
        if (this.waterMeshes) this.waterMeshes = this.waterMeshes.filter((w) => w !== o);
        if (o.userData?.kind === "brush-group") {
          /* shared geometry/materials stay in meshLib; nothing to dispose */
        }
      }
    });
    this.entityMeshes = this.entityMeshes.filter((m) => m.userData?.cellId !== cellId);
    this.cellGroups.delete(cellId);
    this.hmaps.delete(cellId);
    this._ovDirty = true;
  },
  loadOverview(data) {
    if (this.overviewGroup) {
      this.worldGroup.remove(this.overviewGroup);
    }
    this.ovmaps = new Map();
    for (const cell of data.cells || []) {
      if (!cell.heights) continue;
      this.ovmaps.set(cell.id, {
        width: cell.width || 16,
        unit_size: cell.unit_size || 64,
        heights: cell.heights,
        water_level: cell.water_level || 100,
      });
    }
    this.overviewGroup = new THREE.Group();
    this.overviewGroup.name = "overview";
    /* Keep one merged mesh (1 draw call) but rebuild it to EXCLUDE cells that
     * have loaded detail. A continent-wide overview pokes through the detail
     * surface at rivers/valleys (coarse 64 m grid ≠ 2 m grid), which looked
     * like white flooding. Rebuilding only on cell load/unload keeps it cheap. */
    this._ovMat = new THREE.MeshLambertMaterial({
      color: 0xffffff,
      vertexColors: true,
      side: THREE.FrontSide,
    });
    this._ovCells = [];
    for (const cell of data.cells || []) {
      if ((cell.max || 0) <= 1 && (cell.min || 0) <= 1) continue;
      if (!cell.heights) continue;
      const hm = {
        width: cell.width || 16,
        unit_size: cell.unit_size || 64,
        heights: cell.heights,
        water_level: cell.water_level || 100,
      };
      const mesh = this.buildTerrain(hm, cellOrigin(cell.id), cell.id, this._ovMat, true);
      this._ovCells.push({ id: cell.id, geo: mesh.geometry });
    }
    this.worldGroup.add(this.overviewGroup);
    this._ovDirty = true;
  },
  _rebuildOverview() {
    if (!this._ovCells) return;
    const old = this.overviewGroup.children[0];
    if (old) {
      old.geometry.dispose();
      this.overviewGroup.remove(old);
    }
    const loaded = this.cellGroups;
    let vcount = 0;
    let icount = 0;
    const parts = [];
    for (const c of this._ovCells) {
      if (loaded.has(c.id)) continue;
      parts.push(c);
      vcount += c.geo.attributes.position.count;
      icount += c.geo.index.count;
    }
    if (!parts.length) {
      this._ovDirty = false;
      return;
    }
    const pos = new Float32Array(vcount * 3);
    const col = new Float32Array(vcount * 3);
    const nrm = new Float32Array(vcount * 3);
    const idx = vcount > 65535 ? new Uint32Array(icount) : new Uint16Array(icount);
    let vo = 0;
    let io = 0;
    for (const c of parts) {
      const g = c.geo;
      pos.set(g.attributes.position.array, vo * 3);
      col.set(g.attributes.color.array, vo * 3);
      nrm.set(g.attributes.normal.array, vo * 3);
      const gi = g.index.array;
      for (let i = 0; i < gi.length; i++) idx[io + i] = gi[i] + vo;
      vo += g.attributes.position.count;
      io += gi.length;
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
    geo.setAttribute("normal", new THREE.BufferAttribute(nrm, 3));
    geo.setIndex(new THREE.BufferAttribute(idx, 1));
    geo.computeBoundingSphere();
    const mesh = new THREE.Mesh(geo, this._ovMat);
    mesh.userData = { kind: "overview" };
    mesh.position.y = -2.5;
    mesh.castShadow = false;
    mesh.receiveShadow = false;
    mesh.renderOrder = -2;
    this.overviewGroup.add(mesh);
    this._ovDirty = false;
  },
  hideOverviewCell(cellId) {
    this._ovDirty = true;
  },
  buildOverviewCell(cell, mat) {
    const hm = {
      width: cell.width || 16,
      unit_size: cell.unit_size || 64,
      heights: cell.heights,
      water_level: cell.water_level || 100,
    };
    if (!hm.heights) return null;
    const origin = cellOrigin(cell.id);
    const mesh = this.buildTerrain(hm, origin, cell.id, mat, true);
    mesh.userData = { kind: "overview", cellId: cell.id };
    /* Coarse 64 m overview samples can't match the 2 m detail grid at cell
     * borders, so keep the overview just under the detail surface; the
     * altitude toggle in updateClip() hides it entirely at ground level. */
    mesh.position.y = -2.5;
    mesh.castShadow = false;
    mesh.renderOrder = -2;
    return mesh;
  },
  buildTerrain(hm, origin, cellId, matOverride, coarse, coverTex) {
    const nFull = hm.width;
    const step = nFull >= 512 ? 2 : 1;
    const n = Math.floor((nFull - 1) / step) + 1;
    const unit = (hm.unit_size || 2) * step;
    // full physical span of the cell — vertices map to origin .. origin+size
    // exactly, so neighbouring cells share their border (no crack between them)
    const size = nFull * (hm.unit_size || 2);
    const heights = hm.heights;
    const verts = n * n;
    const positions = new Float32Array(verts * 3);
    const colors = new Float32Array(verts * 3);
    const uvs = new Float32Array(verts * 2);
    const blend = new Float32Array(verts * 4); // grass, dirt, sand, rock

    let lo = Infinity;
    let hi = -Infinity;
    for (const row of heights) {
      for (const v of row) {
        if (v < lo) lo = v;
        if (v > hi) hi = v;
      }
    }
    const span = Math.max(1, hi - lo);
    const water = hm.water_level || 0;

    // terrain tint per biome (multiplies the diffuse detail texture)
    const GRASS_T = [0.96, 1.0, 0.9];
    const SAND_T = [1.0, 0.94, 0.79];
    const ROCK_T = [0.6, 0.57, 0.55];

    for (let row = 0; row < n; row++) {
      for (let col = 0; col < n; col++) {
        const i = row * n + col;
        const tr = row / (n - 1);
        const tc = col / (n - 1);
        const rr = Math.min(nFull - 1, Math.round(tr * (nFull - 1)));
        const cc = Math.min(nFull - 1, Math.round(tc * (nFull - 1)));
        const h = Number.isFinite(heights[rr][cc]) ? heights[rr][cc] : 0;
        // heights[ix][iy] — ix is game X, iy is game Y
        const wx = origin.x + tr * size;
        const wz = origin.y + tc * size;
        positions[i * 3] = wx;
        positions[i * 3 + 1] = h;
        positions[i * 3 + 2] = wz;
        // cell-normalised uv (the cover map uses it); detail tiling comes from
        // world position inside the terrain shader instead
        uvs[i * 2] = tr;
        uvs[i * 2 + 1] = tc;

        const hL = heights[Math.max(0, rr - step)][cc];
        const hR = heights[Math.min(nFull - 1, rr + step)][cc];
        const hD = heights[rr][Math.max(0, cc - step)];
        const hU = heights[rr][Math.min(nFull - 1, cc + step)];
        const slope = Math.hypot(hR - hL, hU - hD) / (2 * unit);
        let cr, cg, cb;
        if (coarse) {
          // continent view: altitude + slope tinting, kept in the game's soft
          // palette. The old curve turned every 320 m hill into a pure-white
          // blob that read as "clouds" against the sky.
          const snow = Math.min(1, Math.max(0, (h - 400) / 160)) * 0.8;
          const rock = Math.min(1, Math.max(0, (h - 170) / 150));
          const sand = h < water + 4 ? 0.8 : 0;
          const g = [0.42, 0.62, 0.3];
          const r = [0.55, 0.52, 0.47];
          const s = [0.85, 0.8, 0.62];
          const w = [0.78, 0.8, 0.82];
          const t = (idx2) =>
            (g[idx2] * (1 - rock) + r[idx2] * rock) * (1 - snow) + w[idx2] * snow;
          cr = (t(0) * (1 - sand) + s[0] * sand);
          cg = (t(1) * (1 - sand) + s[1] * sand);
          cb = (t(2) * (1 - sand) + s[2] * sand);
        } else {
          let rock = Math.min(1, Math.max(0, (slope - 0.4) * 2.1));
          let sand = h < water + 3.5 ? 0.85 : 0;
          if (h > lo + span * 0.72) rock = Math.min(1, rock + 0.4);
          // dirt patches: smooth low-frequency pockets (was per-vertex hash →
          // high-frequency checkerboard)
          const nz = valueNoise(wx * 0.016, wz * 0.016);
          const nz2 = valueNoise(wx * 0.0045 + 40, wz * 0.0045 - 17);
          let dirt = Math.max(0, (nz * 0.5 + nz2 * 0.5 - 0.66)) * 1.6 * (1 - rock);
          dirt = Math.min(0.5, dirt);
          // gentle large-scale grass/dirt mottling so flat ground isn't sterile
          const mot = valueNoise(wx * 0.0025 - 90, wz * 0.0025 + 33);
          dirt = Math.min(0.55, dirt + Math.max(0, mot - 0.62) * 0.5);
          let grass = Math.max(0, 1 - rock - sand - dirt);
          const sum = grass + sand + rock + dirt || 1;
          grass /= sum; sand /= sum; rock /= sum; dirt /= sum;
          blend[i * 4] = grass;
          blend[i * 4 + 1] = dirt;
          blend[i * 4 + 2] = sand;
          blend[i * 4 + 3] = rock;
          cr = GRASS_T[0] * grass + SAND_T[0] * sand + ROCK_T[0] * rock + 0.62 * dirt;
          cg = GRASS_T[1] * grass + SAND_T[1] * sand + ROCK_T[1] * rock + 0.5 * dirt;
          cb = GRASS_T[2] * grass + SAND_T[2] * sand + ROCK_T[2] * rock + 0.38 * dirt;
        }
        colors[i * 3] = cr;
        colors[i * 3 + 1] = cg;
        colors[i * 3 + 2] = cb;
      }
    }

    const idx = [];
    for (let row = 0; row < n - 1; row++) {
      for (let col = 0; col < n - 1; col++) {
        const a = row * n + col;
        const b = a + 1;
        const c = a + n;
        const d = c + 1;
        // CCW seen from +Y (three.js front face) — row→+x, col→+z
        idx.push(a, b, c, b, d, c);
      }
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    geo.setAttribute("uv", new THREE.BufferAttribute(uvs, 2));
    geo.setAttribute("aBlend", new THREE.BufferAttribute(blend, 4));
    geo.setIndex(idx);
    /* Seam-free normals: sample height across cell borders (global sampler)
     * instead of computeVertexNormals(), which only agrees inside one cell and
     * left a visible crease on every cell edge. */
    const maps = coarse ? this.ovmaps : this.hmaps;
    const e = unit; // metres between height samples for the slope step
    const normals = new Float32Array(verts * 3);
    for (let row = 0; row < n; row++) {
      for (let col = 0; col < n; col++) {
        const i = row * n + col;
        const wx = positions[i * 3];
        const wz = positions[i * 3 + 2];
        const hL = this.sampleH(maps, wx - e, wz, hm, origin);
        const hR = this.sampleH(maps, wx + e, wz, hm, origin);
        const hD = this.sampleH(maps, wx, wz - e, hm, origin);
        const hU = this.sampleH(maps, wx, wz + e, hm, origin);
        let nx = hL - hR;
        let ny = 2 * e;
        let nz = hD - hU;
        const inv = 1 / Math.max(1e-6, Math.hypot(nx, ny, nz));
        normals[i * 3] = nx * inv;
        normals[i * 3 + 1] = ny * inv;
        normals[i * 3 + 2] = nz * inv;
      }
    }
    geo.setAttribute("normal", new THREE.BufferAttribute(normals, 3));

    const mat = matOverride || this.makeTerrainMat(coverTex);
    const mesh = new THREE.Mesh(geo, mat);
    mesh.name = "terrain";
    mesh.userData = { kind: "terrain", cellId };
    mesh.receiveShadow = true;
    mesh.castShadow = false;
    mesh.frustumCulled = true;
    mesh.renderOrder = -1;
    return mesh;
  },
  buildWater(hm, origin, cellId) {
    const empty = new THREE.Group();
    empty.name = "water";
    empty.userData = { kind: "water", cellId };
    empty.visible = false;
    const waterZ = hm.water_level || 0;
    const heights = hm.heights;
    if (!heights || !heights.length) return empty;
    let below = 0;
    let total = 0;
    const step = Math.max(1, Math.floor(heights.length / 32));
    for (let r = 0; r < heights.length; r += step) {
      const row = heights[r];
      for (let c = 0; c < row.length; c += step) {
        total++;
        if (row[c] < waterZ + 1.25) below++;
      }
    }
    if (!total || below / total < 0.012) return empty;

    const size = (hm.width || 512) * (hm.unit_size || 2);
    /* Water follows the terrain on a fine (~8 m) grid so rivers and lakes
     * render as real shapes, not 64 m blobs. A quad is emitted wherever the
     * terrain sits below the water line; all quads merge into one mesh/call. */
    const grp = new THREE.Group();
    grp.name = "water";
    grp.userData = { kind: "water", cellId };
    grp.visible = state.showWater;
    const mat = new THREE.MeshStandardMaterial({
      color: 0x2f7fb5,
      transparent: true,
      opacity: 0.86,
      roughness: 0.22,
      metalness: 0.0,
      envMapIntensity: 0.5,
      depthWrite: true,
    });
    /* GPU ripple: perturb the surface normal with two travelling sine waves so
     * the env-map sun glint moves — the flat static sheet was the main reason
     * the sea read as "no water at all". */
    const wu = { uTime: { value: 0 } };
    mat.userData.waterUniforms = wu;
    (this.waterMats || (this.waterMats = [])).push(mat);
    mat.onBeforeCompile = (shader) => {
      shader.uniforms.uTime = wu.uTime;
      shader.vertexShader =
        "varying vec3 vWPos;\n" +
        shader.vertexShader.replace(
          "#include <begin_vertex>",
          "#include <begin_vertex>\n\tvWPos = (modelMatrix * vec4(transformed, 1.0)).xyz;",
        );
      shader.fragmentShader =
        "uniform float uTime;\nvarying vec3 vWPos;\n" +
        shader.fragmentShader.replace(
          "#include <normal_fragment_begin>",
          `#include <normal_fragment_begin>
           float wx1 = sin(vWPos.x * 0.12 + uTime * 1.3) * 0.55 + sin(vWPos.x * 0.031 - uTime * 0.6) * 0.45;
           float wz1 = cos(vWPos.z * 0.10 + uTime * 1.1) * 0.55 + sin(vWPos.z * 0.027 + uTime * 0.5) * 0.45;
           normal = normalize(normal + vec3(wx1, 0.0, wz1) * 0.22);`,
        );
    };
    mat.customProgramCacheKey = () => "waterripple";
    const H = heights.length;
    const N = Math.max(8, Math.min(128, Math.round(size / 8)));
    const span = size / N;
    const hScale = (H - 1) / size;
    const verts = [];
    const uvs = [];
    const idxs = [];
    let wet = 0;
    for (let gz = 0; gz < N; gz++) {
      for (let gx = 0; gx < N; gx++) {
        const cx = (gx + 0.5) * span;
        const cz = (gz + 0.5) * span;
        const hr = Math.max(0, Math.min(H - 1, Math.round(cz * hScale)));
        const hc = Math.max(0, Math.min(H - 1, Math.round(cx * hScale)));
        if (heights[hr][hc] < waterZ - 0.2) {
          wet++;
          const x0 = origin.x + gx * span;
          const z0 = origin.y + gz * span;
          const base = verts.length / 3;
          verts.push(x0, waterZ, z0, x0 + span, waterZ, z0, x0 + span, waterZ, z0 + span, x0, waterZ, z0 + span);
          uvs.push(gx * 0.25, gz * 0.25, (gx + 1) * 0.25, gz * 0.25, (gx + 1) * 0.25, (gz + 1) * 0.25, gx * 0.25, (gz + 1) * 0.25);
          idxs.push(base, base + 1, base + 2, base, base + 2, base + 3);
        }
      }
    }
    if (!wet) return empty;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(verts, 3));
    geo.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
    geo.setIndex(idxs);
    geo.computeVertexNormals();
    const water = new THREE.Mesh(geo, mat);
    water.userData = { kind: "water", cellId, base: Float32Array.from(verts) };
    water.frustumCulled = false;
    /* depthWrite:true so the sea occludes correctly against terrain and other
     * water instead of smearing translucent bands across the whole skybox */
    grp.add(water);
    (this.waterMeshes || (this.waterMeshes = [])).push(water);
    return grp;
  },
  animateWater(t) {
    /* the surface ripple is done entirely on the GPU (see the water material's
     * onBeforeCompile normal perturbation) — we only advance the time uniform.
     * The old CPU vertex loop re-uploaded ~65 k verts/frame and caused 5 fps
     * spikes whenever a water body was on screen. */
    if (this.waterMats) {
      for (const m of this.waterMats) {
        if (m.userData.waterUniforms) m.userData.waterUniforms.uTime.value = t;
      }
    }
  },
  applyFlags() {
    if (this.grid) {
      this.grid.visible = state.showGrid;
      if (state.world.cells[0]) {
        const o = state.world.cells[0].origin;
        this.grid.position.set(o.x + CELL_METERS / 2, 0.2, o.y + CELL_METERS / 2);
      }
    }
    this.worldGroup?.traverse((o) => {
      if (o.userData?.kind === "water") o.visible = state.showWater;
      if (o.userData?.volume) o.visible = state.showVolumes;
      if (o.userData?.debug) o.visible = state.showVolumes;
    });
  },
  terrainHeight(hm, u, v) {
    const h = hm?.heights;
    if (!h || !h.length) return hm?.water_level || 80;
    const n = h.length;
    /* exact bilinear sample at (u,v) — the old max-over-±40 m window lifted
     * props up to 40 m above the slope on hillsides (floating bushes). */
    const fx = Math.max(0, Math.min(n - 1.001, u * (n - 1)));
    const fy = Math.max(0, Math.min(n - 1.001, v * (n - 1)));
    const x0 = Math.floor(fx);
    const y0 = Math.floor(fy);
    const x1 = Math.min(n - 1, x0 + 1);
    const y1 = Math.min(n - 1, y0 + 1);
    const tx = fx - x0;
    const ty = fy - y0;
    const g = (a, b) => (Number.isFinite(h[a][b]) ? h[a][b] : 0);
    const h00 = g(x0, y0);
    const h10 = g(x1, y0);
    const h01 = g(x0, y1);
    const h11 = g(x1, y1);
    return (h00 * (1 - tx) + h10 * tx) * (1 - ty) + (h01 * (1 - tx) + h11 * tx) * ty;
  },
  sampleH(maps, wx, wz, fallbackHm, fallbackOrigin) {
    const cx = Math.floor(wx / CELL_METERS);
    const cy = Math.floor(wz / CELL_METERS);
    const id =
      String(Math.max(0, cx)).padStart(3, "0") + "_" + String(Math.max(0, cy)).padStart(3, "0");
    let hm = maps.get(id);
    let o = cellOrigin(id);
    if (!hm) {
      hm = fallbackHm;
      o = fallbackOrigin;
      if (!hm) return 0;
    }
    const h = hm.heights;
    const n = h.length;
    const us = hm.unit_size || 2;
    const fx = Math.max(0, Math.min(n - 1.001, (wx - o.x) / us));
    const fy = Math.max(0, Math.min(n - 1.001, (wz - o.y) / us));
    const x0 = Math.floor(fx);
    const y0 = Math.floor(fy);
    const tx = fx - x0;
    const ty = fy - y0;
    const h00 = h[x0][y0];
    const h10 = h[Math.min(n - 1, x0 + 1)][y0];
    const h01 = h[x0][Math.min(n - 1, y0 + 1)];
    const h11 = h[Math.min(n - 1, x0 + 1)][Math.min(n - 1, y0 + 1)];
    return (h00 * (1 - tx) + h10 * tx) * (1 - ty) + (h01 * (1 - tx) + h11 * tx) * ty;
  },
};
