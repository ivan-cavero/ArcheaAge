// Registry base URL. En dev apunta al registry local; en producción lo
// inyecta el backend Tauri (comando registry_get).
const REGISTRY = "http://localhost:5080";

let currentVersion = null;
let serversTimer = null;

const $ = (sel) => document.querySelector(sel);

function setStatus(text, isError = false) {
  const el = $("#status");
  el.textContent = text;
  el.classList.toggle("error", isError);
}

function setConn(online) {
  $("#conn").classList.toggle("online", online);
  $("#conn").classList.toggle("offline", !online);
  $("#conn-text").textContent = online
    ? "registry conectado"
    : "registry sin conexión";
}

function setProgress(pct, label) {
  const bar = $("#progress-bar");
  const pctEl = $("#progress-pct");
  bar.style.width = `${Math.max(0, Math.min(100, pct))}%`;
  pctEl.textContent = `${Math.round(pct)}%`;
  $("#progress-label").textContent = label;
  $("#progress").classList.remove("hidden");
}

function hideProgress() {
  $("#progress").classList.add("hidden");
}

function fmtMB(bytes) {
  return `${(bytes / 1048576).toFixed(0)} MB`;
}

async function fetchJson(path) {
  const res = await fetch(`${REGISTRY}${path}`);
  if (!res.ok) throw new Error(`HTTP ${res.status} ${path}`);
  return res.json();
}

function pillClass(status) {
  return ["live", "beta", "maintenance", "planned"].includes(status)
    ? status
    : "planned";
}

// --- Render seguro (sin innerHTML: los datos vienen del registry) ---

function renderVersions(versions) {
  const el = $("#versions");
  el.replaceChildren();
  for (const v of versions) {
    const card = document.createElement("div");
    card.className = "version-card";
    card.dataset.id = v.id;

    const top = document.createElement("div");
    top.className = "top";
    const title = document.createElement("h3");
    title.textContent = v.name;
    const pill = document.createElement("span");
    pill.className = `pill ${pillClass(v.status)}`;
    pill.textContent = v.status;
    top.append(title, pill);

    const client = document.createElement("p");
    client.className = "client";
    client.textContent = v.client;

    const stats = document.createElement("div");
    stats.className = "stats";
    const servers = document.createElement("span");
    servers.append(
      document.createTextNode("servers "),
      Object.assign(document.createElement("b"), { textContent: v.servers }),
    );
    const players = document.createElement("span");
    players.append(
      document.createTextNode("online "),
      Object.assign(document.createElement("b"), {
        textContent: v.playersOnline,
      }),
    );
    stats.append(servers, players);

    card.append(top, client, stats);
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

function serverRow(s) {
  const row = document.createElement("div");
  row.className = "server-row";

  const name = document.createElement("div");
  name.className = "server-name";
  const dot = document.createElement("span");
  dot.className = `sdot ${s.status}`;
  const label = document.createElement("span");
  label.textContent = s.name;
  name.append(dot, label);

  const status = document.createElement("div");
  status.className = "server-status";
  status.textContent = s.status;

  const players = document.createElement("div");
  players.className = "players";
  const num = document.createElement("span");
  num.className = "num";
  num.append(
    Object.assign(document.createElement("b"), { textContent: s.players }),
    document.createTextNode(` / ${s.maxPlayers}`),
  );
  const bar = document.createElement("div");
  bar.className = "pbar";
  const fill = document.createElement("i");
  const pct = s.maxPlayers ? Math.round((s.players / s.maxPlayers) * 100) : 0;
  fill.style.width = `${Math.min(100, pct)}%`;
  bar.appendChild(fill);
  players.append(num, bar);

  const btn = document.createElement("button");
  btn.className = "btn";
  btn.textContent = "Jugar";
  btn.disabled = s.status !== "online";
  btn.onclick = () => play(s.version, s.id);

  row.append(name, status, players, btn);
  return row;
}

async function refreshServers() {
  if (!currentVersion) return;
  try {
    const { servers } = await fetchJson(`/versions/${currentVersion}/servers`);
    const el = $("#servers");
    el.replaceChildren();
    if (servers.length) {
      for (const s of servers) el.appendChild(serverRow(s));
    } else {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = "Sin servers online para esta versión.";
      el.appendChild(empty);
    }
    setStatus(`Última actualización: ${new Date().toLocaleTimeString()}`);
  } catch (err) {
    setStatus(`Error: ${err.message}`, true);
  }
}

// --- Flujo de juego: ensure (descarga/verifica) → launch ---

async function play(version, serverId) {
  if (!window.__TAURI__) {
    setStatus(
      "Flujo completo solo dentro de la app Tauri (dev = navegador).",
      true,
    );
    return;
  }
  const { invoke } = await import("@tauri-apps/api/core");
  const { listen } = await import("@tauri-apps/api/event");

  // progreso de descarga en vivo
  await listen("client-progress", (ev) => {
    const { file, downloaded, total } = ev.payload;
    const pct = total ? (downloaded / total) * 100 : 0;
    setProgress(
      pct,
      `Descargando ${file}… ${fmtMB(downloaded)} / ${fmtMB(total)}`,
    );
  });

  setProgress(0, "Comprobando instalación…");
  let status;
  try {
    status = await invoke("client_ensure", { version });
  } catch (err) {
    setStatus(`Descarga fallida: ${err}`, true);
    hideProgress();
    return;
  }
  if (status.verified) {
    setProgress(100, "Client verificado ✓ — lanzando…");
  } else {
    setStatus("Client instalado incompleto (verifica el manifiesto).", true);
    hideProgress();
    return;
  }

  try {
    const result = await invoke("client_launch", { version, serverId });
    setStatus(result);
  } catch (err) {
    setStatus(`Error al lanzar: ${err}`, true);
  }
}

(async function init() {
  const clock = $("#clock");
  clock.textContent = new Date().toLocaleTimeString();
  setInterval(
    () => (clock.textContent = new Date().toLocaleTimeString()),
    1000,
  );

  try {
    const { versions } = await fetchJson("/versions");
    setConn(true);
    renderVersions(versions);
    if (versions.length) selectVersion(versions[0].id);
  } catch (err) {
    setConn(false);
    setStatus(
      `No se pudo conectar al registry (${REGISTRY}): ${err.message}`,
      true,
    );
  }
})();
