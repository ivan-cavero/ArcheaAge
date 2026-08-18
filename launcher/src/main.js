// Registry base URL. En dev apunta al registry local; en producción lo
// inyecta el backend Tauri (comando registry_get).
const REGISTRY = "http://localhost:5080";

let currentVersion = null;
let serversTimer = null;

const $ = (sel) => document.querySelector(sel);

function setStatus(text) {
  $("#status").textContent = text;
}

function setProgress(pct, label) {
  const bar = $("#progress-bar");
  const text = $("#progress-text");
  bar.style.width = `${Math.max(0, Math.min(100, pct))}%`;
  text.textContent = label;
}

async function fetchJson(path) {
  const res = await fetch(`${REGISTRY}${path}`);
  if (!res.ok) throw new Error(`HTTP ${res.status} ${path}`);
  return res.json();
}

// --- Render seguro (sin innerHTML: los datos vienen del registry) ---

function renderVersions(versions) {
  const el = $("#versions");
  el.replaceChildren();
  for (const v of versions) {
    const card = document.createElement("div");
    card.className = "version-card";
    card.dataset.id = v.id;

    const title = document.createElement("h2");
    title.textContent = v.name;
    const meta = document.createElement("p");
    meta.textContent = `${v.client} · ${v.servers} servers · ${v.playersOnline} online · ${v.status}`;

    card.append(title, meta);
    card.onclick = () => selectVersion(v.id);
    el.appendChild(card);
  }
  highlightCurrent();
}

function highlightCurrent() {
  document.querySelectorAll(".version-card").forEach((card) => {
    card.classList.toggle("active", card.dataset.id === currentVersion);
  });
}

async function selectVersion(id) {
  currentVersion = id;
  highlightCurrent();
  await refreshServers();
  clearInterval(serversTimer);
  serversTimer = setInterval(refreshServers, 10000);
}

async function refreshServers() {
  if (!currentVersion) return;
  try {
    const { servers } = await fetchJson(`/versions/${currentVersion}/servers`);
    const tbody = $("#servers");
    tbody.replaceChildren();

    if (servers.length) {
      for (const s of servers) {
        const row = tbody.insertRow();
        row.insertCell().textContent = s.name;
        const status = row.insertCell();
        status.textContent = s.status;
        status.className = s.status === "online" ? "online" : "";
        row.insertCell().textContent = `${s.players}/${s.maxPlayers}`;
        const playCell = row.insertCell();
        const btn = document.createElement("button");
        btn.textContent = "Jugar";
        btn.onclick = () => play(currentVersion, s.id);
        playCell.appendChild(btn);
      }
    } else {
      const row = tbody.insertRow();
      const cell = row.insertCell();
      cell.colSpan = 4;
      cell.textContent = "Sin servers online para esta versión.";
    }
    setStatus(`Última actualización: ${new Date().toLocaleTimeString()}`);
  } catch (err) {
    setStatus(`Error: ${err.message}`);
  }
}

// --- Flujo de juego: ensure (descarga/verifica) → launch ---

async function play(version, serverId) {
  if (!window.__TAURI__) {
    setStatus("Flujo completo solo dentro de la app Tauri (dev = navegador).");
    return;
  }
  const { invoke } = await import("@tauri-apps/api/core");
  const { listen } = await import("@tauri-apps/api/event");

  // progreso de descarga en vivo
  await listen("client-progress", (ev) => {
    const { file, downloaded, total } = ev.payload;
    const pct = total ? (downloaded / total) * 100 : 0;
    setProgress(pct, `Descargando ${file}… ${(downloaded / 1048576).toFixed(0)}/${(total / 1048576).toFixed(0)} MB`);
  });

  setStatus(`Preparando client ${version}…`);
  setProgress(0, "Comprobando instalación…");
  let status;
  try {
    status = await invoke("client_ensure", { version });
  } catch (err) {
    setStatus(`Descarga fallida: ${err}`);
    setProgress(0, "");
    return;
  }
  setProgress(100, status.verified ? "Client verificado ✓" : "Client instalado (parcial)");

  try {
    const result = await invoke("client_launch", { version, serverId });
    setStatus(result);
  } catch (err) {
    setStatus(`Error al lanzar: ${err}`);
  }
}

(async function init() {
  try {
    const { versions } = await fetchJson("/versions");
    renderVersions(versions);
    if (versions.length) selectVersion(versions[0].id);
  } catch (err) {
    setStatus(`No se pudo conectar al registry (${REGISTRY}): ${err.message}`);
  }
})();