<template>
  <div class="cd np">
    <div class="nh">
      <span class="nt">News</span><span class="nva">View All</span>
    </div>
    <div class="nb">
      <div v-for="item in items" :key="item.id" class="ni2" :title="item.body">
        <div class="nt2">{{ item.title }}</div>
        <div class="nd">{{ formatDate(item.date) }}<span v-if="item.tag"> &middot; {{ item.tag }}</span></div>
      </div>
      <div v-if="!items.length" class="empty">No news yet.</div>
    </div>
  </div>
</template>

<script>
export default {
  name: "NewsPanel",
  props: { items: { type: Array, required: true } },
  methods: {
    formatDate(iso) {
      if (!iso) return "";
      const d = new Date(iso);
      return isNaN(d)
        ? iso
        : d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
    },
  },
};
</script>

<style scoped>
.np {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.nh {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid var(--brd);
}
.nt {
  font-family: var(--ff-d);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-gd);
}
.nva {
  font-size: 7.5px;
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--text-2);
  cursor: pointer;
}
.nva:hover {
  color: var(--primary);
}
.nb {
  padding: 2px 14px 8px;
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}
.ni2 {
  padding: 8px 0;
  border-bottom: 1px solid rgba(150, 180, 100, 0.04);
}
.ni2:last-child {
  border-bottom: 0;
}
.nt2 {
  font-size: 11px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 2px;
}
.nd {
  font-size: 8px;
  color: var(--text-m);
}
.empty {
  padding: 14px 0;
  font-size: 9.5px;
  color: var(--text-m);
}
</style>
