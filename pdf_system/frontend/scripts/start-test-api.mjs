import { spawn } from "node:child_process";
const child = spawn(
  process.env.SE_PYTHON || "python",
  ["scripts/start-smoke-api.py"],
  {
    stdio: "inherit",
    shell: false,
    env: {
      ...process.env,
      SE_SMOKE_PORT: "8015",
      SE_SMOKE_MARKER: "playwright-live",
    },
  },
);
child.on("error", (error) => {
  console.error(error);
  process.exitCode = 1;
});
child.on("exit", (code) => process.exit(code ?? 1));
for (const signal of ["SIGTERM", "SIGINT"])
  process.on(signal, () => child.kill(signal));
