import { createServer } from "vite";
const port = Number(process.env.SE_TEST_PORT || 5174);
const server = await createServer({
  server: { host: "127.0.0.1", port, strictPort: true },
});
await server.listen();
for (const signal of ["SIGINT", "SIGTERM"])
  process.on(signal, async () => {
    await server.close();
    process.exit(0);
  });
