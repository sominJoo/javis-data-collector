// 상단바 breadcrumb 텍스트를 페이지에서 설정하기 위한 공유 상태.
export function useCrumb() {
  return useState<string>("crumb", () => "");
}
