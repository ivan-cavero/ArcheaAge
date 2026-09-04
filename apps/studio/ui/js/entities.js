/* Brushes, vegetation, NPCs, doodads, picking — methods mixed into WorldViewport. */
import * as THREE from "three";
import {
  CELL_METERS,
  cellOrigin,
  emit,
  isVolumeClass,
  state,
  toWorldPos,
} from "./state.js";

export const entityMethods = {
  splitSubsets(proto) {
    const geo = proto.geo;
    const mats = proto.mats || [];
    const groups = geo.groups || [];
    if (!groups.length || mats.length <= 1) {
      return [{ geo, mat: mats[0] || new THREE.MeshStandardMaterial({ color: 0x6d7a4a }) }];
    }
    const out = [];
    for (const g of groups) {
      const sg = new THREE.BufferGeometry();
      sg.setAttribute("position", geo.attributes.position);
      if (geo.attributes.normal) sg.setAttribute("normal", geo.attributes.normal);
      if (geo.attributes.uv) sg.setAttribute("uv", geo.attributes.uv);
      const idx = geo.index;
      if (idx) {
        const slice = idx.array.slice(g.start, g.start + g.count);
        sg.setIndex(new THREE.BufferAttribute(slice, 1));
      }
      out.push({ geo: sg, mat: mats[g.materialIndex] || mats[0] });
    }
    return out;
  },
  async addBaked(baked, cellId) {
    const group = this.cellGroups.get(cellId) || this.worldGroup;
    group.userData.baked = baked;
    group.userData.origin = cellOrigin(cellId);
    await this.spawnBrushes(baked, cellId, group);
    await this.spawnVegetation(baked, cellId, group);
    await this.spawnActors(baked, cellId, group);
    this.hideOverviewCell(cellId);
  },
  _dsMats(proto) {
    if (!proto.dsMats) {
      proto.dsMats = proto.mats.map((m) => {
        const c = m.clone();
        c.side = THREE.DoubleSide;
        return c;
      });
    }
    return proto.dsMats;
  },
  _vegFadeMat(baseMat) {
    if (baseMat.userData.vegFade) return baseMat.userData.vegFade;
    const c = baseMat.clone();
    c.side = THREE.DoubleSide;
    c.transparent = false;
    c.depthWrite = true;
    c.userData.vegFadeSrc = true;
    c.onBeforeCompile = (shader) => {
      shader.vertexShader =
        "varying vec3 vFadePos;\n" +
        shader.vertexShader.replace(
          "#include <begin_vertex>",
          "#include <begin_vertex>\n\tvFadePos = (modelMatrix * instanceMatrix * vec4(transformed,1.0)).xyz;",
        );
      shader.fragmentShader =
        "varying vec3 vFadePos;\nuniform vec3 uCamPos;\n" +
        shader.fragmentShader.replace(
          "#include <clipping_planes_fragment>",
          `#include <clipping_planes_fragment>
           float fd = length(vFadePos - uCamPos);
           float fade = clamp(1.0 - (fd - 480.0) / 260.0, 0.0, 1.0);
           vec2 dd = floor(mod(gl_FragCoord.xy, vec2(4.0)));
           float h = mod(dd.x + dd.y * 2.0 + floor(vFadePos.x*0.5+vFadePos.z*0.7), 4.0);
           if (h / 4.0 > fade) discard;`,
        );
      shader.uniforms.uCamPos = this._camUniform;
    };
    c.customProgramCacheKey = () => "vegfade";
    baseMat.userData.vegFade = c;
    return c;
  },
  _cullGeo(geo, center, radius) {
    const g2 = new THREE.BufferGeometry();
    for (const k in geo.attributes) g2.setAttribute(k, geo.attributes[k]);
    g2.index = geo.index;
    g2.groups = geo.groups;
    g2.boundingSphere = new THREE.Sphere(center.clone(), radius);
    return g2;
  },
  _bucketize(items, posFn, size = 512, maxList = 96) {
    if (items.length <= maxList) return [{ center: null, list: items }];
    const map = new Map();
    for (const it of items) {
      const [x, y] = posFn(it);
      const key = Math.floor(x / size) + "_" + Math.floor(y / size);
      let b = map.get(key);
      if (!b) map.set(key, (b = []));
      b.push(it);
    }
    const out = [];
    for (const [key, list] of map) {
      const [bx, by] = key.split("_").map(Number);
      out.push({ center: [(bx + 0.5) * size, (by + 0.5) * size], list });
    }
    return out;
  },
  async spawnBrushes(baked, cellId, group) {
    const origin = group.userData.origin || cellOrigin(cellId);
    const byMesh = new Map();
    for (const obj of baked.objects || []) {
      if (!obj.mesh) continue;
      if (!byMesh.has(obj.mesh)) byMesh.set(obj.mesh, []);
      byMesh.get(obj.mesh).push(obj);
    }
    const tmpM = new THREE.Matrix4();
    const tmpP = new THREE.Vector3();
    for (const [rel, all] of byMesh) {
      const proto = await this.getMeshProto(rel);
      if (!proto) continue;
      if (proto.geo.boundingSphere == null) proto.geo.computeBoundingSphere();
      const modelR = proto.geo.boundingSphere ? proto.geo.boundingSphere.radius * 2.2 : 20;
      const buckets = this._bucketize(all, (o) => [o.matrix[12], o.matrix[14]]);
      for (const { center: bc, list } of buckets) {
        const cw = bc
          ? new THREE.Vector3(origin.x + bc[0], 0, origin.y + bc[1])
          : new THREE.Vector3(origin.x + CELL_METERS / 2, 0, origin.y + CELL_METERS / 2);
        const invC = new THREE.Matrix4().makeTranslation(-cw.x, 0, -cw.z);
        const im = new THREE.InstancedMesh(proto.geo, proto.mats, list.length);
        im.position.copy(cw);
        im.castShadow = true;
        im.receiveShadow = true;
        im.userData = { kind: "brush-group", cellId, model: list[0].model, items: [] };
        let maxR = 0;
        for (let i = 0; i < list.length; i++) {
          const obj = list[i];
          const m4 = new THREE.Matrix4().fromArray(obj.matrix);
          m4.elements[12] += origin.x;
          m4.elements[14] += origin.y;
          im.userData.items.push({ model: obj.model, matrix: m4.elements.slice() });
          tmpM.copy(m4).premultiply(invC);
          im.setMatrixAt(i, tmpM);
          tmpP.setFromMatrixPosition(m4);
          maxR = Math.max(maxR, Math.hypot(tmpP.x - cw.x, tmpP.z - cw.z));
        }
        im.instanceMatrix.needsUpdate = true;
        im.geometry = this._cullGeo(proto.geo, new THREE.Vector3(0, 0, 0), maxR + modelR);
        im.matrixAutoUpdate = false;
        im.updateMatrix();
        group.add(im);
      }
    }
  },
  async spawnVegetation(baked, cellId, group) {
    const origin = group.userData.origin || cellOrigin(cellId);
    const hm = group.userData.data?.heightmap || null;
    const byMesh = new Map();
    for (const v of baked.vegetation || []) {
      if (!v.mesh) continue;
      if (!byMesh.has(v.mesh)) byMesh.set(v.mesh, []);
      byMesh.get(v.mesh).push(v);
    }
    const dummy = new THREE.Object3D();
    for (const [rel, all] of byMesh) {
      const proto = await this.getMeshProto(rel);
      if (!proto) continue;
      const parts = this.splitSubsets(proto);
      const buckets = this._bucketize(all, (v) => v.pos);
      for (const { center: bc, list } of buckets) {
        const cw = bc
          ? new THREE.Vector3(origin.x + bc[0], 0, origin.y + bc[1])
          : new THREE.Vector3(origin.x + CELL_METERS / 2, 0, origin.y + CELL_METERS / 2);
        const invC = new THREE.Matrix4().makeTranslation(-cw.x, 0, -cw.z);
        for (const part of parts) {
        const baseMat =
          part.mat.side === THREE.DoubleSide
            ? part.mat
            : this._dsMats({ mats: [part.mat] })[0];
        const mat = this._vegFadeMat(baseMat);
        const im = new THREE.InstancedMesh(part.geo, mat, list.length);
        im.castShadow = false;
        im.receiveShadow = true;
        im.position.copy(cw);
        im.userData = { kind: "veg", cellId, model: list[0].model };
        let maxR = 0;
        for (let i = 0; i < list.length; i++) {
          const v = list[i];
          dummy.position.set(origin.x + v.pos[0], 0, origin.y + v.pos[1]);
          const y = hm ? this.terrainHeight(hm, v.pos[0] / CELL_METERS, v.pos[1] / CELL_METERS) : v.pos[2];
          dummy.position.y = Number.isFinite(y) ? y : v.pos[2];
          dummy.rotation.set(0, v.yaw || 0, 0);
          const s = Math.abs(v.scale || 1) || 1;
          dummy.scale.set(s, s, s);
          dummy.updateMatrix();
          im.setMatrixAt(i, dummy.matrix.clone().premultiply(invC));
          maxR = Math.max(maxR, Math.hypot(dummy.position.x - cw.x, dummy.position.z - cw.z));
        }
        im.instanceMatrix.needsUpdate = true;
        if (part.geo.boundingSphere == null) part.geo.computeBoundingSphere();
        const modelR = part.geo.boundingSphere ? part.geo.boundingSphere.radius * 2.5 : 15;
        im.geometry = this._cullGeo(part.geo, new THREE.Vector3(0, 0, 0), maxR + modelR);
        im.matrixAutoUpdate = false;
        im.updateMatrix();
        group.add(im);
        }
      }
    }
  },
  async spawnActors(baked, cellId, group) {
    if (!this._npcGeo) {
      this._npcGeo = new THREE.CapsuleGeometry(0.42, 1.15, 3, 6);
      this._npcMat = new THREE.MeshStandardMaterial({
        color: 0xe4b45c,
        roughness: 0.55,
        metalness: 0.05,
        emissive: 0x6a4c10,
        emissiveIntensity: 0.35,
      });
      this._ddGeo = new THREE.BoxGeometry(0.85, 0.85, 0.85);
      this._ddMat = new THREE.MeshStandardMaterial({
        color: 0xa98456,
        roughness: 0.75,
      });
      this._ringGeo = new THREE.RingGeometry(2.2, 3.1, 24);
      this._ringGeo.rotateX(-Math.PI / 2);
      this._ringMat = new THREE.MeshBasicMaterial({
        color: 0xffb020,
        transparent: true,
        opacity: 0.6,
        depthWrite: false,
        side: THREE.DoubleSide,
      });
      this._npcMats = {
        hostile: new THREE.MeshStandardMaterial({
          color: 0xd05048,
          roughness: 0.5,
          emissive: 0x5a1410,
          emissiveIntensity: 0.35,
        }),
        elite: new THREE.MeshStandardMaterial({
          color: 0xb04ad0,
          roughness: 0.5,
          emissive: 0x3a0a52,
          emissiveIntensity: 0.35,
        }),
        friendly: new THREE.MeshStandardMaterial({
          color: 0x62c46a,
          roughness: 0.5,
          emissive: 0x0d3a12,
          emissiveIntensity: 0.3,
        }),
        neutral: new THREE.MeshStandardMaterial({
          color: 0xe4c25c,
          roughness: 0.5,
          emissive: 0x4a3a10,
          emissiveIntensity: 0.3,
        }),
      };
      this._zoneGeo = new THREE.CircleGeometry(1, 40);
      this._zoneGeo.rotateX(-Math.PI / 2);
      this._zoneMats = {
        hostile: new THREE.MeshBasicMaterial({
          color: 0xff4030,
          transparent: true,
          opacity: 0.08,
          depthWrite: false,
          side: THREE.DoubleSide,
        }),
        calm: new THREE.MeshBasicMaterial({
          color: 0x40c070,
          transparent: true,
          opacity: 0.07,
          depthWrite: false,
          side: THREE.DoubleSide,
        }),
      };
      this._ringGeoBig = new THREE.RingGeometry(3.2, 3.9, 40);
      this._ringGeoBig.rotateX(-Math.PI / 2);
      this._edgeMats = {
        hostile: new THREE.MeshBasicMaterial({
          color: 0xff5a3c,
          transparent: true,
          opacity: 0.85,
          depthWrite: false,
          side: THREE.DoubleSide,
        }),
        calm: new THREE.MeshBasicMaterial({
          color: 0x53e07a,
          transparent: true,
          opacity: 0.8,
          depthWrite: false,
          side: THREE.DoubleSide,
        }),
      };
      this._beamGeo = new THREE.CylinderGeometry(0.5, 0.5, 18, 6, 1, true);
      this._beamMat = new THREE.MeshBasicMaterial({
        color: 0xff3020,
        transparent: true,
        opacity: 0.32,
        depthWrite: false,
        side: THREE.DoubleSide,
      });
    }
    const npcs = baked.npcs || [];
    const showOv = state.showVolumes;
    const rings = new THREE.InstancedMesh(this._ringGeo, this._ringMat, npcs.length);
    rings.userData = { kind: "spawn-ring", cellId, debug: true };
    rings.frustumCulled = false;
    rings.visible = showOv;
    const dummy = new THREE.Object3D();
    npcs.forEach((n, i) => {
      const p = n.pos || [0, 0, 0];
      dummy.position.set(p[0], p[2] + 0.25, p[1]);
      dummy.updateMatrix();
      rings.setMatrixAt(i, dummy.matrix);
    });
    if (npcs.length) {
      rings.instanceMatrix.needsUpdate = true;
      group.add(rings);
    }
    /* Real character models + doodad models: one InstancedMesh per unique baked
     * mesh (huge draw-call saving vs individual meshes). Selection resolves the
     * instanceId back to the entity record. Capsules/cubes remain as fallback. */
    const protos = new Map();
    for (const n of npcs) {
      if (!n.mesh) continue;
      if (!protos.has(n.mesh)) protos.set(n.mesh, await this.getMeshProto(n.mesh));
    }
    const ddProtos = new Map();
    for (const d of baked.doodads || []) {
      if (!d.mesh) continue;
      if (!ddProtos.has(d.mesh)) ddProtos.set(d.mesh, await this.getMeshProto(d.mesh));
    }
    const origin = group.userData.origin || cellOrigin(cellId);
    const center = new THREE.Vector3(origin.x + CELL_METERS / 2, 0, origin.y + CELL_METERS / 2);
    const invC = new THREE.Matrix4().makeTranslation(-center.x, 0, -center.z);
    const dm = new THREE.Object3D();

    const npcByMesh = new Map();
    const capsuleNpcs = [];
    for (const n of npcs) {
      const proto = n.mesh ? protos.get(n.mesh) : null;
      if (proto && proto.geo) {
        if (!npcByMesh.has(n.mesh)) npcByMesh.set(n.mesh, []);
        npcByMesh.get(n.mesh).push(n);
      } else {
        capsuleNpcs.push(n);
      }
    }
    for (const [rel, list] of npcByMesh) {
      const proto = protos.get(rel);
      const im = new THREE.InstancedMesh(proto.geo, proto.mats, list.length);
      im.position.copy(center);
      im.castShadow = false;
      im.receiveShadow = true;
      im.userData = { kind: "npc-group", cellId, items: [] };
      let maxR = 0;
      list.forEach((n, i) => {
        const p = n.pos || [0, 0, 0];
        const gs = 1 + Math.min(1.5, ((n.grade || 1) - 1) * 0.15);
        dm.position.set(p[0], p[2], p[1]);
        dm.rotation.set(0, ((n.yaw || 0) * Math.PI) / 180, 0);
        dm.scale.set(gs, gs, gs);
        dm.updateMatrix();
        im.setMatrixAt(i, new THREE.Matrix4().copy(dm.matrix).premultiply(invC));
        im.userData.items.push({ entity: n, unitId: n.unitId });
        maxR = Math.max(maxR, Math.hypot(p[0] - center.x, p[1] - center.z));
      });
      im.instanceMatrix.needsUpdate = true;
      if (proto.geo.boundingSphere == null) proto.geo.computeBoundingSphere();
      const mr = proto.geo.boundingSphere ? proto.geo.boundingSphere.radius * 2.5 : 6;
      im.geometry = this._cullGeo(proto.geo, new THREE.Vector3(), maxR + mr);
      group.add(im);
    }
    for (const n of capsuleNpcs) {
      const p = n.pos || [0, 0, 0];
      const hostile = !!n.aggr;
      const elite = hostile && (n.grade || 1) >= 4;
      const mat = elite
        ? this._npcMats.elite
        : hostile
          ? this._npcMats.hostile
          : (n.name || "").trim()
            ? this._npcMats.friendly
            : this._npcMats.neutral;
      const m = new THREE.Mesh(this._npcGeo, mat);
      const gs = 1 + Math.min(2, (n.grade || 1) * 0.18);
      m.scale.set(gs, gs, gs);
      m.position.set(p[0], p[2] + 0.95 * gs, p[1]);
      m.rotation.y = ((n.yaw || 0) * Math.PI) / 180;
      m.userData = { kind: "npc", unitId: n.unitId, cellId, entity: n };
      m.castShadow = true;
      group.add(m);
      this.entityMeshes.push(m);
    }
    /* doodads: instanced by model */
    const ddByMesh = new Map();
    const ddInstanced = new Set();
    const cubeDds = [];
    for (const d of baked.doodads || []) {
      const proto = d.mesh ? ddProtos.get(d.mesh) : null;
      if (proto && proto.geo) {
        if (!ddByMesh.has(d.mesh)) ddByMesh.set(d.mesh, []);
        ddByMesh.get(d.mesh).push(d);
        ddInstanced.add(d);
      } else {
        cubeDds.push(d);
      }
    }
    for (const [rel, list] of ddByMesh) {
      const proto = ddProtos.get(rel);
      const im = new THREE.InstancedMesh(proto.geo, proto.mats, list.length);
      im.position.copy(center);
      im.castShadow = false;
      im.receiveShadow = true;
      im.userData = { kind: "doodad-group", cellId, items: [] };
      let maxR = 0;
      list.forEach((d, i) => {
        const p = d.pos || [0, 0, 0];
        dm.position.set(p[0], p[2], p[1]);
        dm.rotation.set(0, ((d.yaw || 0) * Math.PI) / 180, 0);
        dm.scale.set(1, 1, 1);
        dm.updateMatrix();
        im.setMatrixAt(i, new THREE.Matrix4().copy(dm.matrix).premultiply(invC));
        im.userData.items.push({ entity: d, unitId: d.unitId, title: d.title });
        maxR = Math.max(maxR, Math.hypot(p[0] - center.x, p[1] - center.z));
      });
      im.instanceMatrix.needsUpdate = true;
      if (proto.geo.boundingSphere == null) proto.geo.computeBoundingSphere();
      const mr = proto.geo.boundingSphere ? proto.geo.boundingSphere.radius * 2.5 : 4;
      im.geometry = this._cullGeo(proto.geo, new THREE.Vector3(), maxR + mr);
      group.add(im);
    }
    for (const d of cubeDds) {
      const p = d.pos || [0, 0, 0];
      const m = new THREE.Mesh(this._ddGeo, this._ddMat);
      m.position.set(p[0], p[2] + 0.4, p[1]);
      m.userData = { kind: "doodad", unitId: d.unitId, title: d.title, cellId, entity: d };
      group.add(m);
      this.entityMeshes.push(m);
    }
    /* spawn zones: cluster nearby spawns (union-find, 45 m radius) and draw a
     * translucent disc — red = contains hostile spawns, green = peaceful */
    if (npcs.length > 1) {
      const parent = npcs.map((_, i) => i);
      const find = (i) => {
        while (parent[i] !== i) {
          parent[i] = parent[parent[i]];
          i = parent[i];
        }
        return i;
      };
      const R = 26;
      const grid = new Map();
      npcs.forEach((n, i) => {
        const key = Math.floor(n.pos[0] / R) + "_" + Math.floor(n.pos[1] / R);
        if (!grid.has(key)) grid.set(key, []);
        grid.get(key).push(i);
        for (let dx = -1; dx <= 1; dx++) {
          for (let dy = -1; dy <= 1; dy++) {
            const near = grid.get(
              Math.floor(n.pos[0] / R) + dx + "_" + (Math.floor(n.pos[1] / R) + dy),
            );
            for (const j of near || []) {
              const a = find(i),
                b = find(j);
              if (a !== b) parent[a] = b;
            }
          }
        }
      });
      const clusters = new Map();
      npcs.forEach((n, i) => {
        const r = find(i);
        if (!clusters.has(r)) clusters.set(r, []);
        clusters.get(r).push(n);
      });
      for (const list of clusters.values()) {
        if (list.length < 2) continue;
        let cx = 0,
          cz = 0,
          hostile = false;
        for (const n of list) {
          cx += n.pos[0];
          cz += n.pos[1];
          if (n.aggr) hostile = true;
        }
        cx /= list.length;
        cz /= list.length;
        let rad = 8;
        for (const n of list) {
          rad = Math.max(rad, Math.hypot(n.pos[0] - cx, n.pos[1] - cz) + 5);
        }
        rad = Math.min(rad, 45); // cap so clusters don't become giant blobs
        const disc = new THREE.Mesh(
          this._zoneGeo,
          hostile ? this._zoneMats.hostile : this._zoneMats.calm,
        );
        disc.scale.set(rad, 1, rad);
        disc.position.set(cx, (list[0].pos[2] || 0) + 0.4, cz);
        disc.userData = {
          kind: "spawn-zone",
          cellId,
          debug: true,
          entity: { count: list.length, hostile, name: list[0].name || "" },
        };
        disc.renderOrder = -0.5;
        disc.visible = showOv;
        group.add(disc);
        /* bright outline ring so the zone edge reads clearly over grass */
        const edge = new THREE.Mesh(
          this._ringGeoBig,
          hostile ? this._edgeMats.hostile : this._edgeMats.calm,
        );
        edge.scale.set(rad / 3.6, 1, rad / 3.6);
        edge.position.set(cx, (list[0].pos[2] || 0) + 0.5, cz);
        edge.userData = { kind: "spawn-zone", cellId, debug: true, entity: disc.userData.entity };
        edge.visible = showOv;
        group.add(edge);
      }
    }
    /* vertical beams over hostile NPCs — visible from far above/through the
     * city clutter so enemy spawns are impossible to miss */
    const hostiles = npcs.filter((n) => n.aggr);
    if (hostiles.length) {
      const beams = new THREE.InstancedMesh(this._beamGeo, this._beamMat, hostiles.length);
      beams.frustumCulled = false;
      beams.userData = { kind: "npc-beam", cellId, debug: true };
      beams.visible = showOv;
      hostiles.forEach((n, i) => {
        const p = n.pos || [0, 0, 0];
        dummy.position.set(p[0], p[2] + 9, p[1]);
        dummy.rotation.set(0, 0, 0);
        dummy.scale.set(1, 1, 1);
        dummy.updateMatrix();
        beams.setMatrixAt(i, dummy.matrix);
      });
      beams.instanceMatrix.needsUpdate = true;
      group.add(beams);
    }
    for (const d of baked.doodads || []) {
      const p = d.pos || [0, 0, 0];
      const proto = d.mesh ? ddProtos.get(d.mesh) : null;
      let m;
      const instanced = ddInstanced.has(d);
      if (instanced) {
        /* already drawn by the doodad-group InstancedMesh above — keep only an
         * invisible proxy so outliner selection/focus still resolves to it.
         * (Rendering it twice was 3.4k extra draw calls.) */
        m = new THREE.Object3D();
        m.position.set(p[0], p[2], p[1]);
      } else if (proto && proto.geo) {
        m = new THREE.Mesh(proto.geo, proto.mats);
        m.position.set(p[0], p[2], p[1]);
        m.rotation.y = ((d.yaw || 0) * Math.PI) / 180;
      } else {
        m = new THREE.Mesh(this._ddGeo, this._ddMat);
        m.position.set(p[0], p[2] + 0.4, p[1]);
      }
      m.userData = {
        kind: "doodad",
        unitId: d.unitId,
        title: d.title,
        cellId,
        entity: d,
      };
      group.add(m);
      this.entityMeshes.push(m);
    }
  },
  buildEntity(ent, origin, cellId) {
    const [gx, gy, gz] = toWorldPos(ent.pos, origin);
    const [sx, sy, sz] = ent.scale || [1, 1, 1];
    const cls = ent.class || "Entity";
    const volume = isVolumeClass(cls);

    let geo;
    let color = 0xc4a35a;
    if ((cls || "").toLowerCase().includes("light")) {
      geo = new THREE.SphereGeometry(1.6, 10, 10);
      color = 0xffe08a;
    } else if ((cls || "").toLowerCase().includes("particle")) {
      geo = new THREE.OctahedronGeometry(1.8, 0);
      color = 0x7ec8e3;
    } else if ((cls || "").toLowerCase().includes("fish")) {
      geo = new THREE.ConeGeometry(1.4, 4.5, 6);
      color = 0x5aa0c8;
    } else if (volume) {
      geo = new THREE.BoxGeometry(8, 2, 8);
      color = 0x9b7ad4;
    } else {
      geo = new THREE.BoxGeometry(2.4, 4.8, 2.4);
    }

    const mat = new THREE.MeshStandardMaterial({
      color,
      roughness: 0.55,
      metalness: 0.05,
      transparent: volume,
      opacity: volume ? 0.35 : 1,
      emissive: (cls || "").toLowerCase().includes("light")
        ? new THREE.Color(0xffcc66)
        : new THREE.Color(0x000000),
      emissiveIntensity: (cls || "").toLowerCase().includes("light") ? 0.8 : 0,
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(gx, gz + (volume ? 0 : 2.4), gy);
    mesh.scale.set(Math.max(0.2, sx), Math.max(0.2, sz), Math.max(0.2, sy));
    const local =
      (ent.pos?.[0] ?? 0) < CELL_METERS + 64 &&
      (ent.pos?.[1] ?? 0) < CELL_METERS + 64;
    mesh.userData = {
      kind: "entity",
      entity: ent,
      origin,
      cellId,
      volume,
      local,
    };
    mesh.visible = !volume || state.showVolumes;

    const [rw, rx, ry, rz] = ent.rotate || [1, 0, 0, 0];
    mesh.quaternion.set(rx, rz, ry, rw);

    this.entityMeshes.push(mesh);
    return mesh;
  },
  selectMesh(mesh) {
    if (this._brushProxy && (!mesh || mesh !== this._brushProxy)) {
      this.scene.remove(this._brushProxy);
      this._brushProxy = null;
    }
    if (this.transform.object && this.transform.object !== mesh) {
      this.transform.detach();
    }
    if (!mesh) {
      this.transform.detach();
      state.selected = null;
      emit("select", null);
      return;
    }
    const kind = mesh.userData.kind;
    if (kind === "entity" || kind === "brush" || kind === "npc" || kind === "doodad") {
      this.transform.attach(mesh);
      this.transform.visible = true;
      this.transform.setMode(state.gizmo);
    } else {
      this.transform.detach();
    }
    state.selected = {
      kind,
      cellId: mesh.userData.cellId,
      entity: mesh.userData.entity,
      model: mesh.userData.model,
      mesh,
    };
    emit("select", state.selected);
  },
  selectEntity(entity, cellId) {
    const mesh = this.entityMeshes.find(
      (m) => m.userData.entity === entity && m.userData.cellId === cellId,
    );
    if (mesh) {
      this.selectMesh(mesh);
      this.focus(mesh);
    }
  },
  syncSelectedFromMesh() {
    const mesh = this.transform.object;
    if (!mesh) return;
    if (mesh.userData?.brush) {
      const { im, instanceId, item } = mesh.userData.brush;
      const m = new THREE.Matrix4().compose(
        mesh.position,
        mesh.quaternion,
        mesh.scale,
      );
      item.matrix = m.elements.slice();
      const invC = new THREE.Matrix4().makeTranslation(-im.position.x, 0, -im.position.z);
      im.setMatrixAt(instanceId, new THREE.Matrix4().copy(m).premultiply(invC));
      im.instanceMatrix.needsUpdate = true;
      emit("entity-moved", { entity: item, cellId: mesh.userData.cellId });
      return;
    }
    if (!mesh.userData?.entity) return;
    const ent = mesh.userData.entity;
    const origin = mesh.userData.origin;
    const yOff = mesh.userData.volume ? 0 : 2.4;
    const gx = mesh.position.x;
    const gy = mesh.position.z;
    const gz = mesh.position.y - yOff;
    ent.pos = mesh.userData.local
      ? [gx - origin.x, gy - origin.y, gz]
      : [gx, gy, gz];
    emit("entity-moved", { entity: ent, cellId: mesh.userData.cellId });
  },
  onPointerDown(e) {
    if (e.button !== 0) return;
    if (this.transform.dragging || this.transform.axis) return;
    const rect = this.renderer.domElement.getBoundingClientRect();
    const mouse = new THREE.Vector2(
      ((e.clientX - rect.left) / rect.width) * 2 - 1,
      -((e.clientY - rect.top) / rect.height) * 2 + 1,
    );
    const ray = new THREE.Raycaster();
    ray.setFromCamera(mouse, this.camera);
    const pickables = this.entityMeshes.filter((m) => m.visible);
    this.worldGroup.traverse((o) => {
      const k = o.userData?.kind;
      if (o.isInstancedMesh && (k === "brush-group" || k === "veg" || k === "npc-group" || k === "doodad-group")) pickables.push(o);
    });
    const hits = ray.intersectObjects(pickables, true);
    if (hits.length) {
      let m = hits[0].object;
      while (m && !m.userData?.kind) m = m.parent;
      const k = m?.userData?.kind;
      if (k === "brush-group") {
        this.selectBrushInstance(m, hits[0].instanceId);
        return;
      }
      if (k === "npc-group" || k === "doodad-group") {
        const item = m.userData.items && m.userData.items[hits[0].instanceId];
        if (item) {
          state.selected = {
            kind: k === "npc-group" ? "npc" : "doodad",
            cellId: m.userData.cellId,
            entity: item.entity,
            mesh: null,
          };
          this.transform.detach();
          emit("select", state.selected);
          return;
        }
      }
      this.selectMesh(m);
      return;
    }
    this.selectMesh(null);
  },
  selectBrushInstance(im, instanceId) {
    const item = im.userData.items && im.userData.items[instanceId];
    if (!item) return this.selectMesh(null);
    if (this._brushProxy) this.scene.remove(this._brushProxy);
    const proxy = new THREE.Object3D();
    const m = new THREE.Matrix4().fromArray(item.matrix);
    m.decompose(proxy.position, proxy.quaternion, proxy.scale);
    proxy.userData = {
      kind: "brush",
      model: item.model,
      cellId: im.userData.cellId,
      brush: { im, instanceId, item },
    };
    this._brushProxy = proxy;
    this.scene.add(proxy);
    this.transform.attach(proxy);
    this.transform.visible = true;
    this.transform.setMode(state.gizmo);
    state.selected = {
      kind: "brush",
      cellId: im.userData.cellId,
      model: item.model,
      mesh: proxy,
    };
    emit("select", state.selected);
  },
};
