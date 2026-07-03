<script setup lang="ts">
// 다중 선택 드롭다운. 선택된 값은 칩으로 표시하고, 옵션 목록은 부모가 API로 조회해 넘긴다.
const model = defineModel<string[]>({ required: true });
const props = defineProps<{
  options: string[];
  placeholder?: string;
  loading?: boolean;
}>();

const open = ref(false);
const root = ref<HTMLElement | null>(null);

function toggleOption(opt: string) {
  if (model.value.includes(opt)) {
    model.value = model.value.filter((v) => v !== opt);
  } else {
    model.value = [...model.value, opt];
  }
}
function removeChip(opt: string) {
  model.value = model.value.filter((v) => v !== opt);
}
function isSelected(opt: string) {
  return model.value.includes(opt);
}

function onClickOutside(e: MouseEvent) {
  if (root.value && !root.value.contains(e.target as Node)) open.value = false;
}
onMounted(() => document.addEventListener("click", onClickOutside));
onBeforeUnmount(() => document.removeEventListener("click", onClickOutside));
</script>

<template>
  <div ref="root" class="ms">
    <div class="ms-field" :class="{ open }" @click="open = !open">
      <div class="ms-chips">
        <template v-if="model.length">
          <span v-for="v in model" :key="v" class="chip">
            {{ v }}
            <span class="chip-x" @click.stop="removeChip(v)">×</span>
          </span>
        </template>
        <span v-else class="ms-placeholder">{{ placeholder || "선택하세요" }}</span>
      </div>
      <span class="ms-caret" :class="{ up: open }">⌄</span>
    </div>

    <div v-if="open" class="ms-panel">
      <div v-if="loading" class="ms-state">불러오는 중...</div>
      <div v-else-if="options.length === 0" class="ms-state">옵션이 없습니다.</div>
      <template v-else>
        <div
          v-for="opt in options"
          :key="opt"
          class="ms-option"
          :class="{ sel: isSelected(opt) }"
          @click="toggleOption(opt)"
        >
          <span class="ms-check" :class="{ on: isSelected(opt) }">
            <svg v-if="isSelected(opt)" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3">
              <path d="M20 6 9 17l-5-5" />
            </svg>
          </span>
          <span class="ms-label">{{ opt }}</span>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped lang="scss">
.ms {
  position: relative;
}
.ms-field {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  padding: 7px 12px;
  border-radius: 10px;
  background: var(--field);
  border: 1px solid var(--fieldline);
  cursor: pointer;
  &.open {
    border-color: var(--pri);
  }
}
.ms-chips {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  min-width: 0;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--pri);
  background: var(--sel);
  padding: 4px 10px;
  border-radius: 999px;
}
.chip-x {
  cursor: pointer;
  font-size: 14px;
}
.ms-placeholder {
  font-size: 13px;
  color: var(--tx3);
}
.ms-caret {
  color: var(--tx3);
  font-size: 16px;
  line-height: 1;
  transition: transform 0.15s;
  &.up {
    transform: rotate(180deg);
  }
}
.ms-panel {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  z-index: 30;
  max-height: 240px;
  overflow: auto;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 11px;
  padding: 6px;
  box-shadow: 0 20px 44px -20px rgba(20, 5, 40, 0.4);
  animation: gxpop 0.16s ease;
}
.ms-state {
  padding: 16px;
  text-align: center;
  font-size: 12.5px;
  color: var(--tx3);
}
.ms-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 8px;
  cursor: pointer;
  &:hover {
    background: var(--panel2);
  }
  &.sel {
    background: var(--sel);
  }
}
.ms-check {
  width: 18px;
  height: 18px;
  border-radius: 5px;
  border: 1.5px solid var(--line2);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  &.on {
    background: var(--pri);
    border-color: var(--pri);
  }
}
.ms-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--tx);
}
</style>
