<template>
  <button class="bp" :class="{ busy }" :disabled="busy" @click="$emit('press')">
    <svg v-if="!busy" viewBox="0 0 24 24" fill="currentColor">
      <path d="M7 4.5L19 12 7 19.5z" />
    </svg>
    <span class="spin" v-else></span>
    {{ label }}
  </button>
</template>

<script>
export default {
  name: "PlayButton",
  props: {
    label: { type: String, default: "Play" },
    busy: { type: Boolean, default: false },
  },
  emits: ["press"],
};
</script>

<style scoped>
.pa {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px 28px;
  min-width: 180px;
}
.bp {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 11px;
  width: 100%;
  padding: 16px 32px;
  border: 1px solid rgba(141, 187, 62, 0.2);
  border-radius: 5px;
  cursor: pointer;
  font-family: var(--ff-d);
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 3.5px;
  text-transform: uppercase;
  color: var(--text);
  position: relative;
  overflow: hidden;
  background: linear-gradient(
    135deg,
    rgba(73, 109, 39, 0.35),
    rgba(110, 152, 47, 0.2) 30%,
    rgba(73, 109, 39, 0.35) 60%,
    rgba(55, 85, 30, 0.45)
  );
  box-shadow:
    0 0 20px rgba(141, 187, 62, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.04),
    inset 0 -1px 0 rgba(0, 0, 0, 0.15);
  transition: all 0.2s;
}
.bp::before {
  content: "";
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    45deg,
    transparent 0 3px,
    rgba(255, 255, 255, 0.008) 3px 4px
  );
}
.bp::after {
  content: "";
  position: absolute;
  inset: -2px;
  border-radius: 7px;
  background: linear-gradient(
    135deg,
    rgba(141, 187, 62, 0.15),
    transparent,
    rgba(141, 187, 62, 0.08)
  );
  z-index: -1;
  filter: blur(4px);
  opacity: 0;
  transition: opacity 0.2s;
}
.bp:hover:not(:disabled) {
  border-color: rgba(141, 187, 62, 0.35);
  box-shadow:
    0 0 28px rgba(141, 187, 62, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
  filter: brightness(1.05);
}
.bp:hover:not(:disabled)::after {
  opacity: 1;
}
.bp:active:not(:disabled) {
  filter: brightness(0.95);
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.2);
}
.bp:disabled {
  cursor: wait;
  opacity: 0.85;
}
.bp svg {
  width: 18px;
  height: 18px;
}
.spin {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid rgba(231, 229, 217, 0.25);
  border-top-color: var(--text);
  animation: rot 0.8s linear infinite;
}
@keyframes rot {
  to {
    transform: rotate(360deg);
  }
}
</style>
