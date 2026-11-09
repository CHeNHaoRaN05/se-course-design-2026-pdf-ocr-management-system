/** 全站唯一 HTTP 出口，保持 reader / OCR 已有调用签名。 */
export const TOKEN_KEY = "pdf_system_token";
export const AUTH_EXPIRED = "pdf-system:auth-expired";
export const TOKEN_CHANGED = "pdf-system:token-changed";
let memoryToken = "";
let memoryOnly = false;
export const tokenStore = {
  get: () => {
    if (memoryOnly) return memoryToken;
    try {
      return localStorage.getItem(TOKEN_KEY) ?? "";
    } catch {
      return memoryToken;
    }
  },
  set: (value: string) => {
    memoryToken = value;
    try {
      localStorage.setItem(TOKEN_KEY, value);
      memoryOnly = false;
    } catch {
      memoryOnly = true;
    }
    window.dispatchEvent(new Event(TOKEN_CHANGED));
  },
  clear: () => {
    memoryToken = "";
    try {
      localStorage.removeItem(TOKEN_KEY);
      memoryOnly = false;
    } catch {
      memoryOnly = true;
    }
    window.dispatchEvent(new Event(TOKEN_CHANGED));
  },
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const messages: Record<string, string> = {
  upload_too_large: "文件超过 20 MiB，请压缩后重试。",
  too_many_pages: "PDF 超过 100 页，请先拆分。",
  pdf_encrypted: "PDF 已加密，请解除密码保护后上传。",
  invalid_pdf: "PDF 已损坏或无法解析，请检查原文件。",
  unsupported_media_type: "仅支持 PDF、PNG 和 JPEG 文件。",
  invalid_credentials: "邮箱或密码不正确，请重试。",
};
async function errorMessage(response: Response): Promise<string> {
  const fallback: Record<number, string> = {
    401: "登录已过期，请重新登录。",
    403: "当前账号没有此操作权限。",
    404: "资源不存在或无权访问。",
    409: "操作冲突，请刷新后重试。",
    413: "文件超过 20 MiB。",
    429: "操作过于频繁或配额不足，请稍后再试。",
    507: "存储空间不足，请联系管理员。",
  };
  try {
    const text = await response.text();
    const body = JSON.parse(text) as {
      detail?: unknown;
      error?: { message?: string; code?: string };
    };
    const detail = body.detail ?? body.error?.message ?? body.error?.code;
    if (typeof detail === "string") return messages[detail] ?? detail;
    if (Array.isArray(detail))
      return detail
        .map((item: { msg?: string }) => item.msg ?? "输入不符合要求")
        .join("；");
  } catch {
    /* 不把代理 HTML 或服务堆栈展示给用户 */
  }
  return (
    fallback[response.status] ??
    `服务暂时不可用（${response.status}），请稍后重试。`
  );
}

async function request(
  path: string,
  init: RequestInit = {},
  token = tokenStore.get(),
): Promise<Response> {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, { ...init, headers });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;
    throw new ApiError(0, "无法连接服务，请检查网络和后端服务后重试。");
  }
  if (!response.ok) {
    // 过时请求的 401 不能清除刚轮换的新令牌；匿名分享/登录不影响当前会话。
    if (
      response.status === 401 &&
      token &&
      token === tokenStore.get() &&
      !["/auth/login", "/auth/register"].includes(path)
    ) {
      tokenStore.clear();
      window.dispatchEvent(new Event(AUTH_EXPIRED));
    }
    throw new ApiError(response.status, await errorMessage(response));
  }
  return response;
}
export async function api<T>(
  path: string,
  init: RequestInit = {},
  token = tokenStore.get(),
): Promise<T> {
  const response = await request(path, init, token);
  if (response.status === 204) return undefined as T;
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError(502, "服务响应格式异常，请稍后重试。");
  }
}
export async function apiBlob(
  path: string,
  token = tokenStore.get(),
): Promise<Blob> {
  return (await request(path, {}, token)).blob();
}
/** 分享接口按权限返回 JSON 元数据或文件流，统一从此处读取。 */
export async function publicFile(
  path: string,
): Promise<{ blob: Blob; filename: string }> {
  const response = await request(path, {}, "");
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  const raw = disposition.match(/filename="?([^";]+)"?/i)?.[1];
  let filename = raw ?? "共享文档.pdf";
  if (encoded) {
    try {
      filename = decodeURIComponent(encoded);
    } catch {
      /* 使用缺省名称 */
    }
  }
  return {
    blob: await response.blob(),
    filename: filename.replace(/[\\/]/g, "_"),
  };
}
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
