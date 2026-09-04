/* Sky, sun, weather, env-map — methods mixed into WorldViewport. */
import * as THREE from "three";
import { state } from "./state.js";

export function installLightsAndSky(vp) {
  const hemi = new THREE.HemisphereLight(0xcfe4ff, 0x8f7f63, 0.55);
  vp.scene.add(hemi);
  vp.hemi = hemi;
  vp.amb = new THREE.AmbientLight(0x30404f, 0.15);
  vp.scene.add(vp.amb);
  const sun = new THREE.DirectionalLight(0xffefd6, 1.45);
  sun.position.set(600, 900, 280);
  sun.castShadow = true;
  sun.shadow.mapSize.set(1024, 1024);
  sun.shadow.camera.near = 50;
  sun.shadow.camera.far = 1600;
  sun.shadow.camera.left = -280;
  sun.shadow.camera.right = 280;
  sun.shadow.camera.top = 280;
  sun.shadow.camera.bottom = -280;
  sun.shadow.bias = -0.0006;
  sun.shadow.normalBias = 1.5;
  vp.renderer.shadowMap.autoUpdate = false;
  vp.renderer.shadowMap.needsUpdate = true;
  vp.sun = sun;
  vp.scene.add(sun);
  vp.scene.add(sun.target);

  vp.skyUniforms = {
    topColor: { value: new THREE.Color(0x2f5f92) },
    bottomColor: { value: new THREE.Color(0xcfe0e6) },
    sunDir: { value: new THREE.Vector3(0, 1, 0) },
    sunColor: { value: new THREE.Color(0xfff2d0) },
    sunGlow: { value: 1 },
    nightMix: { value: 0 },
    offset: { value: 0.12 },
    exponent: { value: 0.9 },
  };
  const skyMat = new THREE.ShaderMaterial({
    uniforms: vp.skyUniforms,
    side: THREE.BackSide,
    depthWrite: false,
    depthTest: false,
    fog: false,
    toneMapped: false,
    vertexShader: `
      varying vec3 vDir;
      void main() {
        vDir = normalize(position);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: `
      varying vec3 vDir;
      uniform vec3 topColor, bottomColor, sunColor, sunDir;
      uniform float sunGlow, nightMix, offset, exponent;
      float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7)))*43758.5453); }
      void main() {
        float h = clamp(vDir.y, -1.0, 1.0);
        float t = pow(max(h + offset, 0.0), exponent);
        vec3 col = mix(bottomColor, topColor, t);
        float d = dot(normalize(vDir), normalize(sunDir));
        float disc = smoothstep(0.9992, 0.9997, d);
        float halo = pow(max(d, 0.0), 220.0) * 0.6 + pow(max(d,0.0), 24.0) * 0.18;
        col += sunColor * (disc * 3.0 + halo * sunGlow);
        if (nightMix > 0.01 && h > 0.0) {
          vec2 g = floor((vDir.xz / max(abs(vDir.y),0.15)) * 220.0);
          float s = step(0.9975, hash(g));
          col += vec3(s) * nightMix * smoothstep(0.0,0.4,h);
        }
        col = mix(col, bottomColor, pow(1.0 - abs(h), 8.0) * 0.35);
        gl_FragColor = vec4(col, 1.0);
      }`,
  });
  vp.sky = new THREE.Mesh(new THREE.SphereGeometry(46000, 32, 24), skyMat);
  vp.sky.renderOrder = -10;
  vp.scene.add(vp.sky);

  vp._pmrem = new THREE.PMREMGenerator(vp.renderer);
  vp._pmrem.compileEquirectangularShader();
  vp._envTimer = 0;
}

export const environmentMethods = {
  applyEnvironment() {
    const h = ((state.timeOfDay % 24) + 24) % 24;
    // sun elevation: peaks ~13h, horizon at 6/18, night otherwise
    const dayT = (h - 6) / 12; // 0 at 6h, 1 at 18h
    const elev = Math.sin(dayT * Math.PI); // >0 during day
    const azim = Math.PI * (0.15 + 0.7 * dayT); // east→west sweep
    const el = Math.max(-0.35, elev) * 1.15;
    const dir = new THREE.Vector3(
      Math.cos(azim) * Math.cos(el),
      Math.sin(el),
      Math.sin(azim) * Math.cos(el),
    ).normalize();

    const w = state.weather;
    const overcast = w === "overcast" ? 1 : w === "rain" ? 0.85 : w === "snow" ? 0.8 : w === "fog" ? 0.6 : 0;
    const isNight = elev <= 0.02;
    const nightMix = THREE.MathUtils.clamp((0.06 - elev) / 0.18, 0, 1);
    const golden = THREE.MathUtils.clamp(1 - Math.abs(elev) / 0.35, 0, 1); // near horizon warmth

    // --- sky colors ---
    const topDay = new THREE.Color(0x2f6fb0);
    const botDay = new THREE.Color(0xbcd6e2);
    const topNight = new THREE.Color(0x0a1226);
    const botNight = new THREE.Color(0x1a2740);
    const grey = new THREE.Color(0x8b939b);
    let top = topDay.clone().lerp(botDay, golden * 0.2).lerp(topNight, nightMix);
    let bot = botDay.clone().lerp(new THREE.Color(0xffb066), golden * 0.55).lerp(botNight, nightMix);
    if (overcast) { top.lerp(grey, overcast * 0.8); bot.lerp(grey, overcast * 0.85); }
    this.skyUniforms.topColor.value.copy(top);
    this.skyUniforms.bottomColor.value.copy(bot);
    this.skyUniforms.sunDir.value.copy(dir);
    this.skyUniforms.nightMix.value = nightMix;
    this.skyUniforms.sunGlow.value = (1 - overcast) * (isNight ? 0.15 : 1);
    this.skyUniforms.sunColor.value.setHex(isNight ? 0x9fb4d8 : 0xfff2d0).lerp(new THREE.Color(0xff9a4a), golden * (1 - overcast));

    // --- sun light ---
    const alt = Math.max(0, elev);
    this.sun.position.copy(dir).multiplyScalar(900).add(this.controls.target);
    this.sun.color.setHex(0xffffff).lerp(new THREE.Color(0xffcf9a), golden).lerp(grey, overcast * 0.5);
    this.sun.intensity = isNight ? 0.12 : (1.5 * alt + 0.15) * (1 - overcast * 0.7);
    this.sun.castShadow = !isNight && overcast < 0.5;

    // --- ambient / hemisphere ---
    this.hemi.color.copy(top);
    this.hemi.groundColor.setHex(isNight ? 0x141a22 : 0x8f7f63);
    this.hemi.intensity = isNight ? 0.32 : 0.78 * (1 - overcast * 0.3) + 0.2;
    this.amb.intensity = isNight ? 0.24 : 0.26;
    this.amb.color.setHex(isNight ? 0x2a3a55 : 0x404040);

    // --- fog ---
    const fogBase = w === "fog" ? 0.0016 : w === "rain" ? 0.0006 : w === "snow" ? 0.0007 : 0.00012;
    this._fogBase = fogBase;
    this.scene.fog.color.copy(bot).lerp(top, 0.3);
    this.renderer.setClearColor(this.scene.fog.color, 1);
    this.scene.background = null; // dome covers it

    // --- exposure (brighter day, dimmer night) ---
    this.renderer.toneMappingExposure = isNight ? 1.25 : 1.05;

    this._applyWeather(w);
    this._lastShadowPos = null; // force shadow refresh on env change
    this.renderer.shadowMap.needsUpdate = true;
    this._envDirty = true;
  },
  _applyWeather(w) {
    const rain = w === "rain", snow = w === "snow";
    const want = rain || snow;
    if (!want) {
      if (this.precip) { this.scene.remove(this.precip); this.precip.geometry.dispose(); this.precip.material.dispose(); this.precip = null; }
      return;
    }
    if (!this.precip || this.precip.userData.kind !== w) {
      if (this.precip) { this.scene.remove(this.precip); this.precip.geometry.dispose(); }
      const N = rain ? 6000 : 3500;
      const pos = new Float32Array(N * 3);
      for (let i = 0; i < N; i++) {
        pos[i * 3] = (Math.random() - 0.5) * 260;
        pos[i * 3 + 1] = Math.random() * 160;
        pos[i * 3 + 2] = (Math.random() - 0.5) * 260;
      }
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
      const m = new THREE.PointsMaterial({
        color: rain ? 0x9fc4de : 0xffffff,
        size: rain ? 0.7 : 1.1,
        transparent: true,
        opacity: rain ? 0.55 : 0.9,
        depthWrite: false,
      });
      this.precip = new THREE.Points(g, m);
      this.precip.userData = { kind: w };
      this.precip.frustumCulled = false;
      this.scene.add(this.precip);
    }
  },
  updatePrecip(dt) {
    if (!this.precip) return;
    const p = this.camera.position;
    this.precip.position.set(p.x, p.y, p.z);
    const arr = this.precip.geometry.attributes.position.array;
    const rain = this.precip.userData.kind === "rain";
    const fall = rain ? 90 : 12;
    for (let i = 1; i < arr.length; i += 3) {
      arr[i] -= fall * dt;
      if (arr[i] < -40) arr[i] = 160;
    }
    this.precip.geometry.attributes.position.needsUpdate = true;
  },
  updateEnvMap() {
    // rebuild the reflection probe from the current sky gradient (debounced)
    try {
      const c = document.createElement("canvas");
      c.width = 128; c.height = 64;
      const ctx = c.getContext("2d");
      const grd = ctx.createLinearGradient(0, 0, 0, 64);
      grd.addColorStop(0, "#" + this.skyUniforms.topColor.value.getHexString());
      grd.addColorStop(1, "#" + this.skyUniforms.bottomColor.value.getHexString());
      ctx.fillStyle = grd; ctx.fillRect(0, 0, 128, 64);
      const tex = new THREE.CanvasTexture(c);
      tex.mapping = THREE.EquirectangularReflectionMapping;
      const rt = this._pmrem.fromEquirectangular(tex);
      if (this._envRT) this._envRT.dispose();
      this._envRT = rt;
      this.scene.environment = rt.texture;
      tex.dispose();
    } catch (e) { /* ignore */ }
    this._envDirty = false;
  },
};
