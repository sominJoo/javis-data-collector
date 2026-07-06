<script setup lang="ts">
definePageMeta({ layout: "auth" });

const api = useApi();
const auth = useAuthStore();

const adminId = ref("");
const adminPw = ref("");
const error = ref("");
const loading = ref(false);

async function doAdminLogin() {
  error.value = "";
  loading.value = true;
  try {
    const session = await api.adminLogin(adminId.value, adminPw.value);
    auth.setSession(session);
    await navigateTo("/");
  } catch (e) {
    error.value = e instanceof Error ? e.message : "로그인에 실패했습니다.";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="card">
    <div class="badge-admin">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
      ADMIN
    </div>
    <h2>관리자 로그인</h2>
    <p class="sub">관리자 계정으로 로그인합니다.</p>

    <label>관리자 ID</label>
    <div class="field">
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#9c99ab" stroke-width="2">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
      </svg>
      <input v-model="adminId" placeholder="admin" @keyup.enter="doAdminLogin" />
    </div>

    <label>Password</label>
    <div class="field">
      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#9c99ab" stroke-width="2">
        <rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </svg>
      <input v-model="adminPw" type="password" placeholder="••••••••" @keyup.enter="doAdminLogin" />
    </div>

    <div v-if="error" class="err">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10" /><path d="M12 8v4M12 16h.01" />
      </svg>
      {{ error }}
    </div>

    <button class="gx-btn submit" :disabled="loading" @click="doAdminLogin">
      {{ loading ? "로그인 중..." : "로그인" }}
    </button>

    <div class="foot">
      <NuxtLink to="/login" class="link">← 사용자 로그인으로</NuxtLink>
    </div>
  </div>
</template>

<style scoped lang="scss">
.card {
  width: 440px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 22px;
  padding: 46px 44px;
  box-shadow: 0 40px 80px -34px rgba(50, 25, 70, 0.4);
  animation: gxpop 0.35s ease;
}
.badge-admin {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 11px;
  border-radius: 999px;
  background: var(--tx);
  color: var(--panel);
  font-size: 11px;
  font-weight: 700;
  margin-bottom: 20px;
}
h2 {
  font-size: 25px;
  font-weight: 800;
  letter-spacing: -0.02em;
  margin: 0 0 8px;
}
.sub {
  font-size: 14px;
  line-height: 1.6;
  color: var(--tx2);
  margin: 0 0 28px;
}
label {
  display: block;
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 8px;
}
.field {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 50px;
  padding: 0 15px;
  border-radius: 12px;
  background: var(--field);
  border: 1px solid var(--fieldline);
  margin-bottom: 16px;
  input {
    border: none;
    outline: none;
    background: transparent;
    font-size: 14px;
    color: var(--tx);
    flex: 1;
    width: 100%;
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
  margin-top: 20px;
  text-align: center;
}
.link {
  font-size: 12.5px;
  color: var(--tx3);
  cursor: pointer;
  text-decoration: none;
}
</style>
