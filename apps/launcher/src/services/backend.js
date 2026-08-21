// Tauri backend bridge. Every call degrades gracefully when the UI runs in a
// plain browser (`npm run dev` without Tauri): commands resolve to demo data
// and event listeners become no-ops, so the whole UI stays explorable.

const IN_TAURI = typeof window !== "undefined" && !!window.__TAURI_INTERNALS__;

async function invoke(cmd, args = {}) {
  if (!IN_TAURI) return demoFor(cmd, args);
  const { invoke } = await import("@tauri-apps/api/core");
  return invoke(cmd, args);
}

/** Listen to `client-progress` events: {stage,file,downloaded,total}. */
export async function onClientProgress(handler) {
  if (!IN_TAURI) return () => {};
  const { listen } = await import("@tauri-apps/api/event");
  const un = await listen("client-progress", (e) => handler(e.payload));
  return un; // call to unsubscribe
}

/** {installed, verified, files, install_dir} */
export function clientStatus(version) {
  return invoke("client_status", { version });
}

/** Download/verify/extract until ready. Emits client-progress while running. */
export function clientEnsure(version) {
  return invoke("client_ensure", { version });
}

export function clientLaunch(version, serverId) {
  return invoke("client_launch", { version, serverId });
}

export function openInstallDir(version) {
  return invoke("open_install_dir", { version });
}

// --- Browser-demo fallbacks -------------------------------------------------

function demoFor(cmd, args) {
  switch (cmd) {
    case "client_status":
      return {
        installed: false,
        verified: false,
        files: 0,
        install_dir: "",
      };
    case "client_ensure":
      return {
        installed: true,
        verified: true,
        files: 1284,
        install_dir: "C:\\demo",
      };
    case "client_launch":
      return "launched";
    default:
      return null;
  }
}

export { IN_TAURI };
