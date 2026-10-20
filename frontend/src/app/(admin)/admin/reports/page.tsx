"use client";

import * as React from "react";
import {
  Award,
  BarChart3,
  CheckCircle2,
  Coins,
  Search,
  Sparkles,
} from "lucide-react";
import { fetchStaffList, fetchStaffPerformanceReport } from "@/lib/api";
import type { StaffPerformanceReport, UserDetail } from "@/lib/types";
import { addDaysISO, formatCurrency, formatDateISOInVN } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Badge,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";

export default function AdminReportsPage(): React.ReactElement {
  const today = React.useMemo(() => formatDateISOInVN(), []);
  const [startDate, setStartDate] = React.useState<string>(() =>
    addDaysISO(today, -30)
  );
  const [endDate, setEndDate] = React.useState<string>(() => today);
  const [staffId, setStaffId] = React.useState<string>("");
  const [commissionRate, setCommissionRate] = React.useState<number>(10);

  const [staffError, setStaffError] = React.useState<string | null>(null);
  const [staffAttempt, setStaffAttempt] = React.useState(0);
  const [staffList, setStaffList] = React.useState<UserDetail[]>([]);
  const [report, setReport] = React.useState<StaffPerformanceReport | null>(
    null
  );
  const [loading, setLoading] = React.useState<boolean>(true);
  const [error, setError] = React.useState<string | null>(null);

  const reportRequest = React.useRef(0);
  const loadReport = React.useCallback(async (): Promise<void> => {
    const request = ++reportRequest.current;
    setReport(null);
    if (!startDate || !endDate || endDate < startDate) {
      setLoading(false); setError("Ngày kết thúc phải bằng hoặc sau ngày bắt đầu."); return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await fetchStaffPerformanceReport({
        start_date: startDate,
        end_date: endDate,
        staff_id: staffId || undefined,
      });
      if (request === reportRequest.current) setReport(data);
    } catch (err) {
      if (request !== reportRequest.current) return;
      setError(
        err instanceof Error
          ? err.message
          : "Không thể tải báo cáo hiệu suất Kỹ thuật viên"
      );
    } finally {
      if (request === reportRequest.current) setLoading(false);
    }
  }, [startDate, endDate, staffId]);

  React.useEffect(() => {
    let cancelled = false;
    setStaffError(null);
    void fetchStaffList().then((list) => { if (!cancelled) setStaffList(list); })
      .catch((err: unknown) => { if (!cancelled) setStaffError(err instanceof Error ? err.message : "Không tải được danh sách KTV"); });
    return () => { cancelled = true; };
  }, [staffAttempt]);

  React.useEffect(() => {
    void loadReport();
    return () => { reportRequest.current += 1; };
  }, [loadReport]);

  return (
    <div className="min-w-0 space-y-5 [overflow-wrap:anywhere]">
      <div>
        <h1 className="text-xl font-bold text-foreground">
          Báo cáo Hiệu suất & Hoa hồng Kỹ thuật viên
        </h1>
        <p className="text-xs text-muted-foreground">
          Thống kê tổng số lịch hoàn thành (COMPLETED), số buổi dịch vụ lẻ /
          liệu trình và giá trị dịch vụ hoàn thành theo múi giờ Asia/Ho_Chi_Minh
        </p>
      </div>

      <p className="text-sm text-muted-foreground">Giá trị dịch vụ hoàn thành không phải tiền đã thu. Xem Thu tiền để đối chiếu thực thu. Hoa hồng chỉ là ước tính, chưa phải khoản lương đã chốt.</p>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void loadReport();
            }}
            className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-5 items-end [&>div]:min-w-0"
          >
            <div className="space-y-1">
              <Label htmlFor="repStart">Từ ngày</Label>
              <Input
                id="repStart"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="repEnd">Đến ngày</Label>
              <Input
                id="repEnd"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="repStaff">Lọc Kỹ thuật viên</Label>
              <select
                id="repStaff"
                value={staffId}
                onChange={(e) => setStaffId(e.target.value)}
                className="h-11 min-w-0 w-full rounded-md border border-input bg-background px-3 text-base font-medium sm:h-9 sm:text-sm"
              >
                <option value="">Tất cả Kỹ thuật viên</option>
                {staffList.map((st) => (
                  <option key={st.id} value={st.id}>
                    {st.full_name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <Label htmlFor="commRate">Tỷ lệ hoa hồng ước tính (%)</Label>
              <Input
                id="commRate"
                type="number"
                min={0}
                max={100}
                value={commissionRate}
                onChange={(e) =>
                  setCommissionRate(Math.min(100, Math.max(0, Number(e.target.value) || 0)))
                }
              />
            </div>

            <Button type="submit" disabled={loading}>
              <Search className="h-4 w-4" />
              {loading ? "Đang tính..." : "Xem báo cáo"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {error && (
        <div role="alert" className="rounded-lg border border-rose-300 bg-rose-50 px-4 py-2.5 text-xs font-medium text-rose-700">
          {error}
        </div>
      )}

      {staffError && <div role="alert" className="space-y-2 text-sm"><p>{staffError}</p><Button variant="outline" onClick={() => setStaffAttempt((v) => v + 1)}>Thử tải lại KTV</Button></div>}

      {/* Summary Cards */}
      {report && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card>
            <CardContent className="flex min-w-0 flex-wrap items-center gap-4 p-5">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <div>
                <p className="text-xs font-medium text-muted-foreground">
                  Tổng lịch hẹn hoàn thành
                </p>
                <p className="text-2xl font-bold text-foreground">
                  {report.totals.completed_bookings_count}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex min-w-0 flex-wrap items-center gap-4 p-5">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-purple-100 text-purple-700">
                <Sparkles className="h-6 w-6" />
              </div>
              <div>
                <p className="text-xs font-medium text-muted-foreground">
                  Tổng suất dịch vụ & buổi liệu trình
                </p>
                <p className="text-2xl font-bold text-foreground">
                  {report.totals.completed_services_count}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex min-w-0 flex-wrap items-center gap-4 p-5">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-100 text-amber-700">
                <Coins className="h-6 w-6" />
              </div>
              <div>
                <p className="text-xs font-medium text-muted-foreground">
                  Giá trị dịch vụ hoàn thành
                </p>
                <p className="text-2xl font-bold text-primary">
                  {formatCurrency(report.totals.total_revenue)}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Staff Performance Table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <BarChart3 className="h-4 w-4 text-primary" />
            Bảng chi tiết theo từng Kỹ thuật viên
          </CardTitle>
          <CardDescription>
            Khoảng thời gian: {startDate} → {endDate}
          </CardDescription>
        </CardHeader>
        <CardContent className="min-w-0 p-0">
          {loading ? (
            <p className="p-10 text-center text-xs text-muted-foreground">
              Đang tổng hợp dữ liệu...
            </p>
          ) : error ? (
            <Button variant="outline" onClick={() => void loadReport()}>Thử tải lại báo cáo</Button>
          ) : !report || report.staff.length === 0 ? (
            <p className="p-10 text-center text-xs text-muted-foreground">
              Không có dữ liệu Kỹ thuật viên trong khoảng thời gian này.
            </p>
          ) : (
            <table className="block w-full text-left text-sm lg:table lg:text-xs">
              <thead className="hidden lg:table-header-group border-b border-border bg-muted/60 text-[11px] font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="block min-w-0 px-4 py-3 lg:table-cell">Kỹ thuật viên</th>
                  <th className="block min-w-0 px-4 py-3 lg:table-cell text-center">Lịch hoàn thành</th>
                  <th className="block min-w-0 px-4 py-3 lg:table-cell text-center">Tổng dịch vụ đã làm</th>
                  <th className="block min-w-0 px-4 py-3 lg:table-cell text-center">
                    Chi tiết (Lẻ / Thẻ liệu trình)
                  </th>
                  <th className="block min-w-0 px-4 py-3 lg:table-cell text-right">Giá trị dịch vụ</th>
                  <th className="block min-w-0 px-4 py-3 lg:table-cell text-right">Hoa hồng ước tính ({commissionRate}%)</th>
                </tr>
              </thead>
              <tbody className="block space-y-3 p-3 lg:table-row-group lg:space-y-0 lg:divide-y lg:divide-border lg:p-0">
                {report.staff.map((item) => {
                  const rev = parseFloat(item.total_revenue) || 0;
                  const commission = (rev * commissionRate) / 100;
                  return (
                    <tr key={item.staff_id} className="grid min-w-0 grid-cols-2 rounded-xl border border-border lg:table-row lg:rounded-none lg:border-0 lg:hover:bg-muted/30">
                      <td className="col-span-2 block min-w-0 px-4 py-3 lg:table-cell">
                        <div className="flex min-w-0 flex-wrap items-center gap-2">
                          <Award className="h-4 w-4 text-primary" />
                          <div>
                            <p className="font-semibold text-foreground text-sm">
                              {item.full_name}
                            </p>
                            <p className="text-muted-foreground">
                              {staffList.find((staff) => staff.id === item.staff_id)?.phone_number}
                            </p>
                          </div>
                          {!item.is_active && (
                            <Badge variant="outline">Đã nghỉ</Badge>
                          )}
                        </div>
                      </td>
                      <td className="block min-w-0 px-4 py-3 lg:table-cell text-center font-semibold">
                        <span className="block text-xs font-normal text-muted-foreground lg:hidden">Lịch hoàn thành</span>
                        {item.completed_bookings_count}
                      </td>
                      <td className="block min-w-0 px-4 py-3 lg:table-cell text-center font-bold text-foreground">
                        <span className="block text-xs font-normal text-muted-foreground lg:hidden">Dịch vụ đã làm</span>
                        {item.completed_services_count}
                      </td>
                      <td className="block min-w-0 px-4 py-3 lg:table-cell text-center">
                        <span className="text-slate-700">
                          {item.single_services_count} lẻ
                        </span>{" "}
                        •{" "}
                        <span className="text-primary font-medium">
                          {item.package_sessions_count} buổi thẻ
                        </span>
                      </td>
                      <td className="col-span-2 block min-w-0 px-4 py-3 lg:table-cell text-right font-bold text-foreground">
                        <span className="block text-xs font-normal text-muted-foreground lg:hidden">Giá trị dịch vụ</span>
                        {formatCurrency(rev)}
                      </td>
                      <td className="col-span-2 block min-w-0 px-4 py-3 lg:table-cell text-right font-bold text-emerald-700">
                        <span className="block text-xs font-normal text-muted-foreground lg:hidden">Hoa hồng ước tính ({commissionRate}%)</span>
                        {formatCurrency(commission)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
