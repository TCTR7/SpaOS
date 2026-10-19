"use client";

import * as React from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  CalendarCheck,
  CalendarClock,
  Clock,
  RefreshCw,
  Ticket,
  XCircle,
} from "lucide-react";
import {
  cancelCustomerBooking,
  rescheduleCustomerBooking,
  fetchCustomerAvailableSlots,
  fetchCustomerBookings,
} from "@/lib/customer-api";
import type { BookingRecord, SlotItem } from "@/lib/types";
import {
  BOOKING_STATUS_META,
  cn,
  formatCurrency,
  formatDateISOInVN,
  formatDateTimeVN,
  formatTimeVN,
} from "@/lib/utils";
import { useCustomerTenant } from "@/components/customer/customer-context";
import { Button } from "@/components/ui/button";
import { Badge, Card, CardContent } from "@/components/ui/card";
import { Input, Label, Textarea } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";

function AppointmentsInner(): React.ReactElement | null {
  const searchParams = useSearchParams();
  const { slug, tenant, user, authLoading } = useCustomerTenant();

  const [scope, setScope] = React.useState<"upcoming" | "history">("upcoming");
  const [bookings, setBookings] = React.useState<BookingRecord[]>([]);
  const [loading, setLoading] = React.useState<boolean>(true);
  const [cancellingId, setCancellingId] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [justBooked, setJustBooked] = React.useState<boolean>(false);
  const [successMsg, setSuccessMsg] = React.useState<string | null>(null);

  // Reschedule Modal State
  const [rescheduleTarget, setRescheduleTarget] =
    React.useState<BookingRecord | null>(null);
  const [rescheduleDate, setRescheduleDate] = React.useState<string>(() =>
    formatDateISOInVN()
  );
  const [rescheduleSlots, setRescheduleSlots] = React.useState<SlotItem[]>([]);
  const [rescheduleSlotsLoading, setRescheduleSlotsLoading] =
    React.useState<boolean>(false);
  const [rescheduleSlotStart, setRescheduleSlotStart] =
    React.useState<string>("");
  const [rescheduleKeepStaff, setRescheduleKeepStaff] =
    React.useState<boolean>(false);
  const [rescheduleNote, setRescheduleNote] = React.useState<string>("");
  const [rescheduleError, setRescheduleError] = React.useState<string | null>(
    null
  );
  const [rescheduleSubmitting, setRescheduleSubmitting] =
    React.useState<boolean>(false);

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

  // Load available slots when Reschedule Modal is open
  React.useEffect(() => {
    if (!rescheduleTarget || !rescheduleDate) {
      setRescheduleSlots([]);
      setRescheduleSlotStart("");
      return;
    }

    let cancelled = false;
    setRescheduleSlotsLoading(true);
    setRescheduleSlots([]);
    setRescheduleSlotStart("");

    void (async () => {
      try {
        const res = await fetchCustomerAvailableSlots(slug, {
          date: rescheduleDate,
          service_ids: rescheduleTarget.items.map((i) => i.service_id),
          staff_id:
            rescheduleKeepStaff && rescheduleTarget.staff_id
              ? rescheduleTarget.staff_id
              : null,
        });
        if (!cancelled) {
          setRescheduleSlots(res.slots);
          setRescheduleSlotStart(res.slots[0]?.start_time || "");
        }
      } catch {
        if (!cancelled) {
          setRescheduleSlots([]);
          setRescheduleSlotStart("");
        }
      } finally {
        if (!cancelled) setRescheduleSlotsLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [slug, rescheduleTarget, rescheduleDate, rescheduleKeepStaff]);

  const serviceById = React.useMemo(() => {
    const map = new Map<string, string>();
    for (const s of tenant?.services || []) map.set(s.id, s.name);
    return map;
  }, [tenant]);

  if (!tenant) return null;
  const themeColor = "var(--brand-color)";

  const handleCancel = async (bookingId: string): Promise<void> => {
    setCancellingId(bookingId);
    setError(null);
    setSuccessMsg(null);
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

  const openRescheduleModal = (booking: BookingRecord): void => {
    setRescheduleError(null);
    setRescheduleTarget(booking);
    setRescheduleDate(formatDateISOInVN(new Date(booking.start_time)));
    setRescheduleKeepStaff(false);
    setRescheduleNote(booking.note || "");
  };

  const handleConfirmReschedule = async (
    e: React.FormEvent<HTMLFormElement>
  ): Promise<void> => {
    e.preventDefault();
    if (!rescheduleTarget || !rescheduleSlotStart) {
      setRescheduleError("Vui lòng chọn khung giờ trống mới.");
      return;
    }

    setRescheduleSubmitting(true);
    setRescheduleError(null);
    try {
      await rescheduleCustomerBooking(slug, rescheduleTarget.id, {
        start_time: rescheduleSlotStart,
        staff_id: rescheduleKeepStaff ? rescheduleTarget.staff_id : null,
        note: rescheduleNote.trim() || null,
      });

      setRescheduleTarget(null);
      setSuccessMsg(
        `Đã dời lịch hẹn thành công sang ${formatDateTimeVN(rescheduleSlotStart)}!`
      );
      await loadBookings();
    } catch (err) {
      setRescheduleError(
        err instanceof Error
          ? err.message
          : "Không thể đổi lịch hẹn. Vui lòng thử lại hoặc chọn khung giờ khác."
      );
      await loadBookings();
    } finally {
      setRescheduleSubmitting(false);
    }
  };

  if (!user && !authLoading) {
    return (
      <Card>
        <CardContent className="p-6 text-center space-y-3">
          <CalendarCheck
            className="mx-auto h-10 w-10"
            style={{ color: "var(--brand-text)" }}
          />
          <h2 className="text-base font-bold text-foreground">
            Đăng nhập để xem Lịch hẹn của bạn
          </h2>
          <p className="text-xs text-muted-foreground">
            Theo dõi trạng thái xác nhận lịch hẹn, chủ động đổi ngày/giờ hoặc
            hủy lịch khi bận.
          </p>
          <Link
            href={`/${slug}/login`}
            className="inline-flex h-9 items-center justify-center rounded-xl px-5 text-xs font-bold text-white shadow"
            style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
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
            Đổi ngày/giờ hoặc hủy lịch miễn phí trước giờ hẹn tối thiểu 2 tiếng
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

      {successMsg && (
        <div className="rounded-xl border border-emerald-300 bg-emerald-50 px-3.5 py-2.5 text-xs font-semibold text-emerald-800">
          ✅ {successMsg}
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
                style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
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
            const canModify =
              b.status === "PENDING" || b.status === "CONFIRMED";
            const hoursUntilStart =
              (new Date(b.start_time).getTime() - Date.now()) /
              (1000 * 60 * 60);
            const withinModifyWindow = hoursUntilStart >= 2;

            return (
              <Card key={b.id} className="overflow-hidden">
                <CardContent className={cn("p-4 space-y-2.5", meta.cardClass)}>
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

                  {b.note && (
                    <p className="rounded bg-white/60 px-2.5 py-1 text-[11px] italic text-slate-600">
                      Ghi chú: {b.note}
                    </p>
                  )}

                  <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border/60 pt-2 text-xs">
                    <span className="font-bold text-foreground">
                      Tổng cộng: {formatCurrency(b.total_price)}
                    </span>

                    {canModify && (
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={
                            cancellingId === b.id || !withinModifyWindow
                          }
                          onClick={() => openRescheduleModal(b)}
                          title={
                            withinModifyWindow
                              ? "Đổi sang ngày hoặc khung giờ khác"
                              : "Chỉ được đổi lịch trước giờ hẹn ít nhất 2 giờ"
                          }
                        >
                          <CalendarClock className="h-3.5 w-3.5" />
                          Đổi ngày/giờ
                        </Button>

                        <Button
                          variant="destructive"
                          size="sm"
                          disabled={
                            cancellingId === b.id || !withinModifyWindow
                          }
                          onClick={() => void handleCancel(b.id)}
                          title={
                            withinModifyWindow
                              ? "Hủy lịch hẹn"
                              : "Chỉ được hủy trước giờ hẹn ít nhất 2 giờ"
                          }
                        >
                          <XCircle className="h-3.5 w-3.5" />
                          {cancellingId === b.id
                            ? "Đang hủy..."
                            : withinModifyWindow
                              ? "Hủy lịch"
                              : "Sát giờ (<2h)"}
                        </Button>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Reschedule Booking Modal */}
      <Modal
        open={Boolean(rescheduleTarget)}
        onClose={() => setRescheduleTarget(null)}
        title="Đổi ngày / giờ buổi hẹn"
        description="Chọn ngày và khung giờ trống mới. Buổi thẻ liệu trình (nếu có) sẽ được tự động chuyển sang lịch mới."
      >
        {rescheduleTarget && (
          <form
            onSubmit={(e) => void handleConfirmReschedule(e)}
            className="space-y-4"
          >
            {rescheduleError && (
              <div className="rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">
                {rescheduleError}
              </div>
            )}

            <div className="rounded-lg border border-border bg-muted/40 p-3 text-xs space-y-1">
              <p className="font-semibold text-foreground">
                Lịch hiện tại: {formatDateTimeVN(rescheduleTarget.start_time)}
              </p>
              <p className="text-muted-foreground">
                Dịch vụ:{" "}
                {rescheduleTarget.items
                  .map((i) => serviceById.get(i.service_id) || "Dịch vụ")
                  .join(", ")}
              </p>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="rescheduleDate">1. Chọn ngày hẹn mới</Label>
              <Input
                id="rescheduleDate"
                type="date"
                min={formatDateISOInVN()}
                value={rescheduleDate}
                onChange={(e) => setRescheduleDate(e.target.value)}
                required
              />
            </div>

            {rescheduleTarget.staff_id && (
              <label className="flex items-center gap-2 text-xs font-medium text-foreground cursor-pointer">
                <input
                  type="checkbox"
                  checked={rescheduleKeepStaff}
                  onChange={(e) => setRescheduleKeepStaff(e.target.checked)}
                  className="h-4 w-4 accent-primary"
                />
                <span>
                  Giữ nguyên Kỹ thuật viên cũ (Bỏ chọn để Spa tự sắp xếp KTV rảnh)
                </span>
              </label>
            )}

            <div className="space-y-2">
              <Label>2. Chọn khung giờ trống mới</Label>
              {rescheduleSlotsLoading ? (
                <p className="rounded-lg border border-border p-3 text-center text-xs text-muted-foreground">
                  Đang tìm khung giờ trống ngày {rescheduleDate}...
                </p>
              ) : rescheduleSlots.length === 0 ? (
                <p className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-center text-xs text-amber-800">
                  Không còn khung giờ trống nào trong ngày {rescheduleDate}. Vui
                  lòng chọn ngày khác.
                </p>
              ) : (
                <div className="max-h-44 overflow-y-auto grid grid-cols-3 gap-2 rounded-lg border border-border p-2">
                  {rescheduleSlots.map((slot) => {
                    const active = rescheduleSlotStart === slot.start_time;
                    return (
                      <button
                        key={slot.start_time}
                        type="button"
                        aria-pressed={active}
                        onClick={() => setRescheduleSlotStart(slot.start_time)}
                        className={cn(
                          "flex min-h-11 flex-col items-center rounded-lg border py-2 px-1.5 text-xs font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                          active
                            ? "border-transparent text-white shadow-xs"
                            : "border-border bg-card text-foreground hover:bg-muted/60"
                        )}
                        style={
                          active ? { backgroundColor: themeColor, color: "var(--brand-foreground)" } : undefined
                        }
                      >
                        <span>{formatTimeVN(slot.start_time)}</span>
                        <span
                          className={cn(
                            "text-[10px]",
                            active ? "text-inherit" : "text-muted-foreground"
                          )}
                        >
                          {slot.available_staff_ids.length} KTV trống
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="rescheduleNote">Ghi chú</Label>
              <Textarea
                id="rescheduleNote"
                value={rescheduleNote}
                onChange={(e) => setRescheduleNote(e.target.value)}
                placeholder="Ghi chú thêm cho buổi hẹn..."
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setRescheduleTarget(null)}
              >
                Đóng
              </Button>
              <Button
                type="submit"
                disabled={rescheduleSubmitting || rescheduleSlotsLoading || !rescheduleSlotStart}
                style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
              >
                {rescheduleSubmitting
                  ? "Đang dời lịch..."
                  : "Xác nhận đổi lịch"}
              </Button>
            </div>
          </form>
        )}
      </Modal>
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
