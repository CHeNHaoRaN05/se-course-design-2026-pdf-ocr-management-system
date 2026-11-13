const EVENT = "pdf-system:files-changed";
let channel: BroadcastChannel | undefined;
if (typeof window !== "undefined" && typeof BroadcastChannel !== "undefined") {
  channel = new BroadcastChannel("pdf-files");
  channel.onmessage = () => window.dispatchEvent(new Event(EVENT));
}
export function filesChanged() {
  window.dispatchEvent(new Event(EVENT));
  channel?.postMessage("changed");
}
export function onFilesChanged(listener: () => void) {
  window.addEventListener(EVENT, listener);
  return () => window.removeEventListener(EVENT, listener);
}
