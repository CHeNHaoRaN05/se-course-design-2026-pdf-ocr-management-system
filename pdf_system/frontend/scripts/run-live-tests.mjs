/** Cross-platform owner of two isolated servers. Never reuses a stale listener. */
import { spawn } from "node:child_process";
import { createServer } from "node:net";
import { randomUUID } from "node:crypto";
const freePort = () =>
  new Promise((resolve, reject) => {
    const server = createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
  });
const apiPort = await freePort();
const webPort = await freePort();
const marker = randomUUID();
const env = {
  ...process.env,
  SE_SMOKE_PORT: String(apiPort),
  SE_SMOKE_MARKER: marker,
  SE_TEST_PORT: String(webPort),
  SE_API_TARGET: `http://127.0.0.1:${apiPort}`,
  SE_FRONTEND_ORIGIN: `http://127.0.0.1:${webPort}`,
};
const children = [];
const launch = (command, args) => {
  const child = spawn(command, args, { stdio: "inherit", shell: false, env });
  child.on("error", (e) => {
    console.error(e);
  });
  children.push(child);
  return child;
};
async function ready(url, child, check = () => true) {
  const deadline = Date.now() + 45000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null || child.signalCode)
      throw Error(`Server exited before ready: ${url}`);
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(1000) });
      if (response.ok && (await check(response))) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw Error(`Server readiness timeout: ${url}`);
}
try {
  const api = launch(process.env.SE_PYTHON || "python", [
    "scripts/start-smoke-api.py",
  ]);
  await ready(
    `http://127.0.0.1:${apiPort}/__smoke_ready`,
    api,
    async (r) => (await r.json()).marker === marker,
  );
  const vite = launch(process.execPath, ["scripts/start-test-vite.mjs"]);
  await ready(`http://127.0.0.1:${webPort}`, vite);
  const test = launch(process.execPath, ["scripts/live-smoke.mjs"]);
  process.exitCode = await new Promise((resolve) => {
    test.on("exit", (code) => resolve(code ?? 1));
    test.on("error", () => resolve(1));
  });
} catch (error) {
  console.error(error);
  process.exitCode = 1;
} finally {
  for (const child of children)
    if (child.exitCode === null && !child.killed) child.kill("SIGTERM");
  await Promise.all(
    children.map((child) =>
      child.exitCode !== null
        ? Promise.resolve()
        : new Promise((resolve) => {
            child.once("exit", resolve);
            const timer = setTimeout(() => {
              if (child.exitCode === null) child.kill("SIGKILL");
              resolve();
            }, 5000);
            timer.unref();
          }),
    ),
  );
}
