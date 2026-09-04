/* Texture / mesh prototype cache — methods mixed into WorldViewport. */
import * as THREE from "three";
import { state } from "./state.js";

export const assetMethods = {
  async loadTex(url, repeat) {
    if (!url) return null;
    const key = url + "|" + (repeat || 1);
    if (this.texLib.has(key)) return this.texLib.get(key);
    const p = new Promise((resolve, reject) => {
      new THREE.TextureLoader().load(
        url,
        (t) => {
          t.wrapS = t.wrapT = THREE.RepeatWrapping;
          t.anisotropy = this.maxAniso || 8;
          t.encoding = THREE.sRGBEncoding;
          // DDS/PNG is top-down like CryEngine UVs; do not flip for WebGL.
          t.flipY = false;
          const r = repeat || 1;
          t.repeat.set(r, r);
          t.userData = { src: url };
          resolve(t);
        },
        undefined,
        () => resolve(null),
      );
    });
    this.texLib.set(key, p);
    return p;
  },
  async matFromSubset(s) {
    const map = s.texture ? await this.loadTex("cache/" + s.texture, 1) : null;
    const alpha = s.alphaTest > 0;
    return new THREE.MeshLambertMaterial({
      map: map || null,
      color: map ? 0xffffff : 0xb0a28c,
      alphaTest: alpha ? Math.min(0.33, Math.max(0.15, s.alphaTest)) : 0,
      transparent: false,
      depthWrite: true,
      /* CryEngine brushes are authored with inconsistent winding (and many
       * facades are single-sided); culling backfaces left holes you could see
       * straight through buildings. Editor > fill-rate: draw both sides. */
      side: THREE.DoubleSide,
    });
  },
  async getMeshProto(rel) {
    if (!rel) return null;
    const url = rel.startsWith("cache/") ? rel : "cache/" + rel;
    if (this.meshLib.has(url)) return this.meshLib.get(url);
    const p = (async () => {
      const r = await fetch(url);
      if (!r.ok) return null;
      const j = await r.json();
      const geo = new THREE.BufferGeometry();
      geo.setAttribute(
        "position",
        new THREE.Float32BufferAttribute(j.positions, 3),
      );
      if (j.normals && j.normals.length) {
        geo.setAttribute("normal", new THREE.Float32BufferAttribute(j.normals, 3));
      } else geo.computeVertexNormals();
      if (j.uvs && j.uvs.length) {
        geo.setAttribute("uv", new THREE.Float32BufferAttribute(j.uvs, 2));
      }
      const idx = Array.isArray(j.indices) ? j.indices.slice() : Array.from(j.indices);
      geo.setIndex(idx);
      const mats = [];
      for (let i = 0; i < (j.subsets || []).length; i++) {
        const s = j.subsets[i];
        if (!s.indexCount) continue;
        geo.addGroup(s.firstIndex, s.indexCount, mats.length);
        mats.push(await this.matFromSubset(s));
      }
      if (!mats.length) {
        mats.push(
          new THREE.MeshStandardMaterial({ color: 0x8a9a6a, roughness: 0.85 }),
        );
      }
      return { geo, mats };
    })();
    this.meshLib.set(url, p);
    return p;
  },
  async loadCover(worldId, cellId) {
    /* per-cell baked terrain map (cover.ctc) if the manifest lists one */
    const man = state.manifest;
    if (!man) return null;
    const w = (man.worlds || []).find((x) => x.id === worldId);
    const entry = (w?.cells || man.cells || []).find((c) => c.id === cellId);
    if (!entry || !entry.cover) return null;
    return await this.loadTex("cache/" + entry.cover, 1);
  },
  async setTerrainMaps(layers) {
    this.terrainMaps = layers || {};
    if (layers && layers.grass) {
      const t = await this.loadTex("cache/" + layers.grass, 1);
      if (t) this.groundTex = t;
    }
    if (layers && layers.dirt) {
      this.dirtTex = await this.loadTex("cache/" + layers.dirt, 1);
    }
    if (layers && layers.rock) {
      this.rockTex = await this.loadTex("cache/" + layers.rock, 1);
    }
    if (layers && layers.sand) {
      this.sandTex = await this.loadTex("cache/" + layers.sand, 1);
    }
  },
};
