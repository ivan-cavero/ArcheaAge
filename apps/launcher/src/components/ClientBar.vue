<template>
  <div class="bb">
    <div class="ci">
      <div class="cil">Client</div>
      <div class="cir">
        <span class="cin">{{ versionLabel }}</span>
        <span class="cis" :class="{ ok: ready }">{{ statusText }}</span>
        <span v-if="progress.active" class="cisz">{{ downloadedGb }} / {{ totalGb }} GB</span>
        <div class="cic">
          <button title="Choose install folder" @click="$emit('choose-dir')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/><path d="M12 10v6M9 13h6"/></svg>
          </button>
          <button title="Open install folder" @click="$emit('open-dir')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
          </button>
        </div>
      </div>
      <div class="pt">
        <div class="pf" :style="{ width: pct + '%' }"></div>
      </div>
      <div class="pinf">
        <span v-if="error" class="cerr" title="Dismiss" @click="$emit('dismiss-error')">⚠ {{ error }} ✕</span>
        <template v-else>
          <span>{{ pct }}%</span>
          <span v-if="progress.active">{{ stageText }}</span>
        </template>
      </div>
    </div>
    <div class="pa">
      <slot />
    </div>
  </div>
</template>

<script>
export default {
  name: "ClientBar",
  props: {
    versionLabel: { type: String, default: "—" },
    status: {
      type: Object,
      default: () => ({ installed: false, verified: false }),
    },
    progress: {
      type: Object,
      default: () => ({ active: false, stage: "", file: "", downloaded: 0, total: 0 }),
    },
    busy: { type: Boolean, default: false },
    error: { type: String, default: "" },
  },
  emits: ["open-dir", "choose-dir", "dismiss-error"],
  computed: {
    ready() {
      return this.status.installed && this.status.verified && !this.progress.active;
    },
    statusText() {
      if (this.progress.active) return `${this.progress.stage}…`;
      if (!this.status.installed) return "Not installed";
      if (!this.status.verified) return "Needs verification";
      return "Ready";
    },
    stageText() {
      const f = this.progress.file ? ` — ${this.progress.file}` : "";
      return `${this.progress.stage}${f}`;
    },
    pct() {
      if (this.progress.active && this.progress.total > 0) {
        return Math.min(100, Math.round((this.progress.downloaded / this.progress.total) * 100));
      }
      return this.ready ? 100 : 0;
    },
    downloadedGb() {
      return (this.progress.downloaded / 1024 ** 3).toFixed(2);
    },
    totalGb() {
      return (this.progress.total / 1024 ** 3).toFixed(2);
    },
  },
};
</script>

<style scoped>
.bb {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: stretch;
  border-top: 1px solid var(--brd);
  background: var(--bg);
  flex-shrink: 0;
}
.ci {
  padding: 12px 22px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  border-right: 1px solid var(--brd);
}
.cil {
  font-family: var(--ff-d);
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-gd);
}
.cir {
  display: flex;
  align-items: center;
  gap: 10px;
}
.cin {
  font-size: 11px;
  font-weight: 600;
  color: var(--text);
}
.cis {
  font-size: 10px;
  color: var(--text-2);
}
.cis.ok {
  color: var(--on);
}
.cisz {
  font-size: 10px;
  color: var(--text-2);
  margin-left: auto;
  font-variant-numeric: tabular-nums;
}
.cic {
  display: flex;
  gap: 3px;
  margin-left: 6px;
}
.cic button {
  width: 24px;
  height: 24px;
  border-radius: 3px;
  border: 1px solid var(--brd);
  background: var(--surface);
  color: var(--text-2);
  cursor: pointer;
  display: grid;
  place-items: center;
  transition: all 0.1s;
}
.cic button:hover {
  border-color: var(--text-m);
  color: var(--text);
}
.cic svg {
  width: 10px;
  height: 10px;
}
.pt {
  height: 3px;
  border-radius: 1.5px;
  background: rgba(150, 180, 100, 0.08);
  overflow: hidden;
}
.pf {
  height: 100%;
  border-radius: 1.5px;
  background: linear-gradient(
    90deg,
    var(--primary-d),
    var(--primary-2),
    var(--primary)
  );
  position: relative;
  transition: width 0.4s ease;
}
.pf::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.06),
    transparent
  );
  animation: sh 2.5s infinite;
}
@keyframes sh {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}
.pinf {
  display: flex;
  justify-content: space-between;
  font-size: 8.5px;
  color: var(--text-m);
  font-variant-numeric: tabular-nums;
}
.cerr {
  color: #e08a8a;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}
.pa {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px 28px;
  min-width: 180px;
}
</style>
