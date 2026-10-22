/** 中文全文检索（负责人：丙）。
 *  命中后用 file_id + page_no 直达阅读器对应页，再由 job_id 取 OCR 坐标。
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../shared/http";

interface Hit {
  file_id: string;
  file_name: string;
  page_no: number;
  job_id: string;
  revision: number;
  snippet: string;
}

export default function SearchPage() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [backend, setBackend] = useState("");
  const [items, setItems] = useState<Hit[]>([]);
  const [error, setError] = useState("");

  async function run(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const result = await api<{ backend: string; items: Hit[] }>(`/search?q=${encodeURIComponent(q)}`);
      setBackend(result.backend);
      setItems(result.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "检索失败");
    }
  }

  return (
    <div>
      <form className="card row" onSubmit={run}>
        <input style={{ flex: 1 }} placeholder="输入关键词，例如：显微镜" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="primary" type="submit">检索</button>
        {backend && <span className="muted">检索引擎：{backend}</span>}
      </form>
      {error && <p className="error">{error}</p>}
      <div className="card">
        {items.map((hit) => (
          <div key={`${hit.file_id}-${hit.page_no}`} style={{ padding: "8px 0", borderBottom: "1px solid #f2f3f5" }}>
            <a href="#" onClick={(e) => { e.preventDefault(); navigate(`/files/${hit.file_id}?page=${hit.page_no}`); }}>
              {hit.file_name} · 第 {hit.page_no} 页
            </a>
            {/* 纯文本渲染：不使用 dangerouslySetInnerHTML */}
            <p className="muted">{hit.snippet}</p>
          </div>
        ))}
        {items.length === 0 && <p className="muted">没有命中结果。</p>}
      </div>
    </div>
  );
}
