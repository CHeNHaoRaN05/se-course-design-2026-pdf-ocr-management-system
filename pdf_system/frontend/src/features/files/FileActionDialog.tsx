import { useState, type FormEvent } from "react";
import type { FileItem } from "../../shared/types";
import { Modal, Notice } from "../management/ui";
import { filesChanged } from "../management/fileEvents";
import { errorText, normalizeFolder, normalizeFilename, parseTags } from "../management/management";
import { deleteFile, updateFile } from "./filesApi";

const titles = {
  rename: "重命名文档",
  move: "移动到分类",
  tag: "编辑文档标签",
  delete: "移入回收站",
};
export type FileAction = keyof typeof titles;

export default function FileActionDialog({
  action, file, onClose, onChanged,
}: {
  action: FileAction;
  file: FileItem;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [value, setValue] = useState(
    { rename: file.name, move: file.folder, tag: file.tags.join(", "), delete: "" }[action],
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<FileItem | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || result) return;
    setBusy(true);
    setError("");
    try {
      if (action === "rename" && !value.trim())
        throw new Error("请输入合法文件名。");
      if (action === "move" && !value.trim())
        throw new Error("请填写目标分类，根目录请填写 /。");
      const updated = action === "delete"
        ? await deleteFile(file.id)
        : await updateFile(file.id, {
          [action === "rename" ? "name" : action === "move" ? "folder" : "tags"]:
            action === "rename" ? normalizeFilename(value)
            : action === "move" ? normalizeFolder(value) : parseTags(value),
        });
      setResult(updated);
      onChanged();
      filesChanged();
    } catch (cause) {
      setError(errorText(cause));
    } finally {
      setBusy(false);
    }
  }

  return <Modal title={titles[action]} onClose={onClose} busy={busy}>
    <form onSubmit={submit} className="form-stack">
      {error && <Notice tone="error">{error}</Notice>}
      {result ? <div className="operation-results" aria-live="polite">
        <strong>成功 1 项</strong>
        <p className="success-text">{result.name}</p>
      </div> : action === "delete" ? <Notice tone="warning">
        将“{file.name}”移入回收站。正在进行的识别任务会取消，之后可在回收站还原文档。
      </Notice> : <label>
        {{ rename: "文件名称", move: "目标分类路径", tag: "标签（留空清除）" }[action]}
        <input autoFocus value={value} onChange={(event) => setValue(event.target.value)}
          disabled={busy} required={action !== "tag"} maxLength={action === "tag" ? 1300 : 255} />
      </label>}
      <div className="modal-actions">
        <button type="button" disabled={busy} onClick={onClose}>{result ? "完成" : "取消"}</button>
        {!result && <button className={action === "delete" ? "danger" : "primary"} disabled={busy}>
          {busy ? "正在处理…" : "确认"}
        </button>}
      </div>
    </form>
  </Modal>;
}
