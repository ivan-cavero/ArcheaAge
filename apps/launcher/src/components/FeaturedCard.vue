<template>
  <div class="cd fc">
    <div class="fbg"></div>
    <div class="fct">
      <div class="fcl">Custom Content</div>
      <div class="fcti">New Zones</div>
      <div class="fcd">
        Discover new lands<br />created by our community.
      </div>
      <a href="#" class="fcb">Explore</a>
    </div>
  </div>
</template>

<script>
export default { name: "FeaturedCard" };
</script>

<style scoped>
.fc {
  overflow: hidden;
  min-height: 100px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}
.fbg {
  position: absolute;
  inset: 0;
  background: url("/images/hero-bg.jpg") center/cover no-repeat;
  opacity: 0.18;
  filter: saturate(0.5) brightness(0.8);
}
.fbg::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgba(7, 16, 13, 0.1) 0%,
    rgba(7, 16, 13, 0.82) 100%
  );
}
.fct {
  position: relative;
  z-index: 1;
  padding: 12px 14px;
}
.fcl {
  font-size: 7px;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--primary-2);
  margin-bottom: 3px;
}
.fcti {
  font-family: var(--ff-d);
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 3px;
}
.fcd {
  font-size: 9px;
  color: var(--text-2);
  line-height: 1.35;
  margin-bottom: 8px;
}
.fcb {
  display: inline-flex;
  padding: 5px 12px;
  border-radius: 3px;
  border: 1px solid var(--brd-s);
  background: rgba(10, 18, 16, 0.7);
  font-size: 8px;
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--text);
  cursor: pointer;
  text-decoration: none;
  transition: all 0.12s;
}
.fcb:hover {
  border-color: var(--primary-2);
  color: var(--primary);
}
</style>
