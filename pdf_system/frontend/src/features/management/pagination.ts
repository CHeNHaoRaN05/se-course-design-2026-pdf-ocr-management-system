/** 兼容旧数组接口的有界读取。不能把重复页当成完整成功结果。 */
export async function readAllPages<T extends { id: string }>(
  read: (offset: number) => Promise<T[]>,
  signal?: AbortSignal,
): Promise<T[]> {
  const seen = new Set<string>();
  const result: T[] = [];
  for (let page = 0; page < 1000; page++) {
    if (signal?.aborted) throw new DOMException("请求已取消", "AbortError");
    const items = await read(page * 100);
    if (!Array.isArray(items) || items.length > 100)
      throw new Error("分页响应格式异常。");
    let added = 0;
    for (const item of items)
      if (!seen.has(item.id)) {
        seen.add(item.id);
        result.push(item);
        added++;
      }
    if (items.length && !added)
      throw new Error("服务端重复返回同一页，已停止加载，请重试。");
    if (items.length < 100) return result;
  }
  throw new Error("数据量超过加载上限，请缩小范围。");
}
