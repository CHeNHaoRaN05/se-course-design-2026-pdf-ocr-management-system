import { throwIfAborted, isCancellation } from "./requests";
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
    public body?: unknown,
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
    const validation: Record<string, string> = {
      literal_error: "请选择允许的选项",
      string_too_long: "输入长度超过限制",
      string_too_short: "输入长度不足",
      missing: "缺少必填项",
      int_parsing: "请输入整数",
      greater_than_equal: "数值低于允许下限",
      less_than_equal: "数值超过允许上限",
      extra_forbidden: "包含不支持的参数",
      datetime_from_date_parsing: "日期时间格式不正确",
    };
    if (typeof item.type === "string" && validation[item.type])
      return validation[item.type];
    return detailMessage(
      item.message ?? item.msg ?? item.detail ?? item.code,
      depth + 1,
    );
  }
  return "";
}
function errorMessage(status: number, body: unknown): string {
  const fallback: Record<number, string> = {
    401: "登录已过期，请重新登录。",
    403: "当前账号没有此操作权限。",
    404: "资源不存在或无权访问。",
    409: "操作冲突，请刷新后重试。",
    413: "文件超过20MiB。",
    422: "输入参数或文件内容不符合要求，请检查后重试。",
    429: "请求过于频繁，请稍后重试。",
    507: "存储空间不足，请联系管理员。",
  };
  const value = body as { detail?: unknown; error?: unknown } | null;
  return (
    detailMessage(value?.detail) ||
    detailMessage(value?.error) ||
    fallback[status] ||
    `服务暂时不可用（${status}），请稍后重试。`
  );
}
function transportError(error: unknown, signal?: AbortSignal | null): never {
  throwIfAborted(signal);
  if (isCancellation(error)) throw error;
  throw new ApiError(0, "连接中断，可能是网络、代理或服务连接异常，请重试。");
}
async function readBody<T>(
  response: Response,
  read: () => Promise<T>,
  signal?: AbortSignal | null,
): Promise<T> {
  try {
    const value = await read();
    throwIfAborted(signal);
    return value;
  } catch (error) {
    throwIfAborted(signal);
    if (isCancellation(error)) throw error;
    if (error instanceof SyntaxError)
      throw new ApiError(502, "服务响应格式异常，请稍后重试。");
    return transportError(error, signal);
  }
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
    return transportError(error, init.signal);
  }
  throwIfAborted(init.signal);
  if (!response.ok) {
    const text = await readBody(response, () => response.text(), init.signal);
    let body: unknown;
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
    throwIfAborted(init.signal);
    // 过时请求的 401 不能清除刚轮换的新令牌；匿名分享/登录不影响当前会话。
    if (
      response.status === 401 &&
      token &&
      token === tokenStore.get() &&
      !["/auth/login", "/auth/register"].includes(path)
    ) {
      tokenStore.clear();
    }
    throw new ApiError(
      response.status,
      errorMessage(response.status, body),
      body,
    );
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
  return readBody(response, () => response.json() as Promise<T>, init.signal);
}
export async function apiBlob(
  path: string,
  token = tokenStore.get(),
  signal?: AbortSignal,
): Promise<Blob> {
  const response = await request(path, { signal }, token);
  return readBody(response, () => response.blob(), signal);
}

/** 分享接口按权限返回 JSON 元数据或文件流，统一从此处读取。 */
export async function publicFile(
  path: string,
  signal?: AbortSignal,
): Promise<{ blob: Blob; filename: string }> {
  const response = await request(path, { signal }, "");
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
    blob: await readBody(response, () => response.blob(), signal),
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
