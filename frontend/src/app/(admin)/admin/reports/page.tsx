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

  const [staffList, setStaffList] = React.useState<UserDetail[]>([]);
  const [report, setReport] = React.useState<StaffPerformanceReport | null>(
    null
  );
  const [loading, setLoading] = React.useState<boolean>(true);
  const [error, setError] = React.useState<string | null>(null);

  const loadReport = React.useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchStaffPerformanceReport({
        start_date: startDate,
        end_date: endDate,
        staff_id: staffId || undefined,
      });
      setReport(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Không thể tải báo cáo hiệu suất Kỹ thuật viên"
      );
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate, staffId]);

  React.useEffect(() => {
    void (async () => {
      try {
        const list = await fetchStaffList();
        setStaffList(list);
      } catch {
        // ignore
      }
    })();
  }, []);

  React.useEffect(() => {
    void loadReport();
  }, [loadReport]);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-foreground">
          Báo cáo Hiệu suất & Hoa hồng Kỹ thuật viên
        </h1>
        <p className="text-xs text-muted-foreground">
          Thống kê tổng số lịch hoàn thành (COMPLETED), số buổi dịch vụ lẻ /
          liệu trình và doanh thu mang lại theo múi giờ Asia/Ho_Chi_Minh
        </p>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void loadReport();
            }}
            className="grid gap-3 sm:grid-cols-5 items-end"
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
                className="h-9 w-full rounded-md border border-input bg-background px-3 text-xs font-medium"
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
                  setCommissionRate(parseFloat(e.target.value || "0"))
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
        <div className="rounded-lg border border-rose-300 bg-rose-50 px-4 py-2.5 text-xs font-medium text-rose-700">
          {error}
        </div>
      )}

      {/* Summary Cards */}
      {report && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card>
            <CardContent className="flex items-center gap-4 p-5">
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
            <CardContent className="flex items-center gap-4 p-5">
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
            <CardContent className="flex items-center gap-4 p-5">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-100 text-amber-700">
                <Coins className="h-6 w-6" />
              </div>
              <div>
                <p className="text-xs font-medium text-muted-foreground">
                  Tổng doanh thu dịch vụ
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
        <CardContent className="p-0 overflow-x-auto">
          {loading ? (
            <p className="p-10 text-center text-xs text-muted-foreground">
              Đang tổng hợp dữ liệu...
            </p>
          ) : !report || report.staff.length === 0 ? (
            <p className="p-10 text-center text-xs text-muted-foreground">
              Không có dữ liệu Kỹ thuật viên trong khoảng thời gian này.
            </p>
          ) : (
            <table className="w-full text-left text-xs">
              <thead className="border-b border-border bg-muted/60 text-[11px] font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Kỹ thuật viên</th>
                  <th className="px-4 py-3 text-center">Lịch hoàn thành</th>
                  <th className="px-4 py-3 text-center">Tổng dịch vụ đã làm</th>
                  <th className="px-4 py-3 text-center">
                    Chi tiết (Lẻ / Thẻ liệu trình)
                  </th>
                  <th className="px-4 py-3 text-right">Doanh thu mang lại</th>
                  <th className="px-4 py-3 text-right">
                    Hoa hồng ({commissionRate}%)
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {report.staff.map((item) => {
                  const rev = parseFloat(item.total_revenue) || 0;
                  const commission = (rev * commissionRate) / 100;
                  return (
                    <tr key={item.staff_id} className="hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
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
                      <td className="px-4 py-3 text-center font-semibold">
                        {item.completed_bookings_count}
                      </td>
                      <td className="px-4 py-3 text-center font-bold text-foreground">
                        {item.completed_services_count}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="text-slate-700">
                          {item.single_services_count} lẻ
                        </span>{" "}
                        •{" "}
                        <span className="text-primary font-medium">
                          {item.package_sessions_count} buổi thẻ
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-bold text-foreground">
                        {formatCurrency(rev)}
                      </td>
                      <td className="px-4 py-3 text-right font-bold text-emerald-700">
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
