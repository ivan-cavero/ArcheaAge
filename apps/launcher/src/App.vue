<template>
  <div class="frame">
    <SideBar :active-tab="activeTab" :registry-ok="registryOk" @navigate="activeTab = $event" />

    <div class="mn">
      <TitleBar :user="login || ''" @logout="logout" />
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
        :error="lastError"
        @open-dir="openDir"
        @choose-dir="chooseDir"
        @dismiss-error="lastError = ''"
      >
        <PlayButton :label="primaryLabel" :busy="busy" @press="primaryAction" />
      </ClientBar>

      <FooterBar />

      <div v-if="showLogin" class="lmodal" @click.self="showLogin = false">
        <div class="lcard">
          <h3 class="lt">Log in</h3>
          <input
            v-model="form.user"
            class="lin"
            placeholder="Username"
            autocomplete="username"
            @keyup.enter="submitLogin"
          />
          <input
            v-model="form.pass"
            class="lin"
            type="password"
            placeholder="Password"
            autocomplete="current-password"
            @keyup.enter="submitLogin"
          />
          <div v-if="loginError" class="lerr">{{ loginError }}</div>
          <p class="lnote">
            Credentials stay on this PC. The server creates your account
            automatically on first login.
          </p>
          <div class="lrow">
            <button class="lbtn pri" :disabled="busy" @click="submitLogin">Log In</button>
            <button class="lbtn" @click="showLogin = false">Cancel</button>
          </div>
        </div>
      </div>
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
  authLogin,
  authStatus,
  authLogout,
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
      login: null,
      showLogin: false,
      loginError: "",
      form: { user: "", pass: "" },
      lastError: "",
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
      if (!this.login) return "Log In";
      return "Play";
    },
    tabTitle() {
      const t = this.activeTab;
      return t.charAt(0).toUpperCase() + t.slice(1);
    },
  },

  async mounted() {
    await Promise.all([this.loadVersions(), this.loadNews()]);
    try {
      const s = await authStatus();
      this.login = s && s.username ? s.username : null;
    } catch {
      /* not in Tauri or not logged */
    }
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
      this.lastError = "";
      if (!this.clientStatus.installed) {
        this.busy = true;
        try {
          this.progress = { active: true, stage: "starting", file: "", downloaded: 0, total: 0 };
          this.clientStatus = await clientEnsure(this.selectedVersionId);
          this.progress = { ...this.progress, active: false, stage: "done" };
        } catch (e) {
          console.error("ensure failed:", e);
          this.lastError = String(e);
          this.progress = { ...this.progress, active: false };
        } finally {
          this.busy = false;
          this.refreshClient();
        }
        return;
      }
      if (!this.login) {
        this.showLogin = true;
        return;
      }
      this.busy = true;
      try {
        await clientLaunch(this.selectedVersionId, this.selectedServerId || "");
      } catch (e) {
        console.error("launch failed:", e);
        this.lastError = String(e);
      } finally {
        this.busy = false;
        this.refreshClient();
      }
    },

    /** Opens the install folder of a version in Windows Explorer. */
    openDir() {
      if (this.selectedVersionId) openInstallDir(this.selectedVersionId);
    },

    /** Lets the user point this version at an existing game install. */
    async chooseDir() {
      if (!this.selectedVersionId || this.busy || !IN_TAURI) return;
      this.lastError = "";
      try {
        const { open } = await import("@tauri-apps/plugin-dialog");
        const picked = await open({
          directory: true,
          multiple: false,
          title: "Select the ArcheAge install folder",
        });
        const dir =
          typeof picked === "string"
            ? picked
            : Array.isArray(picked)
              ? picked[0]
              : (picked && picked.path) || "";
        if (!dir) return;
        this.busy = true;
        this.clientStatus = await setInstallDir(this.selectedVersionId, dir);
      } catch (e) {
        console.error("chooseDir failed:", e);
        this.lastError = String(e);
      } finally {
        this.busy = false;
        this.refreshClient();
      }
    },

    /** Saves credentials (hashed) and closes the login modal. */
    async submitLogin() {
      if (!this.form.user || !this.form.pass) {
        this.loginError = "Enter username and password.";
        return;
      }
      this.busy = true;
      this.loginError = "";
      try {
        const s = await authLogin(this.form.user, this.form.pass);
        this.login = s.username;
        this.showLogin = false;
        this.form = { user: "", pass: "" };
      } catch (e) {
        console.error("login failed:", e);
        this.loginError = String(e);
      } finally {
        this.busy = false;
      }
    },

    /** Clears saved credentials. */
    async logout() {
      try {
        await authLogout();
      } catch {
        /* ignore */
      }
      this.login = null;
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
.lmodal {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: grid;
  place-items: center;
  background: rgba(4, 10, 8, 0.72);
  backdrop-filter: blur(3px);
}
.lcard {
  width: 300px;
  padding: 18px;
  background: var(--bg);
  border: 1px solid var(--brd);
  border-radius: 6px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  gap: 9px;
}
.lt {
  margin: 0;
  font-family: var(--ff-d);
  font-size: 13px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text);
}
.lin {
  padding: 8px 10px;
  border: 1px solid var(--brd);
  border-radius: 3px;
  background: var(--surface);
  color: var(--text);
  font-size: 12px;
  outline: none;
}
.lin:focus {
  border-color: var(--primary-d);
}
.lerr {
  font-size: 11px;
  color: #e08a8a;
}
.lnote {
  margin: 0;
  font-size: 10px;
  line-height: 1.5;
  color: var(--text-m);
}
.lrow {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.lbtn {
  padding: 7px 14px;
  border: 1px solid var(--brd);
  border-radius: 3px;
  background: var(--surface);
  color: var(--text-2);
  font-size: 11px;
  cursor: pointer;
}
.lbtn:hover {
  color: var(--text);
  border-color: var(--text-m);
}
.lbtn.pri {
  background: var(--primary-d, #2f6b3a);
  border-color: var(--primary-d, #2f6b3a);
  color: #eaf2ea;
  font-weight: 600;
}
</style>
