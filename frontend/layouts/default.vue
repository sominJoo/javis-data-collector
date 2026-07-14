<script setup lang="ts">
// 앱 셸: 좌측 레일 + 상단바 + 콘텐츠.
// 세션(localStorage) 의존 UI라 ClientOnly로 감싸 SSR/hydration mismatch를 방지한다.
const crumb = useCrumb();
</script>

<template>
  <ClientOnly>
    <div class="shell">
      <AppRail />
      <div class="main">
        <AppTopbar :crumb="crumb" />
        <div class="content">
          <slot />
        </div>
      </div>
      <AppToast />
      <AppConfirm />
    </div>
    <template #fallback>
      <div class="boot">불러오는 중...</div>
    </template>
  </ClientOnly>
</template>

<style scoped lang="scss">
.shell {
  height: 100vh;
  display: flex;
}
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.content {
  flex: 1;
  overflow: auto;
  background: var(--panel2);
}
.boot {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--tx3);
  font-size: 14px;
}
</style>
