<script setup lang="ts">
// 전역 확인 다이얼로그. useConfirm()으로 열고, 확인/취소 선택을 Promise로 반환한다.
const ui = useUiStore();
const { confirmOptions } = storeToRefs(ui);
</script>

<template>
  <Teleport to="body">
    <div
      v-if="confirmOptions"
      class="overlay"
      @click.self="ui.resolveConfirm(false)"
    >
      <div class="dialog">
        <div class="icon" :class="{ danger: confirmOptions.danger }">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <path d="M12 9v4M12 17h.01" />
          </svg>
        </div>
        <h4>{{ confirmOptions.title }}</h4>
        <p>{{ confirmOptions.message }}</p>
        <div class="actions">
          <button class="btn-ghost" @click="ui.resolveConfirm(false)">취소</button>
          <button
            class="btn-ok"
            :class="{ danger: confirmOptions.danger }"
            @click="ui.resolveConfirm(true)"
          >
            {{ confirmOptions.okText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped lang="scss">
.overlay {
  position: fixed;
  inset: 0;
  z-index: 190;
  background: rgba(30, 15, 45, 0.42);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  animation: gxfade 0.2s ease;
}
.dialog {
  width: 400px;
  max-width: 100%;
  background: var(--panel);
  border-radius: 16px;
  padding: 28px;
  box-shadow: 0 40px 90px -30px rgba(20, 5, 40, 0.6);
  animation: gxpop 0.25s ease;
}
.icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--sel);
  color: var(--pri);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  &.danger {
    background: var(--red-bg);
    color: var(--red);
  }
}
h4 {
  font-size: 17px;
  font-weight: 800;
  margin: 0 0 8px;
}
p {
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--tx2);
  margin: 0 0 22px;
}
.actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}
.btn-ghost {
  height: 42px;
  padding: 0 20px;
  border-radius: 11px;
  border: 1px solid var(--line2);
  background: var(--panel);
  color: var(--tx);
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
}
.btn-ok {
  height: 42px;
  padding: 0 22px;
  border-radius: 11px;
  border: none;
  color: #fff;
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
  background: linear-gradient(135deg, #7c4da0, #c05cab);
  &.danger {
    background: var(--red);
  }
}
</style>
