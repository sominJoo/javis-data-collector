import type { ConfirmOptions } from "~/stores/ui";

// 전역 확인 다이얼로그 헬퍼: if (!(await useConfirm()({ ... }))) return;
export function useConfirm() {
  const ui = useUiStore();
  return (options: ConfirmOptions) => ui.confirm(options);
}
