<template>
  <div class="frame">
    <SideBar :active-tab="activeTab" :registry-ok="registryOk" @navigate="activeTab = $event" />

    <div class="mn">
      <TitleBar />
      <HeroBanner />

      <template v-if="activeTab === 'home'">
        <div class="ct">
          <div class="ct-l">
            <VersionChips
              :versions="versions"
              :selected-id="selectedVersionId"
              @select="selectVersion"
            />
            <ServerPanel
              :servers="servers"
              :loading="serversLoading"
              v-model:query="serverQuery"
              :selected-id="selectedServerId"
              :show-all="showAllServers"
              @refresh="loadServers"
              @select-server="selectedServerId = $event"
              @toggle-all="showAllServers = !showAllServers"
            />
          </div>
          <div class="ct-r">
            <NewsPanel :items="newsItems" />
            <FeaturedCard />
            <PluginSpotlight />
          </div>
        </div>
      </template>

      <div v-else class="ct ct-single">
        <EmptyState :title="tabTitle" />
      </div>

      <ClientBar
        :version-label="versionLabel"
        :status="clientStatus"
        :progress="progress"
        :busy="busy"
        @open-dir="openDir"
        @choose-dir="chooseDir"
      >
        <PlayButton :label="primaryLabel" :busy="busy" @press="primaryAction" />
      </ClientBar>

      <FooterBar />
    </div>
  </div>
</template>

<script>
import SideBar from "./components/SideBar.vue";
import TitleBar from "./components/TitleBar.vue";
import HeroBanner from "./components/HeroBanner.vue";
import VersionChips from "./components/VersionChips.vue";
import ServerPanel from "./components/ServerPanel.vue";
import NewsPanel from "./components/NewsPanel.vue";
import FeaturedCard from "./components/FeaturedCard.vue";
import PluginSpotlight from "./components/PluginSpotlight.vue";
import ClientBar from "./components/ClientBar.vue";
import PlayButton from "./components/PlayButton.vue";
import EmptyState from "./components/EmptyState.vue";
import FooterBar from "./components/FooterBar.vue";
import * as registry from "./services/registry.js";
import {
  IN_TAURI,
  onClientProgress,
  clientStatus,
  clientEnsure,
  clientLaunch,
  openInstallDir,
  setInstallDir,
} from "./services/backend.js";

const SERVERS_POLL_MS = 10_000;

// Browser-demo seed so `npm run dev` outside Tauri still shows a living UI.
const DEMO_VERSIONS = [
  { id: "1.2", name: "ArcheAge 1.2 (launch era)", client: "1.2.4.0 (r208022)", status: "live" },
  { id: "3.5", name: "ArcheAge 3.5 (golden age)", client: "3.5 (r1299)", status: "planned" },
  { id: "6.0", name: "ArcheAge 6.0", client: "", status: "planned" },
];
const DEMO_SERVERS = [
  { id: "eu-1", name: "ArcheaAge EU-1", status: "online", players: 84, maxPlayers: 500 },
];

export default {
  name: "App",
  components: {
    SideBar,
    TitleBar,
    HeroBanner,
    VersionChips,
    ServerPanel,
    NewsPanel,
    FeaturedCard,
    PluginSpotlight,
    ClientBar,
    PlayButton,
    EmptyState,
    FooterBar,
  },

  data() {
    return {
      activeTab: "home",
      registryOk: true,
      versions: [],
      selectedVersionId: null,
      servers: [],
      serversLoading: false,
      serverQuery: "",
      showAllServers: false,
      selectedServerId: null,
      newsItems: [],
      clientStatus: { installed: false, verified: false },
      progress: { active: false, stage: "", file: "", downloaded: 0, total: 0 },
      busy: false,
      _pollTimer: null,
      _unlisten: null,
    };
  },

  computed: {
    selectedVersion() {
      return this.versions.find((v) => v.id === this.selectedVersionId) || null;
    },
    versionLabel() {
      const v = this.selectedVersion;
      if (!v) return "—";
      return v.client ? `ArcheAge ${v.client}` : `ArcheAge ${v.id}`;
    },
    primaryLabel() {
      if (this.busy) return "Working";
      if (!this.clientStatus.installed) return "Download";
      return "Play";
    },
    tabTitle() {
      const t = this.activeTab;
      return t.charAt(0).toUpperCase() + t.slice(1);
    },
  },

  async mounted() {
    await Promise.all([this.loadVersions(), this.loadNews()]);
    await this.refreshClient();

    this._pollTimer = setInterval(() => {
      if (this.selectedVersionId) this.loadServers();
    }, SERVERS_POLL_MS);

    this._unlisten = await onClientProgress((p) => {
      this.progress = { ...this.progress, active: p.stage !== "done", ...p };
      if (p.stage === "done") {
        this.busy = false;
        this.refreshClient();
      }
    });
  },

  beforeUnmount() {
    if (this._pollTimer) clearInterval(this._pollTimer);
    if (this._unlisten) this._unlisten();
  },

  methods: {
    async loadVersions() {
      try {
        this.versions = await registry.fetchVersions();
        this.registryOk = true;
        if (!IN_TAURI && !this.versions.length) this.versions = DEMO_VERSIONS;
      } catch {
        this.registryOk = false;
        if (!IN_TAURI) {
          this.versions = DEMO_VERSIONS;
          this.servers = DEMO_SERVERS;
        }
        return;
      }
      const live = this.versions.find((v) => v.status === "live");
      if (live) await this.selectVersion(live.id);
    },

    async loadNews() {
      const d = await registry.fetchNews();
      this.newsItems = (d.items || []).slice(0, 5);
    },

    async selectVersion(id) {
      if (this.selectedVersionId === id) return;
      this.selectedVersionId = id;
      this.selectedServerId = null;
      this.showAllServers = false;
      this.serverQuery = "";
      await Promise.all([this.loadServers(), this.refreshClient()]);
    },

    async loadServers() {
      if (!this.selectedVersionId) return;
      this.serversLoading = true;
      try {
        this.servers = await registry.fetchServers(this.selectedVersionId);
        if (
          this.selectedServerId &&
          !this.servers.some((s) => s.id === this.selectedServerId)
        ) {
          this.selectedServerId = null;
        }
      } finally {
        this.serversLoading = false;
      }
    },

    async refreshClient() {
      if (!this.selectedVersionId) return;
      try {
        this.clientStatus = await clientStatus(this.selectedVersionId);
      } catch {
        /* keep last known state */
      }
    },

    async primaryAction() {
      if (!this.selectedVersionId || this.busy) return;
      this.busy = true;
      try {
        if (!this.clientStatus.installed) {
          this.progress = { active: true, stage: "starting", file: "", downloaded: 0, total: 0 };
          this.clientStatus = await clientEnsure(this.selectedVersionId);
          this.progress = { ...this.progress, active: false, stage: "done" };
        } else {
          const serverId = this.selectedServerId || "";
          await clientLaunch(this.selectedVersionId, serverId);
        }
      } catch (e) {
        console.error("primaryAction failed:", e);
        alert(`Play failed:\n${e}`);
        this.progress = { ...this.progress, active: false };
      } finally {
        this.busy = false;
        this.refreshClient();
      }
    },

    openDir() {
      if (this.selectedVersionId) openInstallDir(this.selectedVersionId);
    },

    /** Lets the user point this version at an existing game install. */
    async chooseDir() {
      if (!this.selectedVersionId || this.busy || !IN_TAURI) return;
      try {
        const { open } = await import("@tauri-apps/plugin-dialog");
        const picked = await open({
          directory: true,
          multiple: false,
          title: "Select the ArcheAge install folder",
        });
        console.log("chooseDir picked:", picked);
        const dir =
          typeof picked === "string"
            ? picked
            : Array.isArray(picked)
              ? picked[0]
              : (picked && picked.path) || "";
        if (!dir) return;
        this.busy = true;
        const st = await setInstallDir(this.selectedVersionId, dir);
        this.clientStatus = st;
      } catch (e) {
        console.error("chooseDir failed:", e);
        alert(`chooseDir failed:\n${e}`);
      } finally {
        this.busy = false;
        this.refreshClient();
      }
    },
  },
};
</script>

<style scoped>
.frame {
  width: 100vw;
  height: 100vh;
  display: grid;
  grid-template-columns: 210px 1fr;
  overflow: hidden;
}
.mn {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.ct {
  flex: 1;
  overflow: hidden;
  display: grid;
  grid-template-columns: 1fr 260px;
  gap: 14px;
  padding: 10px 22px 14px;
}
.ct-single {
  grid-template-columns: 1fr;
  place-items: center;
}
.ct-l {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}
.ct-r {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}
</style>
