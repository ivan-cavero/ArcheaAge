<template>
  <div>
    <div class="sec-lb">Select Version</div>
    <div class="ver-chips">
      <button
        v-for="v in versions"
        :key="v.id"
        class="vc"
        :class="{ on: v.id === selectedId, dis: !isPlayable(v) }"
        :title="isPlayable(v) ? v.name : `${v.name} — coming soon`"
        @click="isPlayable(v) && $emit('select', v.id)"
      >
        <span class="vc-ic">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
        </span>
        <span class="vc-nm">{{ v.id }}</span>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: "VersionChips",
  props: {
    versions: { type: Array, required: true },
    selectedId: { type: String, default: null },
  },
  emits: ["select"],
  methods: {
    isPlayable(v) {
      return v.status === "live" || v.status === "beta";
    },
  },
};
</script>

<style scoped>
.ver-chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.vc {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 10px 16px;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.12s;
  position: relative;
  overflow: hidden;
  border: 1px solid var(--brd);
  background: rgba(16, 26, 23, 0.5);
}
.vc::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(141, 187, 62, 0.03), transparent 50%);
  opacity: 0;
  transition: opacity 0.12s;
}
.vc:hover {
  border-color: var(--brd-s);
}
.vc:hover::before {
  opacity: 1;
}
.vc.on {
  border-color: rgba(141, 187, 62, 0.3);
  background: rgba(141, 187, 62, 0.06);
}
.vc.on::before {
  opacity: 1;
}
.vc.dis {
  opacity: 0.3;
  cursor: default;
  pointer-events: none;
}
.vc-ic {
  width: 26px;
  height: 26px;
  border-radius: 4px;
  background: var(--surface-el);
  border: 1px solid var(--brd);
  display: grid;
  place-items: center;
  color: var(--text-m);
  flex-shrink: 0;
}
.vc.on .vc-ic {
  background: var(--primary-d);
  border-color: var(--primary-2);
  color: var(--text);
}
.vc-ic svg {
  width: 13px;
  height: 13px;
}
.vc-nm {
  font-family: var(--ff-d);
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}
</style>
