const PUBLIC_ROUTES = ["/login", "/admin-login"];

// 클라이언트 시작 시 테마/세션 복원 + 최초 진입 인증 가드.
// (전역 미들웨어는 클라이언트 내비게이션을 담당하고, 여기서는 하드 새로고침 최초 진입을 담당)
export default defineNuxtPlugin(async () => {
  const theme = useThemeStore();
  const auth = useAuthStore();
  theme.init();
  auth.init();

  const route = useRoute();
  const isPublic = PUBLIC_ROUTES.includes(route.path);
  if (!auth.isAuthenticated && !isPublic) {
    await navigateTo("/login");
  } else if (auth.isAuthenticated && isPublic) {
    await navigateTo("/");
  }
});
