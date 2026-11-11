/** 全站唯一 HTTP 出口，保持 reader / OCR 已有调用签名。 */
export const TOKEN_KEY = "pdf_system_token";
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
  invalid_storage_key: "文件存储位置异常，请联系管理员。",
  pdf_page_limit: "PDF 页数应为 1–100 页，请先拆分文件。",
  invalid_or_encrypted_pdf: "PDF 已损坏或加密，请检查文件并解除密码保护。",
  only_pdf_png_jpeg_supported: "仅支持 PDF、PNG 和 JPEG 文件。",
  image_pixel_limit: "图片超过 2000 万像素，请降低分辨率。",
  invalid_image: "图片内容无效或已损坏，请检查原文件。",
  upload_size_limit: "文件超过 20 MiB，请压缩或拆分后上传。",
  render_pixel_limit: "页面渲染超过像素限制，请降低分辨率。",
  expires_at_must_be_future: "分享有效期必须晚于当前服务器时间。",
};
export function detailMessage(value: unknown, depth = 0): string {
  if (depth > 4) return "";
  if (typeof value === "string") return messages[value.trim()] ?? value.trim();
  if (Array.isArray(value))
    return value
      .map((item) => detailMessage(item, depth + 1))
      .filter(Boolean)
      .join("；");
  if (value && typeof value === "object") {
    const item = value as Record<string, unknown>;
    return detailMessage(
      item.message ?? item.msg ?? item.detail ?? item.code,
      depth + 1,
    );
  }
  return "";
}
async function errorMessage(response: Response): Promise<string> {
  const fallback: Record<number, string> = {
    401: "登录已过期，请重新登录。",
    403: "当前账号没有此操作权限。",
    404: "资源不存在或无权访问。",
    409: "操作冲突，请刷新后重试。",
    413: "文件超过 20 MiB。",
    422: "输入参数或文件内容不符合要求，请检查后重试。",
    429: "操作过于频繁或配额不足，请稍后再试。",
    507: "存储空间不足，请联系管理员。",
  };
  try {
    const body = await response.json();
    const message = detailMessage(body?.detail) || detailMessage(body?.error);
    if (message) return message;
  } catch {
    /* 代理 HTML 不作为业务错误 */
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
  if (init.signal?.aborted) throw new DOMException("请求已取消", "AbortError");
  if (!response.ok) {
    // 过时请求的 401 不能清除刚轮换的新令牌；匿名分享/登录不影响当前会话。
    if (
      response.status === 401 &&
      token &&
      token === tokenStore.get() &&
      !["/auth/login", "/auth/register"].includes(path)
    ) {
      tokenStore.clear();
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
