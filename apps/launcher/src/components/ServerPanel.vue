<template>
  <div class="cd sp">
    <div class="sh">
      <span class="st">Servers <span>({{ servers.length }})</span></span>
      <div class="sa">
        <div class="ss">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            type="text"
            placeholder="Search servers..."
            :value="query"
            @input="$emit('update:query', $event.target.value)"
          />
        </div>
        <button class="sf" title="Refresh" @click="$emit('refresh')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
          </svg>
        </button>
      </div>
    </div>

    <div class="stb">
      <div class="srh">
        <span>Server Name</span><span>Status</span><span>Players</span><span>Ping</span>
      </div>

      <ServerRow
        v-for="s in visibleServers"
        :key="s.id"
        :server="s"
        :selected="s.id === selectedId"
        starred
        @select="$emit('select-server', $event)"
      />

      <div v-if="!visibleServers.length" class="empty">
        {{ servers.length ? "No servers match your search." : loading ? "Loading servers…" : "No servers online right now." }}
      </div>
    </div>

    <button v-if="servers.length > limit" class="sm" @click="$emit('toggle-all')">
      {{ showAll ? "Show less" : `Show full list (${servers.length})` }}
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <polyline points="6 9 12 15 18 9"/>
      </svg>
    </button>
  </div>
</template>

<script>
import ServerRow from "./ServerRow.vue";

export default {
  name: "ServerPanel",
  components: { ServerRow },
  props: {
    servers: { type: Array, required: true },
    loading: { type: Boolean, default: false },
    query: { type: String, default: "" },
    selectedId: { type: String, default: null },
    showAll: { type: Boolean, default: false },
  },
  emits: ["update:query", "refresh", "select-server", "toggle-all"],
  data() {
    return { limit: 5 };
  },
  computed: {
    visibleServers() {
      const q = this.query.trim().toLowerCase();
      const filtered = q
        ? this.servers.filter(
            (s) =>
              s.name.toLowerCase().includes(q) ||
              (s.id || "").toLowerCase().includes(q)
          )
        : this.servers;
      return this.showAll ? filtered : filtered.slice(0, this.limit);
    },
  },
};
</script>

<style scoped>
.sp {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}
.sh {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--brd);
}
.st {
  font-family: var(--ff-d);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-gd);
}
.st span {
  color: var(--text-m);
  font-family: var(--ff-u);
  font-weight: 400;
}
.sa {
  display: flex;
  gap: 5px;
}
.ss {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 9px;
  border-radius: 4px;
  background: var(--input);
  border: 1px solid var(--brd);
  width: 150px;
}
.ss svg {
  width: 11px;
  height: 11px;
  color: var(--text-m);
  flex-shrink: 0;
}
.ss input {
  flex: 1;
  border: 0;
  background: 0;
  font-size: 10px;
  color: var(--text);
  outline: 0;
  font-family: var(--ff-u);
}
.ss input::placeholder {
  color: var(--text-m);
}
.sf {
  width: 26px;
  height: 26px;
  border-radius: 4px;
  border: 1px solid var(--brd);
  background: var(--input);
  color: var(--text-2);
  cursor: pointer;
  display: grid;
  place-items: center;
}
.sf:hover {
  color: var(--primary);
  border-color: var(--brd-s);
}
.sf svg {
  width: 11px;
  height: 11px;
}
.stb {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  min-height: 0;
}
.srh {
  display: grid;
  grid-template-columns: 1fr 85px 115px 75px;
  gap: 12px;
  padding: 8px 16px;
  font-size: 7.5px;
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--text-m);
  border-bottom: 1px solid var(--brd);
}
.empty {
  padding: 22px 16px;
  text-align: center;
  font-size: 10.5px;
  color: var(--text-m);
}
.sm {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 4px;
  padding: 9px;
  font-size: 8px;
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--text-2);
  cursor: pointer;
  border: 0;
  border-top: 1px solid var(--brd);
  background: transparent;
  font-family: var(--ff-u);
  transition: color 0.12s;
}
.sm:hover {
  color: var(--primary);
}
.sm svg {
  width: 8px;
  height: 8px;
}
</style>
