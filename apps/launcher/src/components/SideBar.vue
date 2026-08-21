<template>
  <aside class="sb">
    <div class="sb-logo">
      <img src="/images/logo.png" alt="ArcheaAge" />
      <span class="sb-tag">Reborn. Custom. Community.</span>
      <span class="sb-sep"></span>
      <span class="sb-ver">Launcher v0.1.0</span>
    </div>

    <nav class="sb-nav">
      <button
        v-for="item in items"
        :key="item.id"
        class="ni"
        :class="{ on: activeTab === item.id }"
        @click="$emit('navigate', item.id)"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" v-html="item.icon"></svg>
        {{ item.label }}
      </button>
    </nav>

    <div class="sb-bot">
      <div class="sb-links">
        <a href="#" title="Discord">
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M20.317 4.37a19.791 19.791 0 00-4.885-1.515.074.074 0 00-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 00-5.487 0 12.64 12.64 0 00-.617-1.25.077.077 0 00-.079-.037A19.736 19.736 0 003.677 4.37a.07.07 0 00-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 00.031.057 19.9 19.9 0 005.993 3.03.078.078 0 00.084-.028c.38-.7.73-1.44 1.05-2.22a.076.076 0 00-.041-.106 13.107 13.107 0 01-1.872-.892.077.077 0 01-.008-.128 10.2 10.2 0 00.372-.292.074.074 0 01.077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 01.078.01c.12.098.246.198.373.292a.077.077 0 01-.006.127 12.299 12.299 0 01-1.873.892.077.077 0 00-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 00.084.028 19.839 19.839 0 006.002-3.03.077.077 0 00.032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 00-.031-.03z"/></svg>
        </a>
        <a href="#" title="GitHub">
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/></svg>
        </a>
        <a href="#" title="Website">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/></svg>
        </a>
      </div>
      <div class="sb-stat">
        <span class="dot" :class="{ err: !registryOk }"></span>
        <span>{{ registryOk ? "All systems operational" : "Registry unreachable" }}</span>
      </div>
    </div>
  </aside>
</template>

<script>
const I = {
  home: '<path d="M3 9.5L12 3l9 6.5V20a1 1 0 01-1 1H4a1 1 0 01-1-1V9.5z"/><path d="M9 21V12h6v9"/>',
  versions: '<circle cx="12" cy="12" r="3"/><path d="M12 2v4m0 12v4M2 12h4m12 0h4"/>',
  servers: '<rect x="3" y="3" width="18" height="5" rx="1"/><rect x="3" y="16" width="18" height="5" rx="1"/><circle cx="7" cy="5.5" r="1"/><circle cx="7" cy="18.5" r="1"/>',
  downloads: '<path d="M12 4v10m0 0l-3.5-3.5M12 14l3.5-3.5"/><path d="M4 17v1a2 2 0 002 2h12a2 2 0 002-2v-1"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>',
  mods: '<path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/>',
  plugins: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  news: '<path d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1"/><path d="M19 20a2 2 0 002-2V8a2 2 0 00-2-2h-1"/><line x1="7" y1="8" x2="13" y2="8"/><line x1="7" y1="12" x2="13" y2="12"/>',
};

export default {
  name: "SideBar",
  props: {
    activeTab: { type: String, required: true },
    registryOk: { type: Boolean, default: true },
  },
  emits: ["navigate"],
  data() {
    return {
      items: [
        { id: "home", label: "Home", icon: I.home },
        { id: "versions", label: "Versions", icon: I.versions },
        { id: "servers", label: "Servers", icon: I.servers },
        { id: "downloads", label: "Downloads", icon: I.downloads },
        { id: "settings", label: "Settings", icon: I.settings },
        { id: "mods", label: "Mods & Content", icon: I.mods },
        { id: "plugins", label: "Plugins", icon: I.plugins },
        { id: "news", label: "News", icon: I.news },
      ],
    };
  },
};
</script>

<style scoped>
.sb {
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #091310, #070e0b 50%, #050a08);
  border-right: 1px solid var(--brd);
  position: relative;
  z-index: 10;
}
.sb-logo {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 28px 16px 16px;
}
.sb-logo img {
  width: 120px;
  height: auto;
  filter: brightness(0.9);
  margin-bottom: 6px;
}
.sb-tag {
  font-size: 6px;
  font-weight: 500;
  letter-spacing: 2.5px;
  text-transform: uppercase;
  color: var(--text-m);
  margin-top: 2px;
}
.sb-ver {
  font-size: 7px;
  color: var(--text-m);
  margin-top: 4px;
  opacity: 0.5;
}
.sb-sep {
  width: 50px;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--gold-d), transparent);
  margin: 8px auto 0;
  opacity: 0.35;
}
.sb-nav {
  flex: 1;
  padding: 12px 0;
  overflow-y: auto;
}
.ni {
  display: flex;
  align-items: center;
  gap: 11px;
  width: 100%;
  border: 0;
  background: transparent;
  color: var(--text-2);
  cursor: pointer;
  font-family: var(--ff-u);
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.3px;
  padding: 11px 22px;
  text-align: left;
  transition: all 0.15s;
  border-left: 2.5px solid transparent;
}
.ni:hover {
  background: rgba(141, 187, 62, 0.04);
  color: var(--text);
}
.ni.on {
  color: var(--primary);
  background: rgba(141, 187, 62, 0.06);
  border-left-color: var(--primary);
}
.ni svg {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  opacity: 0.4;
  transition: opacity 0.15s;
}
.ni.on svg {
  opacity: 0.85;
}
.sb-bot {
  padding: 12px 22px 16px;
  border-top: 1px solid var(--brd);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sb-links {
  display: flex;
  gap: 14px;
}
.sb-links a {
  color: var(--text-m);
  text-decoration: none;
  transition: color 0.12s;
}
.sb-links a:hover {
  color: var(--primary);
}
.sb-links svg {
  width: 15px;
  height: 15px;
}
.sb-stat {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 9px;
  color: var(--text-m);
}
.dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--on);
  box-shadow: 0 0 5px var(--on);
}
.dot.err {
  background: var(--off);
  box-shadow: 0 0 5px var(--off);
}
</style>
