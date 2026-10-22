/** OCR 框覆盖层（负责人：丙，契约 C4）。
 *  输入是归一化左上原点坐标 [left, top, right, bottom]，
 *  乘以 pdf.js 当前 viewport 的实际像素尺寸即可对齐；
 *  阅读器若额外做了 90/180/270 度旋转，需要先旋转四个角再取包围盒。
 */
import type { OcrBlock } from "../../shared/types";

interface Props {
  blocks: OcrBlock[];
  width: number;
  height: number;
  activeId?: number;
  onPick?: (block: OcrBlock) => void;
}

export default function OcrOverlay({ blocks, width, height, activeId, onPick }: Props) {
  return (
    <>
      {blocks.map((block) => {
        const [left, top, right, bottom] = block.bbox;
        const style = {
          left: left * width,
          top: top * height,
          width: (right - left) * width,
          height: (bottom - top) * height,
        };
        const className = ["ocr-box", block.needs_review ? "review" : "", block.id === activeId ? "active" : ""]
          .filter(Boolean).join(" ");
        return (
          <div
            key={block.id}
            className={className}
            style={style}
            title={`${block.text}（置信度 ${block.confidence.toFixed(2)}）`}
            onClick={() => onPick?.(block)}
          />
        );
      })}
    </>
  );
}
