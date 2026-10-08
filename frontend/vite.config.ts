import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],

  test: {
    environment: "node",
    globals: true,

    env: {
      VITE_API_BASE_URL: "http://localhost:8000",
      VITE_SUPABASE_URL:
        "https://test-project.supabase.co",
      VITE_SUPABASE_ANON_KEY:
        "test-anon-key",
    },
  },
});