/** 原始字段导出；每个单元格引号包裹并转义，危险首字符显式标记为文本。 */
export function csvCell(value: string): string {
  const dangerous = /^[\s\u0000-\u0020\u007f]*[=+@\-;']|^[\t\r\n]/.test(value);
  return `"${(dangerous ? "'" : "") + value.replace(/"/g, '""')}"`;
}
export function validDateRange(from: string, to: string): boolean {
  const valid = (value: string) =>
    !value ||
    (/^\d{4}-\d{2}-\d{2}$/.test(value) &&
      value < "9999-12-31" &&
      Number.isFinite(Date.parse(value)) &&
      new Date(value).toISOString().slice(0, 10) === value);
  return valid(from) && valid(to) && !(from && to && from > to);
}
