import { createServer } from "vite";
const port = Number(process.env.SE_TEST_PORT || 5174);
const server = await createServer({
  plugins: process.env.SE_CONTRACT_TEST
    ? [
        {
          name: "reject-unmocked-api",
          configureServer(server) {
            server.middlewares.use((req, res, next) => {
              if (req.url?.startsWith("/api/")) {
                res.statusCode = 599;
                res.end("Unmocked API request in contract test");
              } else next();
            });
          },
        },
      ]
    : [],
  server: { host: "127.0.0.1", port, strictPort: true },
});
await server.listen();
for (const signal of ["SIGINT", "SIGTERM"])
  process.on(signal, async () => {
    await server.close();
    process.exit(0);
  });
