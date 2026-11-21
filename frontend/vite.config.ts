import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const here = fileURLToPath(new URL(".", import.meta.url));
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    cors: false,
    allowedHosts: ["localhost", "127.0.0.1"],
    fs: {
      strict: true,
      allow: [
        here,
        fileURLToPath(new URL("../examples/planning", import.meta.url)),
        fileURLToPath(new URL("../examples/scheduling", import.meta.url)),
      ],
    },
  },
  preview: { host: "127.0.0.1", port: 5173, strictPort: true },
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/**/*.test.{ts,tsx}"],
    restoreMocks: true,
  },
});
