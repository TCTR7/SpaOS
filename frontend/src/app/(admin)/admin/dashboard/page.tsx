"use client";
import * as React from "react";
import { SetupGuide } from "@/components/admin/setup-guide";
import { DashboardWork } from "@/components/admin/dashboard-work";
import Link from "next/link";
import { ArrowRight, Building2 } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useAdminAuth } from "@/components/admin/auth-context";
import { fetchBranchDashboard } from "@/lib/api";
import { formatPaymentCurrency as money } from "@/lib/payment-api";
import { formatDateISOInVN } from "@/lib/utils";
import type { BranchDashboard, DashboardMetrics } from "@/lib/types";
import { Input, Label } from "@/components/ui/input";

function Metrics({ data }: { data: DashboardMetrics }): React.ReactElement {
  const groups = [
    { title: "Theo ngày đang xem", rows: [["Lịch hẹn", String(data.appointments)], ["Đang phục vụ", String(data.in_progress)], ["Đã hoàn thành", String(data.completed)], ["Thực thu trong ngày", money(data.net_received)], ["Tiền mặt", money(data.cash)], ["Chuyển khoản", money(data.bank_transfer)], ["Giá trị dịch vụ hoàn thành", money(data.completed_value)]] },
    { title: "Đối chiếu hiện tại · mọi ngày", rows: [["Tổng còn thiếu", money(data.outstanding)], ["Thẻ còn hiệu lực hiện tại", String(data.active_packages)]] },
  ];
  return <div className="space-y-5">{groups.map((group, index) => <section key={group.title} className="space-y-3"><h2 className="text-sm font-semibold text-muted-foreground">{group.title}</h2>
    <div className="grid gap-3 sm:grid-cols-2">{group.rows.filter(([label]) => index === 1 || label === "Lịch hẹn" || label === "Thực thu trong ngày").map(([label, value]) => <div key={label} className="min-w-0 rounded-2xl border bg-card p-5 shadow-sm [overflow-wrap:anywhere]"><p className="text-sm text-muted-foreground">{label}</p><p className="mt-2 text-2xl font-bold tabular-nums text-primary">{value}</p></div>)}</div>
    {index === 0 && <dl className="grid gap-x-5 gap-y-3 rounded-xl border bg-card px-5 py-4 sm:grid-cols-2 xl:grid-cols-3">{group.rows.filter(([label]) => label !== "Lịch hẹn" && label !== "Thực thu trong ngày").map(([label, value]) => <div key={label} className="min-w-0"><dt className="text-xs text-muted-foreground">{label}</dt><dd className="mt-1 text-base font-semibold tabular-nums [overflow-wrap:anywhere]">{value}</dd></div>)}</dl>}
  </section>)}</div>;
}
export default function DashboardPage(): React.ReactElement {
  const { user, tenant, branches } = useAdminAuth();
  const [day, setDay] = React.useState(() => formatDateISOInVN());
  const all = useSearchParams().get("scope") === "all";
  const [data, setData] = React.useState<BranchDashboard | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [attempt, setAttempt] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  React.useEffect(() => {
    if (user?.role !== "ADMIN") return;
    let cancelled = false;
    setLoading(true); setData(null); setError(null);
    void fetchBranchDashboard(day, all).then((value) => { if (!cancelled) setData(value); })
      .catch((e: unknown) => { if (!cancelled) setError(e instanceof Error ? e.message : "Không tải được dashboard"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [user?.role, tenant?.id, day, all, attempt]);
  if (user?.role !== "ADMIN") return <p>Chọn <Link className="underline" href="/admin/bookings">Lịch hẹn</Link> để xem công việc của bạn.</p>;
  return <div className="min-w-0 space-y-5 [overflow-wrap:anywhere]">
    <h1 className="text-xl font-bold">Tổng quan {all ? "tất cả chi nhánh" : tenant?.name}</h1>
    {!all ? <nav aria-label="Công việc tại chi nhánh" className="flex flex-wrap gap-3">
      <Link className="inline-flex min-h-11 items-center rounded-lg border bg-card px-4 text-sm font-semibold" href="/admin/bookings">Xem lịch hẹn</Link>
      <Link className="inline-flex min-h-11 items-center rounded-lg border bg-card px-4 text-sm font-semibold" href="/admin/payments">Thu tiền chi nhánh hiện tại</Link>
    </nav> : <p role="status" className="text-sm">Đang xem tổng hợp. Chọn một chi nhánh để quản lý lịch hẹn và thu tiền.</p>}
    <div className="flex flex-wrap items-end gap-3"><div><Label htmlFor="dashboardDay">Ngày theo giờ Việt Nam</Label><Input id="dashboardDay" type="date" required value={day} onChange={(e) => { if (e.target.value) setDay(e.target.value); }} /></div>
      {branches.some((b) => b.tenant.id === tenant?.id && b.is_owner) &&
        <a className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-primary/20 bg-primary/10 px-4 py-2 text-sm font-semibold text-primary transition-colors hover:bg-primary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" href={all ? "/admin/dashboard" : "/admin/dashboard?scope=all"}><Building2 className="h-4 w-4 shrink-0" />{all ? "Xem chi nhánh hiện tại" : "Xem tất cả chi nhánh"}<ArrowRight className="h-4 w-4 shrink-0" /></a>}
    </div>
    {error && <div role="alert" className="space-y-2 text-rose-700"><p>{error}</p><button className="min-h-11 rounded-lg border px-3 text-sm" onClick={() => setAttempt((v) => v + 1)}>Thử tải lại tổng quan</button></div>}
    {loading && <p role="status">Đang tổng hợp...</p>}
    {!all && <SetupGuide key={"setup:" + user.id + ":" + tenant?.id} />}
    {!all && <DashboardWork key={"work:" + user.id + ":" + tenant?.id} day={day} />}
    {data && <div data-testid="branch-dashboard" className="space-y-5">
      <Metrics data={data.totals} />
      <p className="text-xs text-muted-foreground">Lịch hẹn tính theo ngày phục vụ, không gồm lịch hủy/vắng mặt. Thực thu tính theo ngày ghi nhận tiền và hoàn tác. Tổng còn thiếu gồm toàn bộ khoản chưa thu; thẻ còn hiệu lực tính tại hiện tại.</p>
      {data.totals.unknown_prices > 0 && <p className="text-sm text-amber-700">{data.totals.unknown_prices} thẻ cũ cần đối chiếu giá, chưa cộng vào tổng còn thiếu.</p>}
      {all && data.branches.map((branch) => <details key={branch.branch_id} data-testid={"dashboard-" + branch.branch_id} className="disclosure"><summary><span className="block text-base">{branch.name}</span><span className="mt-2 flex flex-wrap gap-x-6 gap-y-2 text-sm font-normal text-muted-foreground"><span>{branch.metrics.appointments} lịch hẹn</span><span>Thực thu: {money(branch.metrics.net_received)}</span><span>Còn thiếu (mọi ngày): {money(branch.metrics.outstanding)}</span></span></summary><div className="mt-4 border-t pt-4"><Metrics data={branch.metrics} /></div></details>)}
    </div>}
  </div>;
}
