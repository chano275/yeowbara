import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0",
    allowedHosts: [
      "localhost",
      "127.0.0.1",
      "k12b107.p.ssafy.io",
      "react",  // Docker 서비스 이름
    ],
    port: 5173,
    https: false,
    hmr: {
      protocol: 'ws',              // https 쓰는 경우 'wss'
      host: 'k12b107.p.ssafy.io',  // 외부에서 접근하는 도메인
      port: 5173,                  // HMR 전용 포트 (기본은 서버 포트)
      clientPort: 5173             // 클라이언트가 연결할 포트
    },
    proxy: {
      // /api로 들어오는 요청은 fastapi 컨테이너로 포워딩
      "/api": {
        target: "http://fastapi:8000",
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
