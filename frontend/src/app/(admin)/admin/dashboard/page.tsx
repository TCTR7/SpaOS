"use client";
import * as React from "react";
import Link from "@/components/spa-link";
import { Building2, CalendarDays, Wallet, CircleDollarSign, Ticket } from "lucide-react";
import { useSearchParams } from "@/lib/spa-navigation";
import { SetupGuide } from "@/components/admin/setup-guide";
import { QuickActions } from "@/components/admin/quick-actions";
import { DashboardPanel } from "@/components/admin/dashboard-panel";
import { DashboardAppointments, DashboardCollections } from "@/components/admin/dashboard-work";
import { useAdminAuth } from "@/components/admin/auth-context";
import { fetchBranchDashboard } from "@/lib/api";
import { formatPaymentCurrency as money } from "@/lib/payment-api";
import { formatDateISOInVN } from "@/lib/utils";
import type { BranchDashboard, DashboardMetrics } from "@/lib/types";
import { Input, Label } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

function Values({ rows }: { rows: [string, string][] }): React.ReactElement {
  return <dl className="grid gap-4 sm:grid-cols-2">{rows.map(([label, value]) => <div key={label}><dt className="text-sm text-muted-foreground">{label}</dt><dd className="mt-1 text-lg font-semibold tabular-nums">{value}</dd></div>)}</dl>;
}
function BranchValues({ data }: { data: DashboardMetrics }): React.ReactElement {
  return <div className="space-y-5"><Values rows={[["Lịch hẹn trong ngày", String(data.appointments)], ["Đang phục vụ", String(data.in_progress)], ["Đã hoàn thành", String(data.completed)], ["Tiền đã thu trong ngày", money(data.net_received)], ["Tiền mặt", money(data.cash)], ["Chuyển khoản", money(data.bank_transfer)]]} /><div className="border-t pt-4"><Values rows={[["Khoản chưa thu · Tất cả ngày", money(data.outstanding)], ["Thẻ còn sử dụng · Hiện tại", String(data.active_packages)]]} /></div>{data.unknown_prices > 0 && <p className="text-sm text-amber-800">{data.unknown_prices} thẻ cần đối chiếu giá, chưa cộng vào khoản chưa thu.</p>}</div>;
}
export default function DashboardPage(): React.ReactElement {
  const { user, tenant } = useAdminAuth();
  const [day, setDay] = React.useState(() => formatDateISOInVN());
  const all = useSearchParams().get("scope") === "all";
  const queryKey = [user?.id, tenant?.id, day, all].join(":");
  const [result, setResult] = React.useState<{ key: string; data?: BranchDashboard; error?: string } | null>(null);
  const [attempt, setAttempt] = React.useState(0);
  React.useEffect(() => {
    if (user?.role !== "ADMIN") return;
    let cancelled = false; setResult(null);
    void fetchBranchDashboard(day, all).then((data) => { if (!cancelled) setResult({ key: queryKey, data }); })
      .catch((e: unknown) => { if (!cancelled) setResult({ key: queryKey, error: e instanceof Error ? e.message : "Không tải được tổng quan" }); });
    return () => { cancelled = true; };
  }, [user?.role, queryKey, day, all, attempt]);
  if (user?.role !== "ADMIN") return <p>Chọn <Link className="underline" href="/admin/bookings">Lịch hẹn</Link> để xem công việc của bạn.</p>;
  const current = result?.key === queryKey ? result : null;
  const data = current?.data, totals = data?.totals;
  const period = day === formatDateISOInVN() ? "Hôm nay" : day.split("-").reverse().join("/");
  const unavailable = current?.error ? "Chưa có dữ liệu" : "Đang tải…";
  return <div className="mx-auto min-w-0 max-w-5xl space-y-6 [overflow-wrap:anywhere]">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><h1 className="text-xl font-bold">Tổng quan</h1><p className="mt-1 text-sm text-muted-foreground">{all ? "Tất cả chi nhánh được cấp quyền" : tenant?.name}</p></div><div className="flex flex-wrap items-end gap-2"><div className="space-y-1"><Label htmlFor="dashboardDay">Ngày xem</Label><Input id="dashboardDay" type="date" required value={day} onChange={(e) => { if (e.target.value) setDay(e.target.value); }} /></div><Button variant="outline" onClick={() => setDay(formatDateISOInVN())}>Hôm nay</Button></div></div>
    {all && <p className="text-sm text-muted-foreground">Chọn một chi nhánh trên thanh đầu trang để xử lý lịch hẹn hoặc thu tiền.</p>}
    {current?.error && <div role="alert" className="space-y-3 rounded-xl border p-4"><p className="text-sm text-rose-700">{current.error}</p><Button variant="outline" onClick={() => setAttempt((v) => v + 1)}>Thử tải lại tổng quan</Button></div>}
    {!all && <QuickActions />}
    <div key={queryKey} data-testid="branch-dashboard" className="space-y-3" aria-busy={!current}>
      <DashboardPanel testId="dashboard-appointments" title="Lịch hẹn" description={period} summary={totals ? totals.appointments + " lịch" : unavailable} icon={CalendarDays}>
        {totals && <Values rows={[["Đang phục vụ", String(totals.in_progress)], ["Đã hoàn thành", String(totals.completed)]]} />}
        {!all && <DashboardAppointments key={day} day={day} />}
        {all && <p className="text-sm text-muted-foreground">Tổng số lịch của các chi nhánh trong ngày đang xem. Không gồm lịch hủy hoặc khách vắng mặt.</p>}
      </DashboardPanel>
      <DashboardPanel testId="dashboard-received" title="Tiền đã thu" description={period} summary={totals ? money(totals.net_received) : unavailable} icon={Wallet}>
        {totals && <><Values rows={[["Tiền mặt", money(totals.cash)], ["Chuyển khoản", money(totals.bank_transfer)]]} /><p className="text-sm text-muted-foreground">Tiền ghi nhận trong ngày đang xem, đã trừ các khoản hoàn tác cùng ngày.</p><details className="disclosure"><summary>Cách tính và giá trị dịch vụ</summary><div className="mt-3 space-y-3 text-sm"><p>Ngày tính theo giờ Việt Nam. Tiền đã thu dựa vào thời điểm ghi nhận thanh toán, bao gồm các bút toán hoàn tác.</p><p>Giá trị dịch vụ đã hoàn thành trong ngày: <strong>{money(totals.completed_value)}</strong>. Đây là giá trị dịch vụ theo lịch hẹn, độc lập với số tiền đã nhận.</p></div></details></>}
      </DashboardPanel>
      <DashboardPanel testId="dashboard-outstanding" title="Khoản chưa thu" description="Tất cả ngày · Cập nhật hiện tại" summary={totals ? money(totals.outstanding) : unavailable} icon={CircleDollarSign}>
        <p className="text-sm text-muted-foreground">Tổng tiền còn cần thu của tất cả ngày, không thay đổi theo ngày xem ở trên.</p>
        {totals && totals.unknown_prices > 0 && <p role="status" className="text-sm text-amber-800">{totals.unknown_prices} thẻ cũ cần đối chiếu giá, chưa cộng vào tổng tiền.</p>}
        {!all && <DashboardCollections />}
      </DashboardPanel>
      <DashboardPanel testId="dashboard-packages" title="Thẻ liệu trình" description="Còn sử dụng · Hiện tại" summary={totals ? totals.active_packages + " thẻ" : unavailable} icon={Ticket}>
        <p className="text-sm text-muted-foreground">Thẻ đang hoạt động, chưa hết hạn và còn buổi tại thời điểm hiện tại. Mục này không xem lại trạng thái thẻ của ngày trong quá khứ.</p>
        {!all && <Link className="action-link" href="/admin/customers">Quản lý thẻ liệu trình</Link>}
      </DashboardPanel>
      {all && data && <DashboardPanel testId="dashboard-branches" title="Theo từng chi nhánh" description="Mở để đối chiếu các chi nhánh" summary={data.branches.length + " chi nhánh"} icon={Building2}>
        {data.branches.map((branch) => <details key={branch.branch_id} data-testid={"dashboard-" + branch.branch_id} className="disclosure"><summary><span className="block font-semibold">{branch.name}</span><span className="mt-1 block text-sm font-normal text-muted-foreground">{branch.metrics.appointments} lịch · Đã thu {money(branch.metrics.net_received)}</span></summary><div className="mt-4 border-t pt-4"><BranchValues data={branch.metrics} /></div></details>)}
      </DashboardPanel>}
      {!all && <SetupGuide key={"setup:" + user.id + ":" + tenant?.id} />}
    </div>
  </div>;
}
