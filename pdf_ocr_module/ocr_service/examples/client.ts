// Minimal React/browser integration. token comes from the host login module.
const base = "/api/v1/ocr";
export async function ocrRequest<T>(path: string, token: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(base + path, { ...init, headers });
  if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
  return response.json();
}

export async function uploadAndRecognize(file: File, token: string) {
  const body = new FormData(); body.set("file", file);
  const uploaded = await ocrRequest<{id: string}>("/files", token, {method: "POST", body});
  return ocrRequest<{id: string; status: string}>("/jobs", token, {
    method: "POST", body: JSON.stringify({file_id: uploaded.id, mode: "general", tables: true})
  });
}

export async function waitForJob(id: string, token: string, signal: AbortSignal) {
  const terminal = new Set(["succeeded", "partial_success", "failed", "cancelled"]);
  while (!signal.aborted) {
    const job = await ocrRequest<{status: string}>(`/jobs/${id}`, token, {signal});
    if (terminal.has(job.status)) return job;
    await new Promise<void>((resolve, reject) => {
      const onAbort = () => { clearTimeout(timer); reject(new DOMException("Aborted", "AbortError")); };
      const timer = setTimeout(() => { signal.removeEventListener("abort", onAbort); resolve(); }, 1500);
      signal.addEventListener("abort", onAbort, {once: true});
    });
  }
  throw new DOMException("Aborted", "AbortError");
}

// pdf.js page display at its intrinsic rotation: normalized coordinates scale with viewport.
// If the reader applies an EXTRA 90/180/270 degree user rotation, rotate all four corners first.
export function overlayStyle(bbox: number[], width: number, height: number) {
  const [left, top, right, bottom] = bbox;
  return {position: "absolute" as const, left: left * width, top: top * height,
          width: (right - left) * width, height: (bottom - top) * height};
}

export async function downloadExport(jobId: string, token: string, format = "xlsx") {
  const response = await fetch(`${base}/jobs/${jobId}/export?format=${encodeURIComponent(format)}`, {
    headers: {Authorization: `Bearer ${token}`}
  });
  if (!response.ok) throw new Error(await response.text());
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = `ocr-${jobId}.${format}`; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
