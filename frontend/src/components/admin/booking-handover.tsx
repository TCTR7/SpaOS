"use client";
import * as React from "react";
import { apiRequest } from "@/lib/api";
import { useBranchGuard } from "@/lib/branch-guard";
import { Button } from "@/components/ui/button";
import { Label, Textarea } from "@/components/ui/input";
export function BookingHandover({ bookingId, canManage, onDirtyChange, onBusyChange }: {bookingId: string; canManage: boolean; onDirtyChange?: (value: boolean) => void; onBusyChange?: (value: boolean) => void}): React.ReactElement {
  const [note, setNote] = React.useState(""), [baseline, setBaseline] = React.useState<string | null>(null), [error, setError] = React.useState("");
  const [attempt, setAttempt] = React.useState(0), [busy, setBusy] = React.useState(false), [message, setMessage] = React.useState("");
  const flight = React.useRef(false);
  React.useEffect(() => { onDirtyChange?.(canManage && baseline !== null && note !== baseline); return () => onDirtyChange?.(false); }, [canManage, baseline, note, onDirtyChange]);
  React.useEffect(() => { onBusyChange?.(busy); return () => onBusyChange?.(false); }, [busy, onBusyChange]);
  useBranchGuard(canManage && baseline !== null && note !== baseline, busy);
  React.useEffect(() => { let cancelled = false; setBaseline(null); setNote(""); setError("");
    void apiRequest<{note: string}>("/bookings/" + bookingId + "/handover").then((value) => { if (!cancelled) { setNote(value.note); setBaseline(value.note); } })
      .catch(() => { if (!cancelled) setError("Chưa tải được ghi chú bàn giao."); });
    return () => { cancelled = true; };
  }, [bookingId, attempt]);
  return <section aria-label="Bàn giao buổi hẹn" className="mt-3 space-y-3 rounded-xl border bg-card p-4">
    <h3 className="font-semibold">Bàn giao buổi hẹn</h3>
    <p className="text-xs text-muted-foreground">Chỉ viết thông tin cần thiết cho buổi này sau khi đã xác nhận với khách. Không sao chép toàn bộ hồ sơ sức khỏe. Ghi chú không gửi qua thông báo thiết bị.</p>
    {error && <div role="alert"><p>{error}</p><Button variant="outline" onClick={() => setAttempt((value) => value + 1)}>Tải lại bàn giao</Button></div>}
    {baseline !== null && (canManage ? <><Label htmlFor="handoverNote">Thông tin cần bàn giao</Label><Textarea id="handoverNote" maxLength={1000} disabled={busy} value={note} onChange={(event) => setNote(event.target.value)} />
      <Button type="button" disabled={busy || note === baseline} onClick={async () => {
        if (flight.current) return; flight.current = true; setBusy(true); setError("");
        try { await apiRequest("/bookings/" + bookingId + "/handover", { method: "PUT", body: { note } }); setBaseline(note); setMessage("Đã lưu bàn giao cho lịch này."); }
        catch (e) { setError(e instanceof Error ? e.message : "Chưa lưu được bàn giao"); }
        finally { flight.current = false; setBusy(false); }
      }}>Lưu bàn giao</Button></> : <p className="whitespace-pre-wrap text-sm">{note || "Chưa có ghi chú bàn giao. Hãy trao đổi với chủ spa hoặc người phụ trách khách trước khi phục vụ."}</p>)}
    {message && <p role="status" className="feedback-success">{message}</p>}
  </section>;
}
