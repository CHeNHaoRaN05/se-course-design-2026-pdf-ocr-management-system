import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../../shared/http";
import { errorText } from "./management";

export function useResource<T>(
  loader: (signal: AbortSignal) => Promise<T>,
  dependencies: unknown[] = [],
) {
  const load = useRef(loader);
  load.current = loader;
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState(0);
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  const reload = useCallback(() => setRevision((n) => n + 1), []);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setStatus(0);
    setData(null);
    void load
      .current(controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setData(value);
      })
      .catch((e) => {
        if (!controller.signal.aborted) {
          setError(errorText(e));
          setStatus(e instanceof ApiError ? e.status : 0);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
    // dependencies is explicitly supplied by the calling page; stale requests are aborted.
  }, [...dependencies, revision]);
  return { data, error, status, loading, reload };
}
