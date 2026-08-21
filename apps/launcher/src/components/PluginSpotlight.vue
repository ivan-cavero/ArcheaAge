<template>
  <div class="cd pp">
    <div class="ppl">Plugin Spotlight</div>
    <div class="ppc">
      <div class="ppi">
        <svg viewBox="0 0 24 24" fill="currentColor"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg>
      </div>
      <div>
        <div class="ppn">Example Plugin</div>
        <div class="ppd">
          Enhances gameplay with<br />new features and more.
        </div>
        <a href="#" class="ppl2">Browse Plugins &rarr;</a>
      </div>
    </div>
  </div>
</template>

<script>
export default { name: "PluginSpotlight" };
</script>

<style scoped>
.pp {
  padding: 12px 14px;
}
.ppl {
  font-size: 7.5px;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-gd);
  margin-bottom: 9px;
}
.ppc {
  display: flex;
  align-items: center;
  gap: 10px;
}
.ppi {
  width: 38px;
  height: 38px;
  border-radius: 6px;
  background: linear-gradient(135deg, var(--surface-el), var(--surface));
  border: 1px solid var(--brd);
  display: grid;
  place-items: center;
  color: var(--gold);
  flex-shrink: 0;
}
.ppi svg {
  width: 17px;
  height: 17px;
}
.ppn {
  font-size: 11px;
  font-weight: 600;
  color: var(--text);
}
.ppd {
  font-size: 8px;
  color: var(--text-2);
  margin-top: 1px;
  line-height: 1.3;
}
.ppl2 {
  font-size: 8px;
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--primary-2);
  text-decoration: none;
  margin-top: 4px;
  display: inline-block;
}
.ppl2:hover {
  color: var(--primary);
}
</style>
