/** Abort-aware retry for explicitly idempotent operations only. */
export function throwIfAborted(signal?: AbortSignal | null): void {
  if (signal?.aborted)
    throw signal.reason ?? new DOMException("请求已取消", "AbortError");
}
export function isCancellation(error: unknown): boolean {
  return (
    error instanceof Error &&
    ["AbortError", "TimeoutError"].includes(error.name)
  );
}
export function delay(ms: number, signal?: AbortSignal): Promise<void> {
  throwIfAborted(signal);
  return new Promise((resolve, reject) => {
    const abort = () => {
      clearTimeout(timer);
      reject(signal?.reason ?? new DOMException("请求已取消", "AbortError"));
    };
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", abort);
      resolve();
    }, ms);
    signal?.addEventListener("abort", abort, { once: true });
  });
}
