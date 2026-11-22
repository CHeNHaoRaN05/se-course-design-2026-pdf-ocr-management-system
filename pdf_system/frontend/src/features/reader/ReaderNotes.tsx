import { useState } from "react";
import { useAuth } from "../../app/AuthProvider";
import { errorText } from "../management/management";
import { useResource } from "../management/useResource";
import {
  addAnnotation, addBookmark, listAnnotations, listBookmarks,
  removeAnnotation, removeBookmark,
} from "./readerApi";

interface Props {
  fileId: string;
  pageNo: number;
  onPageChange: (page: number) => void;
}

export default function ReaderNotes({ fileId, pageNo, onPageChange }: Props) {
  const { me } = useAuth();
  const canEdit = me?.role === "admin" || me?.role === "user";
  const bookmarks = useResource((signal) => listBookmarks(fileId, signal), [fileId]);
  const notes = useResource((signal) => listAnnotations(fileId, pageNo, signal), [fileId, pageNo]);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function change(operation: () => Promise<unknown>, reload: () => void) {
    setBusy(true);
    setError("");
    try {
      await operation();
      reload();
    } catch (cause) {
      setError(errorText(cause));
    } finally {
      setBusy(false);
    }
  }

  return <section className="card">
    <h3>书签</h3>
    {canEdit && <button disabled={busy} onClick={() => void change(
      () => addBookmark(fileId, pageNo), bookmarks.reload,
    )}>添加本页书签</button>}
    {bookmarks.data?.length === 0 && <p className="muted">暂无书签。</p>}
    {!!bookmarks.data?.length && <ul>{bookmarks.data.map((bookmark) => <li key={bookmark.id}>
      <button onClick={() => onPageChange(bookmark.page_no)}>{bookmark.title || `第 ${bookmark.page_no} 页`}</button>
      {canEdit && <button disabled={busy} onClick={() => void change(
        () => removeBookmark(fileId, bookmark.id), bookmarks.reload,
      )}>删除书签</button>}
    </li>)}</ul>}
    <h3>本页批注</h3>
    {canEdit && <form onSubmit={(event) => {
      event.preventDefault();
      const note = text.trim();
      if (!note || busy) return;
      void change(async () => {
        await addAnnotation(fileId, { page_no: pageNo, kind: "note", text: note });
        setText("");
      }, notes.reload);
    }}>
      <label>批注内容<textarea value={text} maxLength={5000} onChange={(event) => setText(event.target.value)} /></label>
      <button disabled={busy || !text.trim()}>添加批注</button>
    </form>}
    {notes.data?.length === 0 && <p className="muted">本页暂无批注。</p>}
    {!!notes.data?.length && <ul>{notes.data.map((note) => <li key={note.id}>
      <p style={{ whiteSpace: "pre-wrap" }}>{note.payload.text}</p>
      {canEdit && <button disabled={busy} onClick={() => void change(
        () => removeAnnotation(fileId, note.id), notes.reload,
      )}>删除批注</button>}
    </li>)}</ul>}
    {(error || bookmarks.error || notes.error) && <p className="error" role="alert">
      {error || bookmarks.error || notes.error}
    </p>}
  </section>;
}
