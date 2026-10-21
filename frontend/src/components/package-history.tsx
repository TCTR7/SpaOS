"use client";
import * as React from "react";
import { packageVisits, type PackageVisit } from "@/lib/experience-api";
import { BOOKING_STATUS_META, formatDateTimeVN } from "@/lib/utils";
import { Button } from "@/components/ui/button";
export function PackageHistory({ id, slug }: {id: string; slug?: string}): React.ReactElement {
  const [open, setOpen] = React.useState(false);
  const [rows, setRows] = React.useState<PackageVisit[]>([]);
  const [offset, setOffset] = React.useState(0);
  const [more, setMore] = React.useState(false);
  const [error, setError] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [attempt, setAttempt] = React.useState(0);
  React.useEffect(() => {
    if (!open) return;
    let cancelled = false; setLoading(true); setError("");
    void packageVisits(id, offset, slug).then((data) => { if (!cancelled) { setRows((old) => offset ? [...old, ...data] : data); setMore(data.length === 30); } })
      .catch(() => { if (!cancelled) setError("Chưa tải được lịch sử buổi. Hãy thử lại."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [open, id, slug, offset, attempt]);
  return <div className="space-y-2">
    <Button type="button" variant="outline" onClick={() => { if (!open) { setOffset(0); setRows([]); } setOpen((value) => !value); }} aria-expanded={open}>Lịch sử các buổi</Button>
    {open && <div className="space-y-3 rounded-xl border bg-muted/20 p-4 text-sm">
      {rows.map((row) => <p className="border-b border-border py-3 last:border-0" key={row.booking_id}>{formatDateTimeVN(row.start_time)} · {BOOKING_STATUS_META[row.status].label}</p>)}
      {!loading && !error && rows.length === 0 && <p className="empty-state">Chưa có lịch hẹn dùng thẻ này.</p>}
      {loading && <p role="status">Đang tải lịch sử...</p>}
      {error && <div role="alert"><p>{error}</p><Button variant="outline" onClick={() => setAttempt((value) => value + 1)}>Thử lại lịch sử</Button></div>}
      {more && !error && <Button disabled={loading} variant="outline" onClick={() => setOffset(rows.length)}>Xem thêm buổi</Button>}
      <p className="text-xs text-muted-foreground">Chỉ buổi đã hoàn thành mới được tính là đã dùng. Lịch hủy không trừ buổi.</p>
    </div>}
  </div>;
}
