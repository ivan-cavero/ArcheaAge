<template>
  <div class="es cd">
    <div class="es-ic">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
        <rect x="3" y="3" width="18" height="18" rx="2"/>
        <path d="M12 8v8M8 12h8"/>
      </svg>
    </div>
    <div class="es-t">{{ title }}</div>
    <div class="es-d">This section is on the roadmap — check docs/ARQUITECTURA.md for milestones.</div>
  </div>
</template>

<script>
export default {
  name: "EmptyState",
  props: { title: { type: String, required: true } },
};
</script>

<style scoped>
.es {
  align-self: center;
  justify-self: center;
  max-width: 380px;
  padding: 34px 30px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.es-ic {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  background: var(--surface-el);
  border: 1px solid var(--brd);
  display: grid;
  place-items: center;
  color: var(--gold);
  margin-bottom: 4px;
}
.es-ic svg {
  width: 20px;
  height: 20px;
}
.es-t {
  font-family: var(--ff-d);
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--text);
}
.es-d {
  font-size: 10.5px;
  line-height: 1.6;
  color: var(--text-m);
}
</style>
