// Registry HTTP client. The launcher talks to the metaserver directly over
// HTTPS (CORS on the registry allows the Tauri origins). The URL can be
// overridden with ARCHEAAGE_REGISTRY for development.

const REGISTRY_URL =
  window.__ARCHEAAGE_REGISTRY__ || "http://localhost:5080";

async function get(path, timeoutMs = 4000) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(REGISTRY_URL + path, { signal: ctrl.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

/** GET /versions → [{id,name,client,servers,playersOnline,status,downloadSize}] */
export function fetchVersions() {
  return get("/versions").then((d) => d.versions || []);
}

/** GET /versions/{v}/servers → [{id,name,status,players,maxPlayers,lastHeartbeat}] */
export async function fetchServers(version) {
  try {
    const d = await get(`/versions/${encodeURIComponent(version)}/servers`);
    return d.servers || [];
  } catch (e) {
    if (e.name === "AbortError") throw e;
    return []; // 404 = no servers for this version
  }
}

/** GET /news → {items:[{id,date,tag,title,body}]} */
export async function fetchNews() {
  try {
    return await get("/news");
  } catch {
    return { items: [] };
  }
}

export { REGISTRY_URL };
