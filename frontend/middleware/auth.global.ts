const PUBLIC_ROUTES = ["/login", "/admin-login"];

// 미인증 접근은 로그인으로, 인증된 사용자의 로그인 페이지 접근은 홈으로 리다이렉트.
export default defineNuxtRouteMiddleware((to) => {
  // 세션은 localStorage 기반이므로 클라이언트에서만 판정한다.
  if (import.meta.server) return;

  const auth = useAuthStore();
  const isPublic = PUBLIC_ROUTES.includes(to.path);

  if (!auth.isAuthenticated && !isPublic) {
    return navigateTo("/login");
  }
  if (auth.isAuthenticated && isPublic) {
    return navigateTo("/");
  }
});
