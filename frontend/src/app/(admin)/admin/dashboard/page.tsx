"use client";
import * as React from "react";
import Link from "next/link";
import { useAdminAuth } from "@/components/admin/auth-context";
import { fetchBranchDashboard } from "@/lib/api";
import { formatPaymentCurrency as money } from "@/lib/payment-api";
import { formatDateISOInVN } from "@/lib/utils";
import type { BranchDashboard, DashboardMetrics } from "@/lib/types";
import { Input, Label } from "@/components/ui/input";

function Metrics({ data }: { data: DashboardMetrics }): React.ReactElement {
  return <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
    {[
      ["Lịch hẹn", String(data.appointments)], ["Đang phục vụ", String(data.in_progress)],
      ["Đã hoàn thành", String(data.completed)], ["Thực thu trong ngày", money(data.net_received)],
      ["Tiền mặt", money(data.cash)], ["Chuyển khoản", money(data.bank_transfer)],
      ["Giá trị dịch vụ hoàn thành", money(data.completed_value)], ["Tổng còn thiếu", money(data.outstanding)],
      ["Thẻ còn hiệu lực hiện tại", String(data.active_packages)],
    ].map(([label, value]) => <div key={label} className="rounded-xl border bg-card p-4"><p className="text-xs text-muted-foreground">{label}</p><p className="mt-2 text-xl font-bold">{value}</p></div>)}
  </div>;
}
export default function DashboardPage(): React.ReactElement {
  const { user, tenant, branches } = useAdminAuth();
  const [day, setDay] = React.useState(() => formatDateISOInVN());
  const [all, setAll] = React.useState(false);
  const [data, setData] = React.useState<BranchDashboard | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);
  React.useEffect(() => { setAll(new URLSearchParams(window.location.search).get("scope") === "all"); }, []);
  React.useEffect(() => {
    if (user?.role !== "ADMIN") return;
    let cancelled = false;
    setLoading(true); setData(null); setError(null);
    void fetchBranchDashboard(day, all).then((value) => { if (!cancelled) setData(value); })
      .catch((e: unknown) => { if (!cancelled) setError(e instanceof Error ? e.message : "Không tải được dashboard"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [user?.role, tenant?.id, day, all]);
  if (user?.role !== "ADMIN") return <p>Chọn <Link className="underline" href="/admin/bookings">Lịch hẹn</Link> để xem công việc của bạn.</p>;
  return <div className="space-y-5">
    <h1 className="text-xl font-bold">Tổng quan {all ? "tất cả chi nhánh" : tenant?.name}</h1>
    <div className="flex flex-wrap items-end gap-3"><div><Label htmlFor="dashboardDay">Ngày theo giờ Việt Nam</Label><Input id="dashboardDay" type="date" required value={day} onChange={(e) => { if (e.target.value) setDay(e.target.value); }} /></div>
      {branches.some((b) => b.tenant.id === tenant?.id && b.is_owner) &&
        <Link className="text-sm underline" href={all ? "/admin/dashboard" : "/admin/dashboard?scope=all"}>{all ? "Xem chi nhánh hiện tại" : "Xem tất cả chi nhánh"}</Link>}
    </div>
    {error && <p role="alert" className="text-rose-700">{error}</p>}
    {loading && <p role="status">Đang tổng hợp...</p>}
    {data && <div data-testid="branch-dashboard" className="space-y-5">
      <Metrics data={data.totals} />
      <p className="text-xs text-muted-foreground">Lịch hẹn tính theo ngày phục vụ, không gồm lịch hủy/vắng mặt. Thực thu tính theo ngày ghi nhận tiền và hoàn tác. Tổng còn thiếu gồm toàn bộ khoản chưa thu; thẻ còn hiệu lực tính tại hiện tại.</p>
      {data.totals.unknown_prices > 0 && <p className="text-sm text-amber-700">{data.totals.unknown_prices} thẻ cũ cần đối chiếu giá, chưa cộng vào tổng còn thiếu.</p>}
      {all && data.branches.map((branch) => <section key={branch.branch_id} data-testid={"dashboard-" + branch.branch_id} className="space-y-3 rounded-xl border p-4"><h2 className="font-bold">{branch.name}</h2><Metrics data={branch.metrics} /></section>)}
      <div className="flex gap-4 text-sm"><Link className="underline" href="/admin/bookings">Xem lịch hẹn</Link><Link className="underline" href="/admin/payments">Thu tiền chi nhánh hiện tại</Link></div>
    </div>}
  </div>;
}
