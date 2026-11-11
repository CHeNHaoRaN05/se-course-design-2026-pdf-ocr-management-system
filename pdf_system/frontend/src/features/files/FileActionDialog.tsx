import { useState, type FormEvent } from "react";
import type { FileItem } from "../../shared/types";
import { Icon, Modal, Notice } from "../management/ui";
import {
  errorText,
  normalizeFolder,
  parseTags,
} from "../management/management";
import { bulkFiles, mergeFiles, splitFile, updateFile } from "./filesApi";
export type FileAction =
  | "rename"
  | "move"
  | "tag"
  | "delete"
  | "merge"
  | "split";
const titles: Record<FileAction, string> = {
  rename: "重命名文档",
  move: "移动到分类",
  tag: "编辑文档标签",
  delete: "移入回收站",
  merge: "合并 PDF",
  split: "拆分 PDF",
};
interface Result {
  name: string;
  ok: boolean;
  message?: string;
}
export default function FileActionDialog({
  action,
  files,
  onClose,
  onChanged,
}: {
  action: FileAction;
  files: FileItem[];
  onClose: () => void;
  onChanged: () => void;
}) {
  const [value, setValue] = useState(
    action === "rename"
      ? files[0].name
      : action === "move"
        ? files[0].folder
        : action === "tag" && files.length === 1
          ? files[0].tags.join(", ")
          : "",
  );
  const [name, setName] = useState(
    action === "merge" ? "合并文档.pdf" : files[0].name.replace(/\.pdf$/i, ""),
  );
  const [order, setOrder] = useState(files);
  const [mode, setMode] = useState("range");
  const [every, setEvery] = useState("1");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState<Result[]>([]);
  const [done, setDone] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || done) return;
    setError("");
    setResults([]);
    setBusy(true);
    let changed = false;
    const record = (result: Result) => {
      setResults((previous) => [...previous, result]);
      if (result.ok) changed = true;
    };
    try {
      if (action === "merge" || action === "split") {
        if (order.some((file) => file.media_type !== "application/pdf"))
          throw new Error("仅支持 PDF 文件。");
        if (
          action === "merge" &&
          order.reduce((sum, file) => sum + file.page_count, 0) > 100
        )
          throw new Error("合并后的总页数不能超过 100 页。");
        if (!name.trim() || /[\\/:*?"<>|]/.test(name))
          throw new Error("请输入合法的输出文件名。");
        if (action === "merge") {
          const result = await mergeFiles(
            order.map((file) => file.id),
            name.trim(),
          );
          record({ name: result.name, ok: true });
        } else {
          const { splitGroups } = await import("./pdfTools");
          const groups = splitGroups(
            value,
            files[0].page_count,
            mode === "every" ? Number(every) : undefined,
          );
          const output = await splitFile(files[0].id, {
            name: name.trim(),
            groups: groups.map((group) => group.map((page) => page + 1)),
          });
          output.forEach((file) => record({ name: file.name, ok: true }));
        }
      } else if (action === "rename") {
        if (!value.trim() || value.trim().length > 255 || /[\\/]/.test(value))
          throw new Error("请输入合法文件名。");
        const updated = await updateFile(files[0].id, { name: value.trim() });
        record({ name: updated.name, ok: true });
      } else {
        const folder = action === "move" ? normalizeFolder(value) : undefined;
        const tags = action === "tag" ? parseTags(value) : undefined;
        const result = await bulkFiles({
          file_ids: files.map((file) => file.id),
          action,
          folder,
          tags,
          append_tags: files.length > 1,
        });
        result.items.forEach(record);
      }
      setDone(true);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
      if (changed) {
        onChanged();
        window.dispatchEvent(new Event("pdf-system:files-changed"));
      }
    }
  }
  const totalPages = order.reduce((sum, file) => sum + file.page_count, 0);
  return (
    <Modal
      title={titles[action]}
      onClose={onClose}
      busy={busy}
      wide={action === "merge"}
    >
      <form onSubmit={submit} className="form-stack">
        {error && <Notice tone="error">{error}</Notice>}
        {!done && (
          <>
            <p className="muted">
              已选择 {files.length} 份文档
              {action === "merge" && ` · 共 ${totalPages} 页`}
            </p>
            {action === "delete" ? (
              <Notice tone="warning">
                确认将所选文档移入回收站？正在进行的识别任务会由服务端取消。可以凭文档
                ID 还原，彻底删除后无法恢复。
              </Notice>
            ) : null}
            {["rename", "move", "tag"].includes(action) && (
              <label>
                {action === "rename"
                  ? "文件名称"
                  : action === "move"
                    ? "目标分类路径"
                    : files.length > 1
                      ? "批量追加标签"
                      : "标签（留空清除）"}
                <input
                  autoFocus
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  disabled={busy}
                  required={action !== "tag"}
                  maxLength={action === "tag" ? 1300 : 255}
                  placeholder={
                    action === "move"
                      ? "/课程资料/软件工程"
                      : action === "tag"
                        ? "用逗号分隔标签"
                        : "文件名称"
                  }
                />
                {action === "move" && (
                  <small>使用 / 分隔层级，根目录为 /，最多 5 级。</small>
                )}
              </label>
            )}
            {action === "merge" && (
              <>
                <Notice>
                  按下方顺序由服务端合并并保存为新文件。原文件保留，总页数最多
                  100 页。
                </Notice>
                <ol className="merge-order">
                  {order.map((file, i) => (
                    <li key={file.id}>
                      <Icon name="file" />
                      <span>
                        {file.name}
                        <small>{file.page_count} 页</small>
                      </span>
                      <button
                        type="button"
                        disabled={busy || i === 0}
                        aria-label={`上移 ${file.name}`}
                        onClick={() =>
                          setOrder((old) => {
                            const next = [...old];
                            [next[i - 1], next[i]] = [next[i], next[i - 1]];
                            return next;
                          })
                        }
                      >
                        ↑
                      </button>
                      <button
                        type="button"
                        disabled={busy || i === order.length - 1}
                        aria-label={`下移 ${file.name}`}
                        onClick={() =>
                          setOrder((old) => {
                            const next = [...old];
                            [next[i + 1], next[i]] = [next[i], next[i + 1]];
                            return next;
                          })
                        }
                      >
                        ↓
                      </button>
                    </li>
                  ))}
                </ol>
              </>
            )}
            {action === "split" && (
              <>
                <Notice>
                  服务端拆分会生成新文件，原文件保留。每个逗号分隔的页段生成一份文件，未选中的页面不会导出。
                </Notice>
                <label>
                  拆分方式
                  <select
                    disabled={busy}
                    value={mode}
                    onChange={(e) => setMode(e.target.value)}
                  >
                    <option value="range">按页段拆分</option>
                    <option value="every">每 N 页拆分</option>
                  </select>
                </label>
                {mode === "range" ? (
                  <label>
                    页段（共 {files[0].page_count} 页）
                    <input
                      required
                      disabled={busy}
                      value={value}
                      placeholder="例如 1-3,4-6"
                      onChange={(e) => setValue(e.target.value)}
                    />
                  </label>
                ) : (
                  <label>
                    每份页数
                    <input
                      type="number"
                      required
                      min={1}
                      max={files[0].page_count}
                      disabled={busy}
                      value={every}
                      onChange={(e) => setEvery(e.target.value)}
                    />
                  </label>
                )}
              </>
            )}
            {(action === "merge" || action === "split") && (
              <label>
                {action === "merge" ? "输出文件名" : "输出文件名前缀"}
                <input
                  required
                  maxLength={200}
                  disabled={busy}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </label>
            )}
          </>
        )}
        {!!results.length && (
          <div className="operation-results" aria-live="polite">
            <strong>
              成功 {results.filter((r) => r.ok).length} 项 · 失败{" "}
              {results.filter((r) => !r.ok).length} 项
            </strong>
            {results.map((result, i) => (
              <p key={i} className={result.ok ? "success-text" : "error"}>
                <Icon name={result.ok ? "check" : "info"} size={16} />
                {result.name}
                {result.message && `：${result.message}`}
              </p>
            ))}
          </div>
        )}
        <div className="modal-actions">
          <button type="button" disabled={busy} onClick={onClose}>
            {done ? "完成" : "取消"}
          </button>
          {!done && (
            <button
              className={action === "delete" ? "danger" : "primary"}
              disabled={busy}
            >
              {busy ? "正在处理…" : "确认"}
            </button>
          )}
        </div>
      </form>
    </Modal>
  );
}
