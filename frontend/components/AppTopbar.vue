<script setup lang="ts">
defineProps<{ crumb?: string }>();

const theme = useThemeStore();
const auth = useAuthStore();
</script>

<template>
  <div class="topbar">
    <div class="crumb">{{ crumb }}</div>
    <div class="right">
      <button class="gx-btn theme-toggle" @click="theme.toggle()">
        {{ theme.icon }} {{ theme.label }}
      </button>
      <div class="user">
        <div class="user-avatar">{{ auth.initial }}</div>
        <span class="user-name">{{ auth.displayName }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.topbar {
  height: 60px;
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  padding: 0 26px;
  gap: 14px;
  background: var(--panel);
  z-index: 1;
}
.crumb {
  font-size: 14px;
  color: var(--tx3);
}
.right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
}
.theme-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 13px;
  border-radius: 999px;
  border: 1px solid var(--line2);
  background: var(--panel);
  color: var(--tx);
  font-size: 12.5px;
  font-weight: 600;
}
.user {
  display: flex;
  align-items: center;
  gap: 8px;
}
.user-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: linear-gradient(135deg, #7c4da0, #c05cab);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 800;
}
.user-name {
  font-size: 13px;
  font-weight: 600;
}
</style>
