import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 开发期由 Vite 代理后端，前端统一使用相对路径 /api/v1（契约 C1：JWT 走 Authorization 头）
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: true } },
  },
});
