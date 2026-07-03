<script setup lang="ts">
definePageMeta({ layout: "auth" });

const api = useApi();
const auth = useAuthStore();

const apiKey = ref("");
const error = ref("");
const loading = ref(false);

async function doLogin() {
  error.value = "";
  loading.value = true;
  try {
    const session = await api.login(apiKey.value);
    auth.setSession(session);
    await navigateTo("/");
  } catch (e) {
    error.value = e instanceof Error ? e.message : "로그인에 실패했습니다.";
  } finally {
    loading.value = false;
  }
}

function fillDemo() {
  apiKey.value = "sk-graphio-demo-0000";
}
</script>

<template>
  <div class="card">
    <div class="icon-box">
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2">
        <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3" />
      </svg>
    </div>
    <h2>데이터 수집기 로그인</h2>
    <p class="sub">발급받은 API Key로 접속하세요.</p>

    <label>API Key</label>
    <div class="field" :class="{ 'field-error': error }">
      <input
        v-model="apiKey"
        placeholder="sk-graphio-..."
        class="mono"
        @keyup.enter="doLogin"
      />
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#9c99ab" stroke-width="2">
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
        <circle cx="12" cy="12" r="3" />
      </svg>
    </div>
    <div v-if="error" class="err">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10" /><path d="M12 8v4M12 16h.01" />
      </svg>
      {{ error }}
    </div>

    <button class="gx-btn submit" :disabled="loading" @click="doLogin">
      {{ loading ? "로그인 중..." : "로그인" }}
    </button>

    <div class="foot">
      API Key가 없으신가요? <span class="link">관리자 문의</span> ·
      <NuxtLink to="/admin-login" class="link">관리자 로그인</NuxtLink>
    </div>
    <div class="demo"><span @click="fillDemo">데모 키 자동 입력</span></div>
  </div>
</template>

<style scoped lang="scss">
.card {
  width: 440px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 22px;
  padding: 48px 46px;
  box-shadow: 0 40px 80px -34px rgba(50, 25, 70, 0.4);
  animation: gxpop 0.35s ease;
}
.icon-box {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: linear-gradient(135deg, #7c4da0, #c05cab);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  box-shadow: 0 14px 28px -12px rgba(160, 60, 150, 0.6);
}
h2 {
  font-size: 26px;
  font-weight: 800;
  letter-spacing: -0.02em;
  margin: 0 0 8px;
}
.sub {
  font-size: 14px;
  line-height: 1.6;
  color: var(--tx2);
  margin: 0 0 30px;
}
label {
  display: block;
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 9px;
}
.field {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 52px;
  padding: 0 16px;
  border-radius: 12px;
  background: var(--field);
  border: 1.5px solid var(--fieldline);
  margin-bottom: 10px;
  &.field-error {
    border-color: var(--red);
  }
  input {
    border: none;
    outline: none;
    background: transparent;
    font-size: 14px;
    color: var(--tx);
    flex: 1;
    width: 100%;
  }
  .mono {
    font-family: ui-monospace, monospace;
  }
}
.err {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  color: var(--red);
  margin-bottom: 14px;
}
.submit {
  width: 100%;
  height: 50px;
  margin-top: 8px;
  border-radius: 12px;
  border: none;
  background: linear-gradient(135deg, #7c4da0, #c05cab);
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  box-shadow: 0 14px 28px -12px rgba(160, 60, 150, 0.55);
  &:disabled {
    opacity: 0.7;
    cursor: default;
  }
}
.foot {
  margin-top: 24px;
  text-align: center;
  font-size: 12.5px;
  color: var(--tx3);
}
.link {
  color: var(--pri);
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
}
.demo {
  margin-top: 16px;
  text-align: center;
  span {
    font-size: 11.5px;
    color: var(--tx3);
    cursor: pointer;
    text-decoration: underline;
  }
}
</style>
