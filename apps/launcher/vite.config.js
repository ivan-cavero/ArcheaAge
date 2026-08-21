import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  clearScreen: false,
  plugins: [vue()],
  server: {
    host: "127.0.0.1",
    port: 1420,
    strictPort: true,
    // Cargo rewrites DLLs under src-tauri/target while Vite starts watching
    // them → EBUSY on Windows kills the dev server. Rust changes rebuild via
    // cargo itself; the frontend never needs to watch that tree.
    watch: {
      ignored: ["**/src-tauri/**"],
    },
  },
  build: {
    target: "esnext",
  },
});
