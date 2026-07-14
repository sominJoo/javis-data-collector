export default defineNuxtConfig({
  compatibilityDate: "2026-01-01",
  devtools: { enabled: true },
  modules: ["@pinia/nuxt"],
  css: ["~/assets/scss/main.scss"],
  typescript: {
    strict: true,
  },
  app: {
    head: {
      title: "데이터 수집기",
      link: [
        {
          rel: "stylesheet",
          href: "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css",
        },
      ],
    },
  },
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1",
    },
  },
});
