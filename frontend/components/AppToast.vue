<script setup lang="ts">
// 전역 토스트. 화면 하단 중앙에 잠깐 떴다 사라진다.
const ui = useUiStore();
const { toast } = storeToRefs(ui);
</script>

<template>
  <Teleport to="body">
    <Transition name="toast">
      <div v-if="toast" class="toast" :class="toast.kind">
        <span class="ico">{{ toast.kind === "err" ? "⚠" : "✓" }}</span>
        <span>{{ toast.msg }}</span>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped lang="scss">
.toast {
  position: fixed;
  bottom: 32px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 200;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 20px;
  border-radius: 12px;
  color: #fff;
  font-size: 13.5px;
  font-weight: 600;
  box-shadow: 0 16px 40px -12px rgba(20, 5, 40, 0.5);
  background: linear-gradient(135deg, #7c4da0, #c05cab);
  &.err {
    background: var(--red);
  }
}
.ico {
  font-size: 14px;
}
.toast-enter-active {
  animation: gxtoast 0.3s ease;
}
.toast-leave-active {
  animation: gxtoast 0.2s ease reverse;
}
</style>
