/** 第 03 线：全文检索、过滤、账号隔离的本机历史。 */
import { Fragment, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../../app/AuthProvider";
import { api } from "../../shared/http";
import {
  emptyFilters,
  historyKey,
  readHistory,
  rememberSearch,
  type SearchFilters,
} from "./searchHistory";
import {
  EmptyState,
  Icon,
  Loading,
  Notice,
  PageHeading,
} from "../../shared/ui";

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
  const [filters, setFilters] = useState<SearchFilters>({ ...emptyFilters });
  const [submitted, setSubmitted] = useState<SearchFilters | null>(null);
  const [items, setItems] = useState<Hit[]>([]);
  const [history, setHistory] = useState<SearchFilters[]>([]);
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
    setHistory(userId ? readHistory(userId) : []);
    setItems([]);
    setSubmitted(null);
    setFilters({ ...emptyFilters });
    setLoading(false);
    setError("");
    setNotice("");
    return () => {
      request.current++;
    };
  }, [userId]);
  useEffect(() => {
    if (userId && initialQuery.trim())
      void search({ ...emptyFilters, q: initialQuery.slice(0, 100) });
  }, [initialQuery, userId]);
  useEffect(() => {
    setSuggestions([]);
    if (!filters.file_name.trim() || filters.file_id) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      void api<{ items: FileOption[] }>(
        `/search/suggest?q=${encodeURIComponent(filters.file_name.trim())}`,
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
  }, [filters.file_name, filters.file_id, userId]);
  function change(key: keyof SearchFilters, value: string) {
    setFilters((previous) => ({ ...previous, [key]: value }));
  }
  async function search(value: SearchFilters, start = 0) {
    const normalized = { ...value, q: value.q.trim(), tag: value.tag.trim() };
    if (!normalized.q) {
      setError("请输入检索关键词");
      return;
    }
    if (normalized.file_name && !normalized.file_id) {
      setError("请从文件名建议中选择文件，或清空文件过滤");
      return;
    }
    if (
      normalized.date_from &&
      normalized.date_to &&
      normalized.date_from > normalized.date_to
    ) {
      setError("开始日期不能晚于结束日期");
      return;
    }
    const current = ++request.current;
    setLoading(true);
    setError("");
    setNotice("");
    setFilters(normalized);
    const params = new URLSearchParams({
      q: normalized.q,
      limit: String(PAGE_SIZE + 1),
      offset: String(start),
    });
    for (const key of ["file_id", "tag", "date_from", "date_to"] as const) {
      if (normalized[key]) params.set(key, normalized[key]);
    }
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
      else {
        if (result.backend === "substring")
          setNotice("本次使用子串匹配（单字查询或当前数据库未启用全文索引）。");
        if (userId) setHistory(rememberSearch(userId, normalized));
      }
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
          void search(filters);
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
              value={filters.q}
              onChange={(e) => change("q", e.target.value)}
            />
          </label>
          <button className="primary" disabled={loading || !userId}>
            <Icon name="search" />
            {loading ? "检索中…" : "检索"}
          </button>
        </div>
        <div className="row" style={{ flexWrap: "wrap", marginTop: 12 }}>
          <label>
            文件名
            <input
              maxLength={100}
              placeholder="输入名称后选择文件"
              value={filters.file_name}
              onChange={(e) =>
                setFilters((previous) => ({
                  ...previous,
                  file_name: e.target.value,
                  file_id: "",
                }))
              }
            />
          </label>
          <label>
            标签
            <input
              maxLength={64}
              placeholder="精确标签名"
              value={filters.tag}
              onChange={(e) => change("tag", e.target.value)}
            />
          </label>
          <label>
            上传日期（UTC）从
            <input
              type="date"
              value={filters.date_from}
              onChange={(e) => change("date_from", e.target.value)}
            />
          </label>
          <label>
            至
            <input
              type="date"
              value={filters.date_to}
              onChange={(e) => change("date_to", e.target.value)}
            />
          </label>
          <button
            type="button"
            onClick={() => setFilters({ ...emptyFilters, q: filters.q })}
          >
            清除过滤
          </button>
        </div>
        {suggestions.length > 0 && (
          <ul aria-label="文件建议">
            {suggestions.map((file) => (
              <li key={file.file_id}>
                <button
                  type="button"
                  onClick={() => {
                    setFilters((previous) => ({ ...previous, ...file }));
                    setSuggestions([]);
                  }}
                >
                  {file.file_name}
                </button>
              </li>
            ))}
          </ul>
        )}
      </form>
      <div className="card">
        <div className="row">
          <strong>最近检索</strong>
          <span className="muted">仅保存在此浏览器，按账号隔离</span>
          <button
            disabled={!history.length}
            onClick={() => {
              if (userId) {
                try {
                  localStorage.removeItem(historyKey(userId));
                } catch {
                  /* Disabled storage. */
                }
              }
              setHistory([]);
            }}
          >
            清空历史
          </button>
        </div>
        <div className="row" style={{ flexWrap: "wrap", marginTop: 8 }}>
          {history.map((entry, index) => (
            <button
              key={index}
              disabled={loading}
              title={[
                entry.file_name,
                entry.tag,
                entry.date_from,
                entry.date_to,
              ]
                .filter(Boolean)
                .join(" / ")}
              onClick={() => void search(entry)}
            >
              {entry.q}
              {entry.tag ? ` · ${entry.tag}` : ""}
            </button>
          ))}
        </div>
        {!history.length && <p className="muted">暂无检索历史。</p>}
      </div>
      {error && <Notice tone="error">{error}</Notice>}
      {notice && <Notice>{notice}</Notice>}
      <div className="card" aria-busy={loading}>
        {loading && <Loading text="正在检索文档内容…" />}
        {submitted && (
          <p className="search-results-heading">
            “{submitted.q}” · 本页 {groups.size} 份文档，{items.length}{" "}
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
                  <Highlight text={hit.snippet} keyword={submitted?.q ?? ""} />
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
                ? "试试更换关键词或放宽筛选条件。"
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
