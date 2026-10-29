"use client";
import * as React from "react";
import Link from "@/components/spa-link";
import { fetchBookingPage, apiRequest } from "@/lib/api";
import type { BookingRecord, PaymentCollection } from "@/lib/types";
import { formatTimeVN } from "@/lib/utils";
import { formatPaymentCurrency as money } from "@/lib/payment-api";
import { Button } from "@/components/ui/button";

export function DashboardAppointments({ day }: { day: string }): React.ReactElement {
  const [rows, setRows] = React.useState<BookingRecord[][] | null>(null);
  const [error, setError] = React.useState(false);
  const [attempt, setAttempt] = React.useState(0);
  React.useEffect(() => {
    let cancelled = false; setRows(null); setError(false);
    void Promise.all((["PENDING", "CONFIRMED", "IN_PROGRESS"] as const).map((status) => fetchBookingPage({ date_from: day, date_to: day, status, limit: 5 })))
      .then((pages) => { if (!cancelled) setRows(pages.map((page) => page.items)); })
      .catch(() => { if (!cancelled) setError(true); });
    return () => { cancelled = true; };
  }, [day, attempt]);
  return <div className="space-y-5">
    {error ? <div role="alert" className="space-y-3"><p>Chưa tải được lịch hẹn.</p><Button variant="outline" onClick={() => setAttempt((v) => v + 1)}>Thử lại lịch hẹn</Button></div>
      : !rows ? <p role="status" className="text-sm text-muted-foreground">Đang tải lịch hẹn...</p>
      : <div className="grid gap-5 lg:grid-cols-3">{(["Chờ xác nhận", "Đã xác nhận", "Đang phục vụ"] as const).map((label, index) => <section key={label} className="min-w-0 space-y-3"><h3 className="text-sm font-semibold">{label}</h3>
        {rows[index].length === 0 ? <p className="text-sm text-muted-foreground">Không có lịch.</p> : rows[index].map((booking) => <Link key={booking.id} href={"/admin/bookings?" + new URLSearchParams({ booking_id: booking.id })} className="flex min-h-12 items-center gap-3 rounded-lg p-2 hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><span className="shrink-0 text-sm font-semibold tabular-nums">{formatTimeVN(booking.start_time)}</span><span className="min-w-0"><span className="block text-sm font-medium">{booking.customer_name || "Khách hàng"}</span><span className="block text-xs text-muted-foreground">{booking.staff_name || "Chưa phân công"}</span></span></Link>)}
        <Link className="action-link text-sm" href={"/admin/bookings?" + new URLSearchParams({ date: day, status: (["PENDING", "CONFIRMED", "IN_PROGRESS"] as const)[index] })}>Xem lịch {label.toLocaleLowerCase("vi")}</Link>
      </section>)}</div>}
    <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4"><p className="text-xs text-muted-foreground">Tối đa 5 lịch mỗi trạng thái. Số lịch không gồm lịch hủy hoặc khách vắng mặt.</p><Link className="action-link" href={"/admin/bookings?" + new URLSearchParams({ date: day })}>Mở lịch hẹn</Link></div>
  </div>;
}
export function DashboardCollections(): React.ReactElement {
  const [rows, setRows] = React.useState<PaymentCollection[] | null>(null);
  const [error, setError] = React.useState(false);
  const [attempt, setAttempt] = React.useState(0);
  React.useEffect(() => {
    let cancelled = false; setRows(null); setError(false);
    void apiRequest<PaymentCollection[]>("/payments/collections?scope=outstanding&limit=5&offset=0")
      .then((value) => { if (!cancelled) setRows(value); }).catch(() => { if (!cancelled) setError(true); });
    return () => { cancelled = true; };
  }, [attempt]);
  return <div className="space-y-4">
    {error ? <div role="alert" className="space-y-3"><p>Chưa tải được khoản chưa thu.</p><Button variant="outline" onClick={() => setAttempt((v) => v + 1)}>Thử lại khoản chưa thu</Button></div>
      : !rows ? <p role="status" className="text-sm text-muted-foreground">Đang tải khoản chưa thu...</p>
      : rows.length === 0 ? <p className="text-sm text-muted-foreground">Không có khoản đang cần thu.</p>
      : <div className="divide-y">{rows.map((row) => <Link key={row.source_type + ":" + row.source_id} href={"/admin/payments?customer_id=" + row.customer_id} className="flex min-h-12 flex-wrap items-center justify-between gap-3 rounded-lg px-2 py-3 hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><span className="min-w-0"><span className="block text-sm font-semibold">{row.customer_name}</span><span className="mt-1 block text-sm text-muted-foreground">{row.description}</span></span><span className="font-semibold tabular-nums">{row.balance_due === null ? "Cần đối chiếu giá" : money(row.balance_due)}</span></Link>)}</div>}
    <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4"><p className="text-xs text-muted-foreground">Tối đa 5 khoản chưa thu, gồm tất cả ngày.</p><Link className="action-link" href="/admin/payments">Thu tiền</Link></div>
  </div>;
}
