<script setup lang="ts">
// 로그인/관리자 로그인 공용 레이아웃 (중앙 정렬 카드 배경).
</script>

<template>
  <div class="auth-bg">
    <div class="brand">
      <BrandLogo :size="26" />
      <span class="brand-name">Graphio</span>
    </div>
    <slot />
    <ClientOnly>
      <AppToast />
      <AppConfirm />
    </ClientOnly>
  </div>
</template>

<style scoped lang="scss">
.auth-bg {
  height: 100vh;
  width: 100%;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(1100px 620px at 50% -10%, var(--sel), var(--bg) 60%);
}
.brand {
  position: absolute;
  top: 30px;
  left: 38px;
  display: flex;
  align-items: center;
  gap: 9px;
}
.brand-name {
  font-size: 19px;
  font-weight: 800;
  letter-spacing: -0.02em;
}
</style>
