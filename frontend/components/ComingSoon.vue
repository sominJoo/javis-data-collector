<script setup lang="ts">
defineProps<{ title: string }>();
</script>

<template>
  <div class="coming">
    <div class="box">
      <div class="emoji">🚧</div>
      <h3>{{ title }}</h3>
      <p>이 화면은 다음 단계에서 구현될 예정입니다.</p>
      <NuxtLink to="/" class="link">← 원본 데이터 목록으로</NuxtLink>
    </div>
  </div>
</template>

<style scoped lang="scss">
.coming {
  padding: 60px 28px;
  animation: gxfade 0.3s ease;
  display: flex;
  justify-content: center;
}
.box {
  text-align: center;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 48px 60px;
}
.emoji {
  font-size: 40px;
  margin-bottom: 16px;
}
h3 {
  font-size: 20px;
  font-weight: 800;
  margin: 0 0 8px;
}
p {
  font-size: 13.5px;
  color: var(--tx3);
  margin: 0 0 20px;
}
.link {
  font-size: 13px;
  font-weight: 600;
  color: var(--pri);
  text-decoration: none;
}
</style>
