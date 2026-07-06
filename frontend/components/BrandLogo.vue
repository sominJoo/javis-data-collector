<script setup lang="ts">
// Graphio 4-bar 로고. variant에 따라 색상 팔레트가 바뀐다.
const props = withDefaults(
  defineProps<{ size?: number; variant?: "color" | "light" }>(),
  { size: 26, variant: "color" },
);

const palette = computed(() =>
  props.variant === "light"
    ? ["#ffd0e6", "#ffe9a8", "#a6f0e0", "#d9c4ff"]
    : ["#e85b9e", "#f5c23e", "#35c4a8", "#6e4fa0"],
);
const rotations = [22, 74, -38, 120];
const barW = computed(() => Math.round(props.size * 0.27));
const barH = computed(() => Math.round(props.size * 0.88));
</script>

<template>
  <span class="brand-logo" :style="{ width: `${size}px`, height: `${size}px` }">
    <span
      v-for="(color, i) in palette"
      :key="i"
      class="bar"
      :style="{
        width: `${barW}px`,
        height: `${barH}px`,
        background: color,
        transform: `rotate(${rotations[i]}deg)`,
      }"
    />
  </span>
</template>

<style scoped lang="scss">
.brand-logo {
  position: relative;
  display: inline-block;
}
.bar {
  position: absolute;
  inset: 0;
  margin: auto;
  border-radius: 5px;
}
</style>
