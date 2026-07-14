export interface ApiResponse<T> {
  result: number;
  errorMessage: string;
  data: T | null;
}
