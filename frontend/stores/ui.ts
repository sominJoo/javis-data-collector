import { defineStore } from "pinia";

export type ToastKind = "ok" | "err";

export interface ConfirmOptions {
  title: string;
  message: string;
  okText?: string;
  danger?: boolean; // true(기본): 위험 액션(빨강 확인 버튼), false: 기본 액션(그라디언트)
}

// Promise resolver / 타이머는 반응형 상태 밖에서 관리한다.
let confirmResolver: ((ok: boolean) => void) | null = null;
let toastTimer: ReturnType<typeof setTimeout> | undefined;

// 전역 토스트/컨펌 상태. 프로토타입의 toast()/confirm 패턴을 대체한다.
export const useUiStore = defineStore("ui", {
  state: () => ({
    toast: null as { msg: string; kind: ToastKind } | null,
    confirmOptions: null as ConfirmOptions | null,
  }),
  actions: {
    showToast(msg: string, kind: ToastKind = "ok") {
      this.toast = { msg, kind };
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => {
        this.toast = null;
      }, 2600);
    },
    // 확인 다이얼로그를 띄우고, 사용자의 선택(확인/취소)을 Promise<boolean>으로 반환한다.
    confirm(options: ConfirmOptions): Promise<boolean> {
      // 이전 컨펌이 열려 있다면 취소 처리
      confirmResolver?.(false);
      this.confirmOptions = { danger: true, okText: "확인", ...options };
      return new Promise<boolean>((resolve) => {
        confirmResolver = resolve;
      });
    },
    resolveConfirm(ok: boolean) {
      this.confirmOptions = null;
      confirmResolver?.(ok);
      confirmResolver = null;
    },
  },
});
