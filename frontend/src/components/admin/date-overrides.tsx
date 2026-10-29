"use client";
import * as React from "react";
import { displayDate } from "@/lib/display-date";
import { getDateOverrides, saveDateOverride, removeDateOverride, type DateOverride } from "@/lib/experience-api";
import { useBranchGuard } from "@/lib/branch-guard";
import { formatDateISOInVN } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
export function DateOverrides({ staffId, onBusyChange, onDirtyChange }: {staffId: string; onBusyChange?: (busy: boolean) => void; onDirtyChange?: (dirty: boolean) => void}): React.ReactElement {
  const [day, setDay] = React.useState(formatDateISOInVN), [off, setOff] = React.useState(true);
  const [start, setStart] = React.useState("08:00"), [end, setEnd] = React.useState("21:00");
  const [rows, setRows] = React.useState<DateOverride[]>([]), [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState(""), [attempt, setAttempt] = React.useState(0), [loaded, setLoaded] = React.useState(false);
  const flight = React.useRef(false);
  const baseline = React.useRef(JSON.stringify([day, off, start, end]));
  const dirty = JSON.stringify([day, off, start, end]) !== baseline.current;
  useBranchGuard(dirty, busy);
  React.useEffect(() => { onBusyChange?.(busy); return () => onBusyChange?.(false); }, [busy, onBusyChange]);
  React.useEffect(() => { onDirtyChange?.(dirty); return () => onDirtyChange?.(false); }, [dirty, onDirtyChange]);
  React.useEffect(() => { let cancelled = false; setLoaded(false); setRows([]); setError("");
    void getDateOverrides(staffId).then((value) => { if (!cancelled) { setRows(value); setLoaded(true); } })
      .catch((e: unknown) => { if (!cancelled) setError(e instanceof Error ? e.message : "Chưa tải được ngày nghỉ"); });
    return () => { cancelled = true; };
  }, [staffId, attempt]);
  const mutate = async (remove?: string) => {
    if (flight.current || !loaded || (remove && !window.confirm("Bỏ ca ngoại lệ ngày " + remove + " và trở về ca tuần?"))) return; flight.current = true; setBusy(true); setError("");
    try { if (remove) await removeDateOverride(staffId, remove); else await saveDateOverride(staffId, { day, start_time: start, end_time: end, is_day_off: off }); if (!remove) baseline.current = JSON.stringify([day, off, start, end]); setAttempt((value) => value + 1); }
    catch (e) { setError(e instanceof Error ? e.message : "Chưa cập nhật được ca theo ngày"); }
    finally { flight.current = false; setBusy(false); }
  };
  return <section aria-label="Ca riêng theo ngày" className="space-y-3 rounded-xl border p-4">
    <h3 className="font-semibold">Nghỉ hoặc đổi giờ trong một ngày</h3>
    <p className="text-xs text-muted-foreground">Không thay đổi lịch tuần. Nếu ảnh hưởng lịch đã nhận, hãy đổi hoặc hủy lịch hẹn trước khi lưu ca mới.</p>
    <div><Label htmlFor="overrideDay">Ngày áp dụng</Label><Input id="overrideDay" type="date" min={formatDateISOInVN()} value={day} disabled={busy} onChange={(event) => setDay(event.target.value)} /></div>
    <label className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" disabled={busy} checked={off} onChange={(event) => setOff(event.target.checked)} />Nghỉ cả ngày này</label>
    {!off && <div className="grid gap-2 sm:grid-cols-2"><div><Label htmlFor="overrideStart">Giờ bắt đầu</Label><Input id="overrideStart" type="time" disabled={busy} value={start} onChange={(event) => setStart(event.target.value)} /></div><div><Label htmlFor="overrideEnd">Giờ kết thúc</Label><Input id="overrideEnd" type="time" disabled={busy} value={end} onChange={(event) => setEnd(event.target.value)} /></div></div>}
    <Button type="button" disabled={busy || !loaded || !day} onClick={() => void mutate()}>Lưu ca cho ngày này</Button>
    {error && <div role="alert"><p>{error}</p>{!loaded && <Button variant="outline" onClick={() => setAttempt((value) => value + 1)}>Thử lại ca theo ngày</Button>}</div>}
    {rows.map((row) => <div key={row.day} className="flex flex-wrap items-center justify-between gap-2 border-t py-2 text-sm"><span>{displayDate(row.day)} · {row.is_day_off ? "Nghỉ" : row.start_time.slice(0,5) + " – " + row.end_time.slice(0,5)}</span><Button variant="outline" disabled={busy} onClick={() => void mutate(row.day)}>Trở về ca tuần</Button></div>)}
  </section>;
}
