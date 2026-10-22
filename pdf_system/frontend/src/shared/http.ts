/** 统一请求封装（负责人：甲）。所有业务模块共用，禁止各自封装 fetch。 */
const TOKEN_KEY = "pdf_system_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY) ?? "",
  set: (value: string) => localStorage.setItem(TOKEN_KEY, value),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function parse(response: Response): Promise<string> {
  return (await response.text()) || `${response.status}`;
}

/** JSON 请求；401 时抛错由 AuthProvider 统一跳登录。 */
export async function api<T>(path: string, init: RequestInit = {}, token = tokenStore.get()): Promise<T> {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const isForm = init.body instanceof FormData;
  if (init.body && !isForm) headers.set("Content-Type", "application/json");
  const response = await fetch(`/api/v1${path}`, { ...init, headers });
  if (!response.ok) throw new ApiError(response.status, await parse(response));
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

/** 二进制下载（导出、原文件），不能用裸 <a href>——带不上 JWT。 */
export async function apiBlob(path: string, token = tokenStore.get()): Promise<Blob> {
  const response = await fetch(`/api/v1${path}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new ApiError(response.status, await parse(response));
  return response.blob();
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
