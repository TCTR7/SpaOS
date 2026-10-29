"use client";
import * as React from "react";
import Link from "@/components/spa-link";
import { apiRequest } from "@/lib/api";
import type { BookingRecord } from "@/lib/types";
import { BOOKING_STATUS_META, formatDateTimeVN } from "@/lib/utils";
import { Button } from "@/components/ui/button";
export function CustomerVisits({ customerId }: {customerId: string}): React.ReactElement {
  const [rows, setRows] = React.useState<{upcoming: BookingRecord | null; history: BookingRecord | null} | null>(null);
  const [error, setError] = React.useState(false), [attempt, setAttempt] = React.useState(0);
  React.useEffect(() => { let cancelled = false; setRows(null); setError(false);
    void Promise.all(["upcoming", "history"].map((scope) => apiRequest<BookingRecord[]>("/bookings?customer_id=" + customerId + "&scope=" + scope + "&limit=1")))
      .then(([upcoming, history]) => { if (!cancelled) setRows({upcoming: upcoming[0] || null, history: history[0] || null}); })
      .catch(() => { if (!cancelled) setError(true); });
    return () => { cancelled = true; };
  }, [customerId, attempt]);
  return <section aria-label="Lịch gần đây của khách" className="space-y-2 rounded-lg border p-3 text-sm"><h3 className="font-semibold">Lịch hẹn của khách</h3>
    {error ? <div role="alert"><p>Chưa tải được lịch gần đây.</p><Button variant="outline" onClick={() => setAttempt((value) => value + 1)}>Thử lại lịch của khách</Button></div> : !rows ? <p role="status">Đang tải lịch...</p> : <>{(["upcoming", "history"] as const).map((scope) => <div className="rounded-xl bg-muted/30 p-3" key={scope}><p className="text-xs text-muted-foreground">{scope === "upcoming" ? "Sắp tới" : "Lịch sử gần nhất"}</p>{rows[scope] ? <Link className="action-link mt-2" href={"/admin/bookings?booking_id=" + rows[scope]!.id}>{formatDateTimeVN(rows[scope]!.start_time)} · {BOOKING_STATUS_META[rows[scope]!.status].label}</Link> : <p>{scope === "upcoming" ? "Chưa có lịch sắp tới." : "Chưa có lịch sử hẹn."}</p>}</div>)}</>}
  </section>;
}
