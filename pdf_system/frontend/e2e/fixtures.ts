/** Browser contract fixtures only. No mock transport or sample data is included in the application. */
import { expect, type Page } from "@playwright/test";
import { PDFDocument } from "pdf-lib";
import type { FileItem } from "../src/shared/types";
import type { Role, ShareItem } from "../src/features/management/management";

const unexpected = new WeakMap<Page, string[]>();
export function assertNoUnexpectedApi(page: Page) {
  expect(
    unexpected.get(page) ?? [],
    "contract test issued an unmocked request",
  ).toEqual([]);
}
export const userId = "a".repeat(32);
export const otherUserId = "b".repeat(32);
const names = [
  "软件工程课程设计需求分析.pdf",
  "数据库系统原理 · 第三章.pdf",
  "项目验收报告.pdf",
  "用户访谈记录.pdf",
  "系统架构设计说明.pdf",
  "接口规范与对接文档.pdf",
  "2026年技术调研报告.pdf",
  "设备使用手册.pdf",
  "实验数据汇总.pdf",
  "产品设计规范.pdf",
  "文献阅读笔记.pdf",
  "数据结构课程讲义.pdf",
  "操作系统复习资料.pdf",
  "工程实践周报.pdf",
  "会议记录.pdf",
];
export async function mockApi(
  page: Page,
  options: {
    role?: Role;
    loggedIn?: boolean;
    extensions?: boolean;
    mounted?: boolean;
  } = {},
) {
  const errors: string[] = [];
  unexpected.set(page, errors);
  page.on("response", (response) => {
    if (response.status() === 599) errors.push(response.url());
  });
  const role = options.role ?? "user";
  let mounted = options.mounted ?? true;
  const files: FileItem[] = names.map((name, i) => ({
    id: (i + 1).toString(16).padStart(32, "0"),
    name,
    folder:
      i % 3 === 0
        ? "/课程资料/软件工程"
        : i % 3 === 1
          ? "/参考文献"
          : "/项目文档",
    media_type: "application/pdf",
    size: 400000 + i * 135217,
    page_count: 2,
    version: 1,
    tags: i % 2 ? ["参考资料"] : ["课程设计", "已归档"],
    created_at: `2026-11-${String(9 - (i % 6)).padStart(2, "0")}T08:30:00`,
  }));
  const trash: (FileItem & { deleted_at: string })[] = [];
  const shares: ShareItem[] = [];
  const requests: {
    path: string;
    method: string;
    auth?: string;
    body: unknown;
  }[] = [];
  const user = {
    id: userId,
    email: "student@example.com",
    display_name: "学习工作空间",
    role,
    disabled: false,
    created_at: "2026-10-01T00:00:00",
  };
  const people = [
    user,
    {
      id: otherUserId,
      email: "reader@example.com",
      display_name: "协作成员",
      role: "user" as Role,
      disabled: false,
      created_at: "2026-10-05T00:00:00",
    },
  ];
  let expired = false;
  let sequence = 100;
  let failUpdate = false;
  const doc = await PDFDocument.create();
  doc.addPage([595, 842]);
  doc.addPage([595, 842]);
  const pdf = Buffer.from(await doc.save());
  if (options.loggedIn !== false)
    await page.addInitScript(() => {
      if (!sessionStorage.getItem("fixture-auth-initialized")) {
        localStorage.setItem("pdf_system_token", "fixture-token");
        sessionStorage.setItem("fixture-auth-initialized", "1");
      }
    });
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace("/api/v1", "");
    const method = request.method();
    let body: any = null;
    try {
      body = request.postDataJSON();
    } catch {
      /* multipart */
    }
    requests.push({
      path,
      method,
      auth: request.headers().authorization,
      body,
    });
    const paged = (items: any[]) => {
      const offset = Number(url.searchParams.get("offset") || 0);
      const limit = Number(url.searchParams.get("limit") || 20);
      return json(
        url.searchParams.get("envelope") === "true"
          ? {
              items: items.slice(offset, offset + limit),
              total: items.length,
              limit,
              offset,
            }
          : items,
      );
    };
    const json = (data: unknown, status = 200) =>
      route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(data),
      });
    const empty = () => route.fulfill({ status: 204 });
    const notFound = () => json({ detail: "资源不存在或无权访问" }, 404);
    if (
      expired &&
      !path.startsWith("/auth/login") &&
      !path.startsWith("/share/token/")
    )
      return json({ detail: "登录已过期" }, 401);
    if (path === "/auth/login" || path === "/auth/register")
      return json({ access_token: "fixture-token", expires_in: 7200, role });
    if (path === "/auth/me") return json(user);
    if (path === "/auth/refresh" || path === "/auth/change-password")
      return json({
        access_token: "fixture-refreshed",
        expires_in: 7200,
        role,
      });
    if (path === "/auth/logout") return empty();
    if (path === "/auth/users")
      return role === "admin"
        ? paged(people)
        : json({ detail: "需要管理员角色" }, 403);
    const userMatch = path.match(/^\/auth\/users\/([^/]+)\/(role|disabled)$/);
    if (userMatch) {
      const target = people.find((person) => person.id === userMatch[1]);
      if (!target) return notFound();
      Object.assign(target, body);
      return json(target);
    }
    if (path === "/quota/overview")
      return json({
        files: files.length,
        storage_bytes: files.reduce((n, f) => n + f.size, 0),
        quota: {
          month: "2026-11",
          pages_used: 156,
          pages_reserved: 24,
          pages_committed: 180,
        },
      });
    if (path === "/ocr-host/capabilities")
      return json({ mounted, quota_per_month: 500 });
    if (path === "/ocr-host/usage")
      return json({
        ocr: {
          jobs_by_status: {
            succeeded: 28,
            running: 2,
            failed: 1,
            partial_success: 3,
          },
          recognized_page_results: 320,
        },
      });
    if (path === "/ocr/jobs")
      return json(
        files.slice(0, 10).map((file, i) => ({
          file_id: file.id,
          status: [
            "succeeded",
            "succeeded",
            "running",
            "partial_success",
            "none",
          ][i % 5],
        })),
      );
    if (path.match(/^\/ocr-host\/files\/.+\/jobs$/))
      return json({ job_id: null, status: null });
    if (path === "/files/trash") return paged(trash);
    if (path === "/files/folders")
      return json([...new Set(files.map((f) => f.folder))]);
    if (path === "/files/tags")
      return json([...new Set(files.flatMap((f) => f.tags))]);
    if (path === "/files/query") {
      const keyword = url.searchParams.get("q") ?? "";
      const state = (f: FileItem) =>
        ["succeeded", "succeeded", "running", "partial_success", "none"][
          files.indexOf(f) % 5
        ];
      let matching = files.filter(
        (f) =>
          f.name.includes(keyword) &&
          (!url.searchParams.get("media_type") ||
            f.media_type === url.searchParams.get("media_type")) &&
          (!url.searchParams.get("folder") ||
            f.folder.startsWith(url.searchParams.get("folder")!)) &&
          (!url.searchParams.get("tag") ||
            f.tags.includes(url.searchParams.get("tag")!)) &&
          (!mounted ||
            !url.searchParams.get("status") ||
            state(f) === url.searchParams.get("status")),
      );
      matching.sort(
        (a, b) =>
          b.created_at.localeCompare(a.created_at) || a.id.localeCompare(b.id),
      );
      const offset = Number(url.searchParams.get("offset"));
      const limit = Number(url.searchParams.get("limit") || 20);
      return json({
        items: matching.slice(offset, offset + limit).map((f) => ({
          ...f,
          status: mounted ? state(f) : "unknown",
          generation: mounted ? 1 : null,
        })),
        total: matching.length,
        status_available: mounted,
        effective_sort: mounted ? url.searchParams.get("sort") : "newest",
      });
    }
    if (path === "/files/bulk") {
      const items = body.file_ids.map((id: string) => {
        const f = files.find((f) => f.id === id)!;
        if (failUpdate) {
          failUpdate = false;
          return { id, name: f.name, ok: false, message: "测试：分类保存失败" };
        }
        if (body.action === "delete") {
          files.splice(files.indexOf(f), 1);
          trash.push({ ...f, deleted_at: new Date().toISOString() });
        }
        if (body.action === "move") f.folder = body.folder;
        if (body.action === "tag")
          f.tags = body.append_tags
            ? [...new Set([...f.tags, ...body.tags])]
            : body.tags;
        return { id, name: f.name, ok: true };
      });
      return json({ items });
    }
    if (path === "/files/merge" || path.endsWith("/split")) {
      const created = (
        path.endsWith("/merge")
          ? [body.name]
          : body.groups.map(
              (_: unknown, i: number) => `${body.name}-${i + 1}.pdf`,
            )
      ).map((name: string) => ({
        ...files[0],
        name,
        id: (++sequence).toString(16).padStart(32, "0"),
        created_at: new Date().toISOString(),
      }));
      files.unshift(...created);
      return json(path.endsWith("/merge") ? created[0] : created, 201);
    }
    if (path === "/files" && method === "GET") {
      const offset = Number(url.searchParams.get("offset") ?? 0);
      const limit = Number(url.searchParams.get("limit") ?? 20);
      return json(files.slice(offset, offset + limit));
    }
    if (path === "/files" && method === "POST") {
      const text = request.postDataBuffer()?.toString() ?? "";
      const name = text.match(/filename="([^"]+)"/)?.[1] ?? "上传文档.pdf";
      const file = {
        ...files[0],
        id: (++sequence).toString(16).padStart(32, "0"),
        name,
        created_at: new Date().toISOString(),
      };
      files.unshift(file);
      return json(file, 201);
    }
    const fileMatch = path.match(
      /^\/files\/([^/]+)(?:\/(content|restore|purge))?$/,
    );
    if (fileMatch) {
      const id = fileMatch[1];
      const file = files.find((f) => f.id === id);
      if (fileMatch[2] === "restore") {
        const index = trash.findIndex((f) => f.id === id);
        if (index < 0) return notFound();
        const restored = trash.splice(index, 1)[0];
        files.push(restored);
        return json(restored);
      }
      if (fileMatch[2] === "purge") {
        const index = trash.findIndex((f) => f.id === id);
        if (index < 0) return notFound();
        trash.splice(index, 1);
        return empty();
      }
      if (!file) return notFound();
      if (fileMatch[2] === "content")
        return route.fulfill({ contentType: "application/pdf", body: pdf });
      if (method === "DELETE") {
        files.splice(files.indexOf(file), 1);
        trash.push({ ...file, deleted_at: new Date().toISOString() });
        return json(file);
      }
      if (method === "PATCH") {
        if (failUpdate) {
          failUpdate = false;
          return json({ detail: "测试：分类保存失败" }, 500);
        }
        Object.assign(file, body);
      }
      return json(file);
    }
    if (path === "/share" && method === "GET") return json(shares);
    if (path === "/share" && method === "POST") {
      const share = {
        id: String(++sequence),
        token: "t".repeat(63) + sequence,
        share_url: "",
        expired: false,
        expires_at: new Date(
          Date.now() + body.expires_in_days * 86400000,
        ).toISOString(),
        visit_count: 0,
        created_at: new Date().toISOString(),
        ...body,
      };
      shares.push(share);
      return json(share, 201);
    }
    if (path.startsWith("/share/token/")) {
      const share = shares.find((item) => path.endsWith(item.token));
      if (
        !share ||
        (share.access_code &&
          share.access_code !== url.searchParams.get("code"))
      )
        return notFound();
      share.visit_count++;
      if (share.allow_download)
        return route.fulfill({
          contentType: "application/pdf",
          body: pdf,
          headers: {
            "Content-Disposition": "inline; filename*=UTF-8''shared.pdf",
          },
        });
      return json(files.find((f) => f.id === share.file_id));
    }
    if (path.startsWith("/share/") && method === "DELETE") {
      const i = shares.findIndex((s) => path === `/share/${s.id}`);
      if (i < 0) return notFound();
      shares.splice(i, 1);
      return empty();
    }
    if (path === "/search/suggest")
      return json({
        items: files
          .slice(0, 3)
          .map((f) => ({ file_id: f.id, file_name: f.name })),
      });
    if (path === "/search")
      return json({
        backend: "substring",
        items: files.slice(0, 2).map((f, i) => ({
          file_id: f.id,
          file_name: f.name,
          page_no: i + 1,
          job_id: "c".repeat(32),
          revision: 2,
          snippet: `软件工程项目的验收报告记录了功能验证结果。${url.searchParams.get("q")} <script>alert(1)</script>`,
        })),
      });
    if (path === "/audit")
      return options.extensions
        ? paged([
            {
              id: "1",
              actor_id: userId,
              action: "file_uploaded",
              resource_id: files[0].id,
              created_at: "2026-11-09T08:30:00",
              detail: {},
            },
          ])
        : notFound();
    errors.push(`${method} ${path}`);
    return json({ detail: "Unexpected API in contract test" }, 599);
  });
  return {
    files,
    trash,
    shares,
    requests,
    pdf,
    user,
    setMounted: (value: boolean) => {
      mounted = value;
    },
    expire: () => {
      expired = true;
    },
    failNextUpdate: () => {
      failUpdate = true;
    },
  };
}
