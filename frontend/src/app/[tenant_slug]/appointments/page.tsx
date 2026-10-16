"use client";

import * as React from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  CalendarCheck,
  Clock,
  RefreshCw,
  Ticket,
  XCircle,
} from "lucide-react";
import {
  cancelCustomerBooking,
  fetchCustomerBookings,
} from "@/lib/customer-api";
import type { BookingRecord } from "@/lib/types";
import {
  BOOKING_STATUS_META,
  cn,
  formatCurrency,
  formatDateTimeVN,
} from "@/lib/utils";
import { useCustomerTenant } from "@/components/customer/customer-context";
import { Button } from "@/components/ui/button";
import { Badge, Card, CardContent } from "@/components/ui/card";

function AppointmentsInner(): React.ReactElement | null {
  const searchParams = useSearchParams();
  const { slug, tenant, user, authLoading } = useCustomerTenant();

  const [scope, setScope] = React.useState<"upcoming" | "history">("upcoming");
  const [bookings, setBookings] = React.useState<BookingRecord[]>([]);
  const [loading, setLoading] = React.useState<boolean>(true);
  const [cancellingId, setCancellingId] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [justBooked, setJustBooked] = React.useState<boolean>(false);

  React.useEffect(() => {
    if (searchParams.get("booked") === "1") {
      setJustBooked(true);
    }
  }, [searchParams]);

  const loadBookings = React.useCallback(async (): Promise<void> => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCustomerBookings(slug, scope);
      setBookings(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Không thể tải danh sách lịch hẹn"
      );
    } finally {
      setLoading(false);
    }
  }, [slug, scope, user]);

  React.useEffect(() => {
    if (user) {
      void loadBookings();
    } else if (!authLoading) {
      setLoading(false);
    }
  }, [user, authLoading, loadBookings]);

  if (!tenant) return null;
  const themeColor = tenant.theme_color || "#be185d";

  const serviceById = React.useMemo(() => {
    const map = new Map<string, string>();
    for (const s of tenant.services) map.set(s.id, s.name);
    return map;
  }, [tenant.services]);

  const handleCancel = async (bookingId: string): Promise<void> => {
    setCancellingId(bookingId);
    setError(null);
    try {
      await cancelCustomerBooking(slug, bookingId);
      await loadBookings();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Không thể hủy lịch (Lưu ý: chỉ được hủy trước giờ hẹn tối thiểu 2 giờ)."
      );
    } finally {
      setCancellingId(null);
    }
  };

  if (!user && !authLoading) {
    return (
      <Card>
        <CardContent className="p-6 text-center space-y-3">
          <CalendarCheck
            className="mx-auto h-10 w-10"
            style={{ color: themeColor }}
          />
          <h2 className="text-base font-bold text-foreground">
            Đăng nhập để xem Lịch hẹn của bạn
          </h2>
          <p className="text-xs text-muted-foreground">
            Theo dõi trạng thái xác nhận lịch hẹn và chủ động hủy lịch khi bận.
          </p>
          <Link
            href={`/${slug}/login`}
            className="inline-flex h-9 items-center justify-center rounded-xl px-5 text-xs font-bold text-white shadow"
            style={{ backgroundColor: themeColor }}
          >
            Đăng nhập ngay
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-foreground">
            Lịch hẹn của tôi
          </h1>
          <p className="text-xs text-muted-foreground">
            Hủy lịch miễn phí trước giờ hẹn tối thiểu 2 tiếng
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => void loadBookings()}
        >
          <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
        </Button>
      </div>

      {justBooked && (
        <div className="rounded-xl border border-emerald-300 bg-emerald-50 px-3.5 py-2.5 text-xs font-semibold text-emerald-800">
          🎉 Đặt lịch thành công! Lễ tân đã nhận được thông báo lịch hẹn của
          bạn.
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-rose-300 bg-rose-50 px-3.5 py-2.5 text-xs font-medium text-rose-700">
          {error}
        </div>
      )}

      {/* Scope Tabs */}
      <div className="grid grid-cols-2 rounded-xl border border-border bg-muted p-1 text-xs font-semibold">
        <button
          type="button"
          onClick={() => setScope("upcoming")}
          className={cn(
            "rounded-lg py-2 transition",
            scope === "upcoming"
              ? "bg-card text-foreground shadow-xs"
              : "text-muted-foreground"
          )}
        >
          Sắp tới
        </button>
        <button
          type="button"
          onClick={() => setScope("history")}
          className={cn(
            "rounded-lg py-2 transition",
            scope === "history"
              ? "bg-card text-foreground shadow-xs"
              : "text-muted-foreground"
          )}
        >
          Lịch sử
        </button>
      </div>

      {loading ? (
        <Card>
          <CardContent className="p-8 text-center text-xs text-muted-foreground">
            Đang tải lịch hẹn...
          </CardContent>
        </Card>
      ) : bookings.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center space-y-3">
            <p className="text-xs text-muted-foreground">
              {scope === "upcoming"
                ? "Bạn chưa có lịch hẹn nào sắp diễn ra."
                : "Chưa có lịch sử làm đẹp nào."}
            </p>
            {scope === "upcoming" && (
              <Link
                href={`/${slug}/book`}
                className="inline-flex h-8 items-center justify-center rounded-lg px-4 text-xs font-semibold text-white"
                style={{ backgroundColor: themeColor }}
              >
                + Đặt lịch mới
              </Link>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {bookings.map((b) => {
            const meta = BOOKING_STATUS_META[b.status];
            const canCancel =
              b.status === "PENDING" || b.status === "CONFIRMED";
            const hoursUntilStart =
              (new Date(b.start_time).getTime() - Date.now()) /
              (1000 * 60 * 60);
            const withinCancelWindow = hoursUntilStart >= 2;

            return (
              <Card key={b.id} className="overflow-hidden">
                <CardContent
                  className={cn("p-4 space-y-2.5", meta.cardClass)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-900">
                        <Clock className="h-3.5 w-3.5 text-primary" />
                        {formatDateTimeVN(b.start_time)}
                      </p>
                      <p className="text-[11px] text-muted-foreground">
                        Tổng thời lượng: {b.total_duration_minutes} phút
                      </p>
                    </div>
                    <span
                      className={cn(
                        "rounded-full border px-2.5 py-0.5 text-[11px] font-semibold",
                        meta.badgeClass
                      )}
                    >
                      {meta.label}
                    </span>
                  </div>

                  <div className="space-y-1">
                    {b.items.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center justify-between rounded bg-white/80 px-2.5 py-1 text-xs border border-border/60"
                      >
                        <span className="font-medium text-foreground">
                          {serviceById.get(item.service_id) || "Dịch vụ Spa"} (
                          {item.duration_minutes}p)
                        </span>
                        {item.customer_package_id ? (
                          <Badge variant="default" className="gap-1">
                            <Ticket className="h-3 w-3" />
                            Trừ thẻ (0₫)
                          </Badge>
                        ) : (
                          <span className="font-semibold">
                            {formatCurrency(item.price)}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>

                  <div className="flex items-center justify-between border-t border-border/60 pt-2 text-xs">
                    <span className="font-bold text-foreground">
                      Tổng cộng: {formatCurrency(b.total_price)}
                    </span>

                    {canCancel && (
                      <Button
                        variant="destructive"
                        size="sm"
                        disabled={
                          cancellingId === b.id || !withinCancelWindow
                        }
                        onClick={() => void handleCancel(b.id)}
                        title={
                          withinCancelWindow
                            ? "Hủy lịch hẹn"
                            : "Chỉ được hủy trước giờ hẹn ít nhất 2 giờ"
                        }
                      >
                        <XCircle className="h-3.5 w-3.5" />
                        {cancellingId === b.id
                          ? "Đang hủy..."
                          : withinCancelWindow
                            ? "Hủy lịch"
                            : "Sát giờ (<2h)"}
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function CustomerAppointmentsPage(): React.ReactElement {
  return (
    <React.Suspense
      fallback={
        <div className="p-8 text-center text-xs text-muted-foreground">
          Đang tải lịch hẹn...
        </div>
      }
    >
      <AppointmentsInner />
    </React.Suspense>
  );
}
