/** 全文检索与文件名建议。 */
import { Fragment, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../../app/AuthProvider";
import { api } from "../../shared/http";
import {
  EmptyState,
  Icon,
  Loading,
  Notice,
  PageHeading,
} from "../management/ui";

interface Hit {
  file_id: string;
  file_name: string;
  page_no: number;
  job_id: string;
  revision: number;
  snippet: string;
}
interface FileOption {
  file_id: string;
  file_name: string;
}
const PAGE_SIZE = 20;
function Highlight({ text, keyword }: { text: string; keyword: string }) {
  if (!keyword) return <>{text}</>;
  return (
    <>
      {text.split(keyword).map((part, i) => (
        <Fragment key={i}>
          {i > 0 && <mark>{keyword}</mark>}
          {part}
        </Fragment>
      ))}
    </>
  );
}

export default function SearchPage() {
  const { me } = useAuth();
  const [params] = useSearchParams();
  const initialQuery = params.get("q") ?? "";
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [items, setItems] = useState<Hit[]>([]);
  const [suggestions, setSuggestions] = useState<FileOption[]>([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const request = useRef(0);
  const userId = me?.id;

  useEffect(() => {
    request.current++;
    setItems([]);
    setSubmitted(null);
    setQuery("");
    setLoading(false);
    setError("");
    setNotice("");
    return () => {
      request.current++;
    };
  }, [userId]);
  useEffect(() => {
    if (userId && initialQuery.trim())
      void search(initialQuery.slice(0, 100));
  }, [initialQuery, userId]);
  useEffect(() => {
    setSuggestions([]);
    if (!query.trim() || !userId || query.trim() === submitted) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      void api<{ items: FileOption[] }>(
        `/search/suggest?q=${encodeURIComponent(query.trim())}`,
        { signal: controller.signal },
      )
        .then((data) => {
          if (!controller.signal.aborted) setSuggestions(data.items);
        })
        .catch(() => undefined);
    }, 250);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [query, submitted, userId]);
  async function search(value: string, start = 0) {
    const normalized = value.trim();
    if (!normalized) return;
    const current = ++request.current;
    setLoading(true);
    setError("");
    setNotice("");
    setQuery(normalized);
    const params = new URLSearchParams({
      q: normalized,
      limit: String(PAGE_SIZE + 1),
      offset: String(start),
    });
    try {
      const result = await api<{ backend: string; items: Hit[] }>(
        `/search?${params}`,
      );
      if (current !== request.current) return;
      setItems(result.items.slice(0, PAGE_SIZE));
      setHasMore(result.items.length > PAGE_SIZE);
      setSubmitted(normalized);
      setOffset(start);
      if (result.backend === "ocr_not_ready")
        setNotice("OCR 服务尚未就绪，请启动服务后重试。");
      else if (result.backend === "substring")
        setNotice("本次使用子串匹配（单字查询或当前数据库未启用全文索引）。");
    } catch (e) {
      if (current === request.current) {
        setError(e instanceof Error ? e.message : "检索失败");
        setItems([]);
        setSubmitted(null);
      }
    } finally {
      if (current === request.current) setLoading(false);
    }
  }
  const groups = new Map<string, Hit[]>();
  for (const hit of items)
    groups.set(hit.file_id, [...(groups.get(hit.file_id) ?? []), hit]);
  return (
    <div className="workspace-page search-page">
      <PageHeading
        eyebrow="FIND YOUR KNOWLEDGE"
        title="全文检索"
        description="不用记住文件名，从文档内容中找到你需要的答案。"
      />
      <form
        className="card search-form"
        onSubmit={(event) => {
          event.preventDefault();
          void search(query);
        }}
      >
        <div className="row">
          <label style={{ flex: 1 }}>
            关键词
            <input
              style={{ width: "100%" }}
              maxLength={100}
              required
              placeholder="例如：显微镜"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <button className="primary" disabled={loading || !userId}>
            <Icon name="search" />
            {loading ? "检索中…" : "检索"}
          </button>
        </div>
        {suggestions.length > 0 && (
          <ul aria-label="文件建议">
            {suggestions.map((file) => (
              <li key={file.file_id}>
                <Link to={`/files/${file.file_id}`}>{file.file_name}</Link>
              </li>
            ))}
          </ul>
        )}
      </form>
      {error && <Notice tone="error">{error}</Notice>}
      {notice && <Notice>{notice}</Notice>}
      <div className="card" aria-busy={loading}>
        {loading && <Loading text="正在检索文档内容…" />}
        {submitted && (
          <p className="search-results-heading">
            “{submitted}” · 本页 {groups.size} 份文档，{items.length}{" "}
            个页面命中
          </p>
        )}
        {Array.from(groups, ([id, hits]) => (
          <section className="search-result" key={id}>
            <h3>
              <Icon name="file" />
              {hits[0].file_name}
              <span className="count-badge">本页 {hits.length} 处命中</span>
            </h3>
            {hits.map((hit) => (
              <div
                key={`${hit.file_id}-${hit.page_no}`}
                style={{ borderBottom: "1px solid #eee", padding: "8px 0" }}
              >
                <Link to={`/files/${hit.file_id}?page=${hit.page_no}`}>
                  第 {hit.page_no} 页
                </Link>
                <span className="muted"> · 修订 {hit.revision}</span>
                <span className="muted" title={hit.job_id}>
                  {" "}
                  · 来源任务 {hit.job_id.slice(0, 8)}
                </span>
                <p>
                  <Highlight text={hit.snippet} keyword={submitted ?? ""} />
                </p>
              </div>
            ))}
          </section>
        ))}
        {!items.length && !loading && (
          <EmptyState
            icon="search"
            title={submitted ? "没有找到匹配内容" : "从一个关键词开始"}
            description={
              submitted
                ? "试试更换关键词。"
                : "搜索已识别文档中的文字，点击结果即可跳到对应页。"
            }
          />
        )}
        {submitted && (
          <div className="row" style={{ marginTop: 12 }}>
            <button
              disabled={loading || offset === 0}
              onClick={() => void search(submitted, offset - PAGE_SIZE)}
            >
              上一页
            </button>
            <span>第 {Math.floor(offset / PAGE_SIZE) + 1} 页</span>
            <button
              disabled={loading || !hasMore}
              onClick={() => void search(submitted, offset + PAGE_SIZE)}
            >
              下一页
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
