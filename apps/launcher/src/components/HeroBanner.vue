<template>
  <section class="hero">
    <div class="hero-bg"></div>
    <div class="hero-v"></div>
    <div class="hero-body">
      <span class="hero-ov">Welcome to</span>
      <h2 class="hero-t">ArcheaAge</h2>
      <span class="hero-tag">Your adventure, your world.</span>
      <p class="hero-desc">
        Open source private ArcheAge server.<br />Community powered.
        Player driven.
      </p>
    </div>
    <div class="hero-u">
      <div class="u-badge">
        <span class="u-dot"></span>
        <span class="u-name">Adventurer</span>
        <span class="u-st">Online</span>
        <span class="u-ch">&#9662;</span>
      </div>
    </div>
  </section>
</template>

<script>
export default { name: "HeroBanner" };
</script>

<style scoped>
.hero {
  position: relative;
  height: 300px;
  flex-shrink: 0;
  display: grid;
  grid-template-columns: 1fr 240px;
  overflow: hidden;
}
.hero-bg {
  position: absolute;
  inset: 0;
  background: url("/images/hero-library.jpg") 20% center/cover no-repeat;
  filter: saturate(0.6) brightness(0.85) contrast(1.05);
}
.hero-bg::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    rgba(7, 16, 13, 0.92) 0%,
    rgba(7, 16, 13, 0.7) 20%,
    rgba(7, 16, 13, 0.35) 50%,
    rgba(7, 16, 13, 0.08) 85%,
    rgba(7, 16, 13, 0.02) 100%
  );
}
.hero-bg::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    transparent 25%,
    rgba(7, 16, 13, 0.5) 70%,
    var(--bg) 100%
  );
}
.hero-v {
  position: absolute;
  inset: 0;
  background: radial-gradient(
    ellipse at 70% 40%,
    transparent 40%,
    rgba(7, 16, 13, 0.25) 100%
  );
  z-index: 1;
}
.hero-body {
  position: relative;
  z-index: 2;
  padding: 36px 40px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
}
.hero-ov {
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 3.5px;
  text-transform: uppercase;
  color: var(--text-2);
  margin-bottom: 3px;
}
.hero-t {
  font-family: var(--ff-d);
  font-weight: 900;
  font-size: 48px;
  letter-spacing: 4px;
  line-height: 1;
  text-transform: uppercase;
  color: var(--text);
  text-shadow: 0 2px 16px rgba(0, 0, 0, 0.4);
}
.hero-tag {
  font-family: var(--ff-d);
  font-size: 18px;
  font-weight: 500;
  color: var(--primary);
  font-style: italic;
  margin-top: 6px;
}
.hero-desc {
  font-size: 12px;
  color: var(--text-2);
  line-height: 1.7;
  margin-top: 8px;
  max-width: 380px;
}
.hero-u {
  position: relative;
  z-index: 2;
  display: flex;
  justify-content: flex-end;
  padding: 18px 20px 0 0;
}
.u-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 4px;
  background: rgba(16, 26, 23, 0.85);
  border: 1px solid var(--brd);
  backdrop-filter: blur(4px);
  cursor: pointer;
  transition: border-color 0.12s;
}
.u-badge:hover {
  border-color: var(--primary-d);
}
.u-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--on);
  box-shadow: 0 0 4px var(--on);
}
.u-name {
  font-size: 11px;
  font-weight: 600;
  color: var(--text);
}
.u-st {
  font-size: 10px;
  color: var(--text-2);
}
.u-ch {
  font-size: 8px;
  color: var(--text-m);
  margin-left: 2px;
}
</style>
