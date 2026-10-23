"use client";

import * as React from "react";
import { Minus, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";

const FRAME = 260;
const MAX_ZOOM = 5;
const MAX_BYTES = 900 * 1024;

interface Props {
  /** Ảnh người dùng vừa chọn; null thì đóng hộp thoại. */
  file: File | null;
  title: string;
  /** Hình dạng khung hiển thị: tròn cho ảnh nhân viên, vuông cho logo. */
  round?: boolean;
  format: "png" | "jpeg";
  /** Cạnh ảnh xuất ra (px). Tự giảm nếu ảnh sau khi mã hóa vẫn quá nặng. */
  outputSize: number;
  onCancel: () => void;
  /** Nhận ảnh đã cắt ở dạng base64 (không kèm tiền tố data:). */
  onConfirm: (base64: string) => void;
}

function clamp(value: number, limit: number): number {
  return Math.max(-limit, Math.min(limit, value));
}

/** Khung cắt ảnh: kéo để di chuyển, thanh trượt hoặc con lăn để phóng to/thu nhỏ. Không giới hạn dung lượng ảnh gốc. */
export function ImageCropper({ file, title, round = false, format, outputSize, onCancel, onConfirm }: Props): React.ReactElement | null {
  const [image, setImage] = React.useState<HTMLImageElement | null>(null);
  const [url, setUrl] = React.useState("");
  const [zoom, setZoom] = React.useState(1);
  const [offset, setOffset] = React.useState({ x: 0, y: 0 });
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const drag = React.useRef<{ pointer: number; startX: number; startY: number; from: { x: number; y: number } } | null>(null);

  React.useEffect(() => {
    setImage(null); setError(null); setZoom(1); setOffset({ x: 0, y: 0 });
    if (!file) { setUrl(""); return; }
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    const element = new Image();
    let cancelled = false;
    element.onload = () => { if (!cancelled) setImage(element); };
    element.onerror = () => { if (!cancelled) setError("Không đọc được ảnh. Hãy chọn ảnh JPG, PNG hoặc WebP."); };
    element.src = objectUrl;
    return () => { cancelled = true; URL.revokeObjectURL(objectUrl); };
  }, [file]);

  const geometry = React.useMemo(() => {
    if (!image) return null;
    const cover = Math.max(FRAME / image.naturalWidth, FRAME / image.naturalHeight);
    const contain = Math.min(FRAME / image.naturalWidth, FRAME / image.naturalHeight);
    return { cover, minZoom: contain / cover };
  }, [image]);

  const limits = (nextZoom: number): { x: number; y: number } => {
    if (!image || !geometry) return { x: 0, y: 0 };
    const scale = geometry.cover * nextZoom;
    return { x: Math.max(0, (image.naturalWidth * scale - FRAME) / 2), y: Math.max(0, (image.naturalHeight * scale - FRAME) / 2) };
  };
  const applyZoom = (value: number): void => {
    if (!geometry) return;
    const next = Math.max(geometry.minZoom, Math.min(MAX_ZOOM, value));
    const bound = limits(next);
    setZoom(next);
    setOffset((current) => ({ x: clamp(current.x, bound.x), y: clamp(current.y, bound.y) }));
  };
  const move = (dx: number, dy: number): void => {
    const bound = limits(zoom);
    setOffset((current) => ({ x: clamp(current.x + dx, bound.x), y: clamp(current.y + dy, bound.y) }));
  };

  const exportImage = (): string => {
    if (!image || !geometry) throw new Error("Ảnh chưa sẵn sàng");
    const scale = geometry.cover * zoom;
    const attempts = [1, 0.75, 0.5, 0.35].map((factor) => Math.max(128, Math.round(outputSize * factor)));
    for (const size of attempts) {
      const canvas = document.createElement("canvas");
      canvas.width = canvas.height = size;
      const context = canvas.getContext("2d");
      if (!context) throw new Error("Trình duyệt không hỗ trợ xử lý ảnh.");
      if (format === "jpeg") { context.fillStyle = "#ffffff"; context.fillRect(0, 0, size, size); }
      const ratio = size / FRAME;
      const width = image.naturalWidth * scale * ratio, height = image.naturalHeight * scale * ratio;
      context.imageSmoothingQuality = "high";
      context.drawImage(image, size / 2 + offset.x * ratio - width / 2, size / 2 + offset.y * ratio - height / 2, width, height);
      const qualities = format === "jpeg" ? [0.9, 0.8, 0.65] : [undefined];
      for (const quality of qualities) {
        const data = canvas.toDataURL(format === "jpeg" ? "image/jpeg" : "image/png", quality).split(",")[1] || "";
        if (data.length * 0.75 <= MAX_BYTES) return data;
      }
    }
    throw new Error("Ảnh quá phức tạp để nén. Hãy thử ảnh khác.");
  };

  const confirm = (): void => {
    setBusy(true); setError(null);
    try { onConfirm(exportImage()); }
    catch (err) { setError(err instanceof Error ? err.message : "Không xử lý được ảnh"); }
    finally { setBusy(false); }
  };

  if (!file) return null;
  const scale = image && geometry ? geometry.cover * zoom : 1;
  return (
    <Modal open onClose={onCancel} title={title} maxWidthClass="max-w-md"
      footer={<div className="flex flex-wrap justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel}>Hủy</Button>
        <Button type="button" disabled={!image || busy} onClick={confirm}>{busy ? "Đang xử lý..." : "Dùng ảnh này"}</Button>
      </div>}>
      <div className="space-y-4">
        {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
        {!image && !error && <p role="status" className="py-10 text-center text-sm text-muted-foreground">Đang đọc ảnh...</p>}
        {image && geometry && (
          <>
            <p className="text-center text-xs text-muted-foreground">Kéo ảnh để chọn vùng hiển thị, dùng thanh trượt để phóng to hoặc thu nhỏ.</p>
            <div
              data-testid="crop-frame" tabIndex={0} role="group" aria-label="Khung cắt ảnh, kéo hoặc dùng phím mũi tên để di chuyển"
              className={"relative mx-auto touch-none select-none overflow-hidden border-2 border-primary bg-[conic-gradient(#e5e7eb_25%,#fff_0_50%,#e5e7eb_0_75%,#fff_0)] bg-[length:16px_16px] outline-none focus-visible:ring-2 focus-visible:ring-ring " + (round ? "rounded-full" : "rounded-2xl")}
              style={{ width: FRAME, height: FRAME, cursor: "grab" }}
              onPointerDown={(event) => { event.currentTarget.setPointerCapture(event.pointerId); drag.current = { pointer: event.pointerId, startX: event.clientX, startY: event.clientY, from: offset }; }}
              onPointerMove={(event) => {
                const state = drag.current;
                if (!state || state.pointer !== event.pointerId) return;
                const bound = limits(zoom);
                setOffset({ x: clamp(state.from.x + event.clientX - state.startX, bound.x), y: clamp(state.from.y + event.clientY - state.startY, bound.y) });
              }}
              onPointerUp={() => { drag.current = null; }} onPointerCancel={() => { drag.current = null; }}
              onWheel={(event) => applyZoom(zoom * (event.deltaY < 0 ? 1.08 : 0.92))}
              onKeyDown={(event) => {
                const step = event.shiftKey ? 30 : 10;
                const delta: Record<string, [number, number]> = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
                const change = delta[event.key];
                if (change) { event.preventDefault(); move(change[0], change[1]); }
              }}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={url} alt="Ảnh đang chỉnh" draggable={false} className="pointer-events-none absolute max-w-none"
                style={{ width: image.naturalWidth * scale, height: image.naturalHeight * scale,
                  left: FRAME / 2 + offset.x - (image.naturalWidth * scale) / 2, top: FRAME / 2 + offset.y - (image.naturalHeight * scale) / 2 }} />
            </div>
            <div className="flex items-center gap-2">
              <Button type="button" variant="outline" size="icon" aria-label="Thu nhỏ" onClick={() => applyZoom(zoom / 1.15)}><Minus className="h-4 w-4" /></Button>
              <input type="range" aria-label="Phóng to thu nhỏ" className="h-11 min-w-0 flex-1 accent-primary" min={geometry.minZoom} max={MAX_ZOOM} step={0.01}
                value={zoom} onChange={(event) => applyZoom(Number(event.target.value))} />
              <Button type="button" variant="outline" size="icon" aria-label="Phóng to" onClick={() => applyZoom(zoom * 1.15)}><Plus className="h-4 w-4" /></Button>
            </div>
            <div className="flex flex-wrap justify-center gap-2">
              <Button type="button" variant="outline" size="sm" onClick={() => { applyZoom(geometry.minZoom); setOffset({ x: 0, y: 0 }); }}>Vừa khung</Button>
              <Button type="button" variant="outline" size="sm" onClick={() => { setZoom(1); setOffset({ x: 0, y: 0 }); }}>Lấp đầy khung</Button>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}
