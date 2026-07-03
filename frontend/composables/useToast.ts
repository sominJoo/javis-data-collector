import type { ToastKind } from "~/stores/ui";

// 전역 토스트 헬퍼: useToast()("저장되었습니다.")
export function useToast() {
  const ui = useUiStore();
  return (msg: string, kind: ToastKind = "ok") => ui.showToast(msg, kind);
}
