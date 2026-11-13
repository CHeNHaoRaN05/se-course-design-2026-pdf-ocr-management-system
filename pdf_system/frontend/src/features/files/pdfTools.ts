import { PDFDocument } from "pdf-lib";

export function splitGroups(
  value: string,
  total: number,
  every?: number,
): number[][] {
  if (!Number.isInteger(total) || total < 1 || total > 100)
    throw new Error("PDF 页数必须在 1–100 之间。");
  if (every !== undefined) {
    if (!Number.isInteger(every) || every < 1 || every > total)
      throw new Error(`每份页数应为 1–${total} 的整数。`);
    return Array.from({ length: Math.ceil(total / every) }, (_, group) =>
      Array.from(
        { length: Math.min(every, total - group * every) },
        (_, i) => group * every + i,
      ),
    );
  }
  if (!value.trim()) throw new Error("请输入拆分页段，例如 1-3,4-6。");
  const used = new Set<number>();
  return value
    .replace(/，/g, ",")
    .split(",")
    .map((part) => {
      const match = part.trim().match(/^(\d+)(?:\s*-\s*(\d+))?$/);
      if (!match)
        throw new Error("页段格式不正确，请使用 1-3,4-6 或单独页码。");
      const start = Number(match[1]);
      const end = Number(match[2] ?? match[1]);
      if (start < 1 || end < start || end > total)
        throw new Error(`页码必须在 1–${total} 之间，且起始页不能大于结束页。`);
      return Array.from({ length: end - start + 1 }, (_, i) => {
        const page = start + i - 1;
        if (used.has(page)) throw new Error("页段不能重复或重叠。");
        used.add(page);
        return page;
      });
    });
}
async function loadPdf(bytes: ArrayBuffer): Promise<PDFDocument> {
  try {
    return await PDFDocument.load(bytes);
  } catch {
    throw new Error("无法处理此 PDF，请确认文件未加密且内容完整。");
  }
}
export async function mergePdfs(buffers: ArrayBuffer[]): Promise<Uint8Array> {
  const target = await PDFDocument.create();
  for (const buffer of buffers) {
    const source = await loadPdf(buffer);
    if (target.getPageCount() + source.getPageCount() > 100)
      throw new Error("合并结果不能超过 100 页。");
    const pages = await target.copyPages(source, source.getPageIndices());
    pages.forEach((page) => target.addPage(page));
  }
  if (!target.getPageCount()) throw new Error("请选择至少一个有效 PDF。");
  return target.save();
}
export async function splitPdf(
  buffer: ArrayBuffer,
  groups: number[][],
): Promise<Uint8Array[]> {
  const source = await loadPdf(buffer);
  const result: Uint8Array[] = [];
  for (const group of groups) {
    if (
      !group.length ||
      group.some(
        (page) =>
          !Number.isInteger(page) || page < 0 || page >= source.getPageCount(),
      )
    )
      throw new Error("拆分页码超出文件实际范围。");
    const target = await PDFDocument.create();
    const pages = await target.copyPages(source, group);
    pages.forEach((page) => target.addPage(page));
    result.push(await target.save());
  }
  return result;
}
