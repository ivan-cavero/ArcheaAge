<template>
  <div class="sr" @click="$emit('select', server.id)">
    <div class="snc">
      <span v-if="starred" class="ss-star">&#9733;</span>
      <div>
        <div class="sn">{{ server.name }}</div>
        <div class="st2">{{ server.id }}</div>
      </div>
    </div>
    <div class="bd" :class="badgeClass">
      <span class="d"></span>{{ statusLabel }}
    </div>
    <div class="pc">
      <div class="pn"><b>{{ server.players }}</b> / {{ server.maxPlayers }}</div>
      <div class="pb"><i :style="{ width: fillPct + '%' }"></i></div>
    </div>
    <div class="pg">&mdash;</div>
  </div>
</template>

<script>
export default {
  name: "ServerRow",
  props: {
    server: { type: Object, required: true },
    starred: { type: Boolean, default: false },
    selected: { type: Boolean, default: false },
  },
  emits: ["select"],
  computed: {
    isOnline() {
      return this.server.status === "online";
    },
    badgeClass() {
      if (this.isOnline) return "bd-on";
      if (this.server.status === "maintenance") return "bd-mt";
      return "bd-off";
    },
    statusLabel() {
      const s = this.server.status || "offline";
      return s.charAt(0).toUpperCase() + s.slice(1);
    },
    fillPct() {
      const max = this.server.maxPlayers || 1;
      return Math.min(100, Math.round((this.server.players / max) * 100));
    },
  },
};
</script>

<style scoped>
.sr {
  display: grid;
  grid-template-columns: 1fr 85px 115px 75px;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(150, 180, 100, 0.04);
  transition: background 0.1s;
  cursor: pointer;
}
.sr:last-child {
  border-bottom: 0;
}
.sr:hover,
.sr.sel {
  background: rgba(141, 187, 62, 0.03);
}
.snc {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}
.ss-star {
  color: var(--gold);
  font-size: 13px;
}
.sn {
  font-family: var(--ff-d);
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}
.st2 {
  font-size: 9.5px;
  color: var(--text-2);
  margin-top: 1px;
}
.pc {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.pn {
  font-size: 10.5px;
  color: var(--text-2);
  font-variant-numeric: tabular-nums;
}
.pn b {
  color: var(--text);
  font-weight: 600;
}
.pg {
  font-size: 10.5px;
  color: var(--text-2);
}
</style>
