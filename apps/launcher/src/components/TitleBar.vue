<template>
  <div class="tb" data-tauri-drag-region>
    <span
      class="tb-user"
      :class="{ anon: !user }"
      :title="user ? 'Click to log out' : 'Not logged in'"
      @click="user && $emit('logout')"
    >
      <span class="tb-dot" :class="{ on: !!user }"></span>
      {{ user ? user + " · log out" : "Not logged in" }}
    </span>
    <div class="tb-b">
      <button title="Minimize" @click.stop="win?.minimize()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M5 12h14"/></svg>
      </button>
      <button title="Maximize" @click.stop="win?.toggleMaximize()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="5" y="5" width="14" height="14" rx="1"/></svg>
      </button>
      <button class="x" title="Close" @click.stop="win?.close()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
      </button>
    </div>
  </div>
</template>

<script>
import { getCurrentWindow } from "@tauri-apps/api/window";

export default {
  name: "TitleBar",
  props: { user: { type: String, default: "" } },
  emits: ["logout"],
  data() {
    return { win: null };
  },
  async mounted() {
    try {
      this.win = getCurrentWindow();
    } catch {
      // Plain browser: buttons are inert.
    }
  },
};
</script>

<style scoped>
.tb {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  height: 30px;
  flex-shrink: 0;
  background: rgba(7, 16, 13, 0.3);
  -webkit-app-region: drag;
}
.tb-user {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  color: var(--text-2);
  padding: 2px 8px;
  border-radius: 3px;
}
.tb-user.anon {
  color: var(--text-m);
}
.tb-user:not(.anon) {
  cursor: pointer;
}
.tb-user:not(.anon):hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text);
}
.tb-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--text-m);
}
.tb-dot.on {
  background: var(--on);
  box-shadow: 0 0 4px var(--on);
}
.tb-b {
  display: flex;
  -webkit-app-region: no-drag;
}
.tb-b button {
  width: 36px;
  height: 30px;
  border: 0;
  background: 0;
  color: var(--text-m);
  cursor: pointer;
  display: grid;
  place-items: center;
  transition:
    background 0.12s,
    color 0.12s;
  outline: 0;
}
.tb-b button:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-2);
}
.tb-b .x:hover {
  background: rgba(142, 78, 78, 0.5);
  color: var(--text);
}
.tb-b svg {
  width: 11px;
  height: 11px;
}
</style>
