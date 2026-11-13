/** Session notifications carry no credentials. BroadcastChannel covers disabled localStorage. */
const KEY = "pdf_logout_notice_v2";
export const LOGOUT_EVENT = "pdf-system:logout";
let notice = "";
const listeners = new Set<() => void>();
let channel: BroadcastChannel | undefined;
function receive(value: unknown) {
  const message = value as {
    type?: string;
    message?: string;
    expires?: number;
    clear?: boolean;
  } | null;
  if (
    message?.type !== "logout" ||
    typeof message.message !== "string" ||
    !message.expires ||
    message.expires < Date.now()
  )
    return;
  notice = message.message;
  listeners.forEach((fn) => fn());
  if (message.clear) window.dispatchEvent(new Event(LOGOUT_EVENT));
}
if (typeof window !== "undefined") {
  try {
    receive(JSON.parse(localStorage.getItem(KEY) ?? "null"));
  } catch {}
  if (typeof BroadcastChannel !== "undefined") {
    channel = new BroadcastChannel("pdf-session");
    channel.onmessage = (event) => receive(event.data);
  }
  window.addEventListener("storage", (event) => {
    if (event.key === KEY && event.newValue) {
      try {
        receive(JSON.parse(event.newValue));
      } catch {}
    }
  });
}
export function publishLogout(message: string, clear = true) {
  const value = {
    type: "logout",
    message,
    clear,
    expires: Date.now() + 30_000,
  };
  receive(value);
  try {
    localStorage.setItem(KEY, JSON.stringify(value));
  } catch {}
  channel?.postMessage(value);
}
export function clearLogoutNotice() {
  notice = "";
  listeners.forEach((fn) => fn());
  try {
    localStorage.removeItem(KEY);
  } catch {}
}
export const subscribeLogout = (listener: () => void) => {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
};
export const logoutSnapshot = () => notice;
