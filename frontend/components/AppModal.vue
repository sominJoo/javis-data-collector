<script setup lang="ts">
// 재사용 모달 (오버레이 + 카드). v-model:open 으로 표시 제어.
const open = defineModel<boolean>("open", { required: true });
defineProps<{ title?: string }>();

function close() {
  open.value = false;
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="overlay" @click.self="close">
      <div class="modal">
        <div class="modal-head">
          <span class="modal-title">{{ title }}</span>
          <button class="close" @click="close">✕</button>
        </div>
        <div class="modal-body">
          <slot />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped lang="scss">
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(20, 12, 30, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 24px;
}
.modal {
  width: 100%;
  max-width: 640px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: 0 40px 80px -34px rgba(50, 25, 70, 0.5);
  animation: gxpop 0.25s ease;
}
.modal-head {
  display: flex;
  align-items: center;
  padding: 18px 22px;
  border-bottom: 1px solid var(--line);
}
.modal-title {
  font-size: 15px;
  font-weight: 800;
}
.close {
  margin-left: auto;
  border: none;
  background: transparent;
  color: var(--tx3);
  cursor: pointer;
  font-size: 16px;
}
.modal-body {
  padding: 22px;
  overflow: auto;
}
</style>
