"use client";
import * as React from "react";
import Link from "next/link";
import { ArrowRight, CalendarClock, Wallet } from "lucide-react";
import { fetchBookingPage, apiRequest } from "@/lib/api";
import type { BookingRecord, PaymentCollection } from "@/lib/types";
import { formatTimeVN, formatCurrency } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export function DashboardWork({ day }: { day: string }): React.ReactElement {
  const [data, setData] = React.useState<{ day: string; pending: BookingRecord[]; active: BookingRecord[] } | null>(null);
  const [collections, setCollections] = React.useState<PaymentCollection[]>([]);
  const [error, setError] = React.useState(false);
  const [attempt, setAttempt] = React.useState(0);
  React.useEffect(() => {
    let cancelled = false; setData(null); setCollections([]); setError(false);
    void Promise.all([
      fetchBookingPage({ date_from: day, date_to: day, status: "PENDING", limit: 5 }),
      fetchBookingPage({ date_from: day, date_to: day, status: "CONFIRMED", limit: 5 }),
      apiRequest<PaymentCollection[]>("/payments/collections?scope=outstanding&limit=5&offset=0"),
    ]).then(([pending, active, money]) => { if (!cancelled) { setData({ day, pending: pending.items, active: active.items }); setCollections(money); } })
      .catch(() => { if (!cancelled) setError(true); });
    return () => { cancelled = true; };
  }, [day, attempt]);
  const groups = data?.day === day ? [["Lịch chờ xác nhận", "PENDING", data.pending], ["Lịch đã xác nhận", "CONFIRMED", data.active]] as const : null;
  return <section aria-label="Công việc cần xử lý" className="space-y-4">
    <div><h2 className="text-lg font-semibold">Công việc trong ngày</h2><p className="mt-1 text-sm text-muted-foreground">Các lịch cần theo dõi và khoản cần thu.</p></div>
    {error ? <div role="alert" className="feedback-error space-y-3"><p>Chưa tải được công việc trong ngày.</p><Button variant="outline" onClick={() => setAttempt((value) => value + 1)}>Thử lại công việc</Button></div> : !groups ? <p role="status" className="rounded-xl bg-muted/40 p-5 text-sm text-muted-foreground">Đang tải công việc...</p> : <div className="grid gap-4 xl:grid-cols-2">{groups.map(([label, status, rows]) => <div key={status} className="flex min-w-0 flex-col rounded-2xl border bg-card p-4 shadow-sm sm:p-5">
      <h3 className="mb-4 flex items-center gap-2 font-semibold"><CalendarClock className="h-5 w-5 shrink-0 text-primary" />{label}</h3>
      <div className="flex-1 space-y-2">{rows.length === 0 ? <p className="empty-state">Không có lịch ở trạng thái này.</p> : rows.map((booking) => <Link key={booking.id} href={"/admin/bookings?" + new URLSearchParams({ booking_id: booking.id })} className="flex min-w-0 items-center gap-3 rounded-xl border border-transparent bg-muted/30 p-3 transition-colors hover:border-primary/20 hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
        <span className="shrink-0 rounded-lg bg-card px-2 py-2 text-sm font-bold tabular-nums text-primary">{formatTimeVN(booking.start_time)}</span>
        <span className="min-w-0 flex-1"><span className="block text-sm font-semibold [overflow-wrap:anywhere]">{booking.customer_name || "Khách hàng"}</span><span className="mt-1 block text-sm text-muted-foreground [overflow-wrap:anywhere]">{booking.staff_name || "Chưa phân công"}</span></span><ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" />
      </Link>)}</div>
      <div className="mt-4 border-t pt-3"><Link className="action-link w-full" href={"/admin/bookings?" + new URLSearchParams({ date: day, status })}>Xem toàn bộ {label.toLocaleLowerCase("vi")}<ArrowRight className="h-4 w-4 shrink-0" /></Link>
      {rows.length > 0 && <p className="mt-2 text-xs text-muted-foreground">Hiển thị tối đa 5 lịch theo giờ hẹn.</p>}</div>
    </div>)}</div>}
    {groups && <section className="space-y-4 rounded-2xl border bg-card p-4 shadow-sm sm:p-5"><h3 className="flex items-center gap-2 font-semibold"><Wallet className="h-5 w-5 shrink-0 text-primary" />Khoản cần thu hiện tại · mọi ngày</h3>
      {collections.length === 0 ? <p className="empty-state">Không có khoản đang cần thu.</p> : <div className="divide-y">{collections.map((row) => <Link key={row.source_type + ":" + row.source_id} href={"/admin/payments?customer_id=" + row.customer_id} className="flex min-w-0 flex-wrap items-center justify-between gap-3 rounded-lg px-2 py-4 transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><span className="min-w-0"><span className="block text-sm font-semibold [overflow-wrap:anywhere]">{row.customer_name}</span><span className="mt-1 block text-sm text-muted-foreground [overflow-wrap:anywhere]">{row.description}</span></span><span className="text-base font-bold tabular-nums text-primary">{row.balance_due === null ? "Cần đối chiếu giá" : formatCurrency(row.balance_due)}</span></Link>)}</div>}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-3"><p className="max-w-lg text-xs leading-relaxed text-muted-foreground">Hiển thị tối đa 5 khoản. Số tiền chưa thu khác giá trị dịch vụ đã hoàn thành.</p><Link className="action-link" href="/admin/payments">Xem toàn bộ khoản cần thu<ArrowRight className="h-4 w-4 shrink-0" /></Link></div>
    </section>}
  </section>;
}
