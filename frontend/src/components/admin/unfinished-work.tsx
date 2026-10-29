"use client";
import * as React from "react";
import { Button } from "@/components/ui/button";

export type WorkLocation = { tab: string; title: string; path: string; pending: boolean };
export function UnfinishedWork(): React.ReactElement | null {
  const [items, setItems] = React.useState<WorkLocation[]>([]);
  React.useEffect(() => {
    const show = (event: Event): void => setItems((event as CustomEvent<WorkLocation[]>).detail);
    window.addEventListener("spaos:unfinished-work", show);
    return () => window.removeEventListener("spaos:unfinished-work", show);
  }, []);
  if (!items.length) return null;
  return <section className="mb-4 space-y-3 rounded-xl border bg-card p-4" aria-label="Công việc đang dở">
    <p className="font-semibold">Tiếp tục công việc trước khi đổi chi nhánh</p>
    {items.map(item => <div key={item.tab} className="flex flex-wrap items-center justify-between gap-2">
      <p className="text-sm">{item.title} · {item.pending ? "Đang xử lý" : "Có thay đổi chưa lưu"}</p>
      <Button variant="outline" onClick={() => {
        if (window.name === item.tab) {
          document.querySelector<HTMLDialogElement>("dialog[open]")?.scrollIntoView();
          document.querySelector<HTMLElement>("dialog[open] input:not([disabled]), dialog[open] button")?.focus();
        } else {
          // Reuse the live named tab without navigating, preserving its complete form state.
          const target = window.open("", item.tab); target?.focus();
        }
      }}>Đến công việc đang dở</Button>
    </div>)}
    <p className="text-xs text-muted-foreground">Giữ nguyên tab và dữ liệu đang nhập. Nếu trình duyệt không tự chuyển tab, chọn tab có tên màn hình bên trên.</p>
    <Button variant="ghost" onClick={()=>setItems([])}>Ẩn danh sách</Button>
  </section>;
}
