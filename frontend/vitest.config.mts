import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

/**
 * Unit and component tests.
 *
 * `.mts` so the file is loaded as ESM. Path aliases ("@/...") are resolved
 * natively from tsconfig.json, so imports read exactly as they do in the app.
 */
export default defineConfig({
  plugins: [react()],
  resolve: { tsconfigPaths: true },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    css: false,
    // Spies are restored and vi.fn() call history is reset between tests;
    // without clearMocks a hoisted module mock keeps calls from earlier tests.
    restoreMocks: true,
    clearMocks: true,
    coverage: {
      reporter: ["text", "lcov"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/**/*.{test,spec}.{ts,tsx}", "src/components/ui/**"],
    },
  },
});
