<script setup lang="ts">
const route = useRoute();
const auth = useAuthStore();

interface NavItem {
  to: string;
  title: string;
  match: (path: string) => boolean;
  adminOnly?: boolean;
}

const items: NavItem[] = [
  { to: "/", title: "원본 데이터", match: (p) => p === "/" || p.startsWith("/data") },
  { to: "/report-types", title: "보고서 유형", match: (p) => p.startsWith("/report-types") },
  { to: "/admin", title: "API Key 관리", match: (p) => p.startsWith("/admin"), adminOnly: true },
];

const visibleItems = computed(() => items.filter((i) => !i.adminOnly || auth.isAdmin));

function logout() {
  auth.logout();
  navigateTo("/login");
}

// 내비 아이콘 (경로별 SVG).
const icons: Record<string, string> = {
  "/": `<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/></svg>`,
  "/report-types": `<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M9 13h6M9 17h6"/></svg>`,
  "/admin": `<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3"/></svg>`,
};
function iconFor(to: string): string {
  return icons[to] ?? "";
}
</script>

<template>
  <div class="rail">
    <BrandLogo class="rail-logo" :size="30" variant="light" />

    <NuxtLink
      v-for="item in visibleItems"
      :key="item.to"
      :to="item.to"
      class="gx-nav nav-item"
      :class="{ active: item.match(route.path) }"
      :title="item.title"
    >
      <span class="nav-icon" v-html="iconFor(item.to)" />
    </NuxtLink>

    <button class="gx-nav nav-item logout" title="로그아웃" @click="logout">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
      </svg>
    </button>

    <div class="avatar">{{ auth.initial }}</div>
  </div>
</template>

<style scoped lang="scss">
.rail {
  flex: 0 0 68px;
  background: linear-gradient(180deg, var(--sb1), var(--sb2));
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 18px 0;
  gap: 6px;
  z-index: 2;
}
.rail-logo {
  margin-bottom: 16px;
}
.nav-item {
  width: 44px;
  height: 44px;
  border-radius: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  cursor: pointer;
  border: none;
  background: transparent;
  text-decoration: none;
  &.active {
    background: rgba(255, 255, 255, 0.2);
    box-shadow: 0 6px 16px -6px rgba(0, 0, 0, 0.3);
  }
}
.nav-icon {
  display: inline-flex;
}
.logout {
  margin-top: auto;
  color: rgba(255, 255, 255, 0.8);
}
.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.9);
  color: #a94fa0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 800;
}
</style>
