"use client";

import * as React from "react";
import { useRefreshOnReturn } from "@/lib/use-refresh-on-return";
import { customerAuthHref } from "@/lib/customer-return-to";
import { useAvailableSlots } from "@/lib/use-available-slots";
import { CalendarDownload } from "@/components/customer/calendar-download";
import { ReschedulePreview } from "@/components/reschedule-preview";
import { ApiError } from "@/lib/api";
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
  fetchCustomerBookingDetail,
  rescheduleCustomerBooking,
  fetchCustomerBookingPage,
} from "@/lib/customer-api";
import type { BookingRecord } from "@/lib/types";
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
  const listScope = JSON.stringify([slug, user?.id, scope]);
  const liveScope = React.useRef(listScope);
  liveScope.current = listScope;
  const listRequest = React.useRef(0);
  const [list, setList] = React.useState({ scope: "", rows: [] as BookingRecord[], loading: true, nextOffset: null as number | null, moreLoading: false, moreError: null as string | null });
  const listRef = React.useRef(list);
  listRef.current = list;
  const bookings = list.scope === listScope ? list.rows : [];
  const loading = list.scope !== listScope || list.loading;
  const [cancelTarget, setCancelTarget] = React.useState<BookingRecord | null>(null);
  const cancelFlight = React.useRef(false);
  const mutationIdentity = JSON.stringify([slug, user?.id]);
  const liveIdentity = React.useRef(mutationIdentity);
  liveIdentity.current = mutationIdentity;
  React.useEffect(() => { setCancelTarget(null); setRescheduleTarget(null); }, [mutationIdentity]);
  const [cancellingId, setCancellingId] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [justBooked, setJustBooked] = React.useState<boolean>(false);
  const [successMsg, setSuccessMsg] = React.useState<string | null>(null);

  const [lastUpdated, setLastUpdated] = React.useState(0);
  const [linkedBooking, setLinkedBooking] = React.useState<BookingRecord | null>(null);
  const [linkedError, setLinkedError] = React.useState("");
  React.useEffect(() => {
    const id = searchParams.get("booking_id");
    setLinkedBooking(null); setLinkedError("");
    if (!id || !user) return;
    let cancelled = false;
    void fetchCustomerBookingDetail(slug, id).then((booking) => { if (!cancelled) setLinkedBooking(booking); })
      .catch(() => { if (!cancelled) setLinkedError("Không mở được lịch hẹn này. Hãy làm mới danh sách hoặc liên hệ spa."); });
    return () => { cancelled = true; };
  }, [slug, user?.id, searchParams, lastUpdated]);

  // Reschedule Modal State
  const [rescheduleTarget, setRescheduleTarget] =
    React.useState<BookingRecord | null>(null);
  const [rescheduleDate, setRescheduleDate] = React.useState<string>(() =>
    formatDateISOInVN()
  );
  const [rescheduleKeepStaff, setRescheduleKeepStaff] =
    React.useState<boolean>(false);
  const [rescheduleNote, setRescheduleNote] = React.useState<string>("");
  const [rescheduleError, setRescheduleError] = React.useState<string | null>(
    null
  );
  const [rescheduleSubmitting, setRescheduleSubmitting] =
    React.useState<boolean>(false);
  const rescheduleFlight = React.useRef(false);

  React.useEffect(() => {
    if (searchParams.get("booked") === "1") {
      setJustBooked(true);
    }
  }, [searchParams]);

  const loadBookings = React.useCallback(async (append = false): Promise<void> => {
    if (!user || liveScope.current !== listScope) return;
    const previous = listRef.current;
    if (append && (previous.scope !== listScope || previous.moreLoading || previous.nextOffset === null)) return;
    const offset = append ? previous.nextOffset! : 0;
    const request = ++listRequest.current;
    if (append) setList((value) => ({ ...value, moreLoading: true, moreError: null }));
    else setList({ scope: listScope, rows: [], loading: true, nextOffset: null, moreLoading: false, moreError: null });
    setError(null);
    try {
      const data = await fetchCustomerBookingPage(slug, scope, offset);
      if (request !== listRequest.current || liveScope.current !== listScope) return;
      setLastUpdated(Date.now());
      setList((value) => ({ scope: listScope, rows: Array.from(new Map([
        ...(append && value.scope === listScope ? value.rows : []), ...data.items,
      ].map((booking) => [booking.id, booking])).values()), loading: false, nextOffset: data.nextOffset, moreLoading: false, moreError: null }));
    } catch (err) {
      if (request !== listRequest.current || liveScope.current !== listScope) return;
      if (append) {
        setList((value) => ({ ...value, moreLoading: false, moreError: err instanceof Error ? err.message : "Không tải thêm được lịch" }));
        return;
      }
      setList({ scope: listScope, rows: [], loading: false, nextOffset: null, moreLoading: false, moreError: null });
      setError(
        err instanceof Error ? err.message : "Không thể tải danh sách lịch hẹn"
      );
    }
  }, [slug, scope, user, listScope]);

  React.useEffect(() => {
    if (user) {
      void loadBookings();
    }
    return () => { listRequest.current += 1; };
  }, [user, authLoading, loadBookings]);
  useRefreshOnReturn(() => void loadBookings(), !cancellingId && !rescheduleTarget && !cancelTarget);
  const latestLoad = React.useRef(loadBookings);
  React.useLayoutEffect(() => { latestLoad.current = loadBookings; }, [loadBookings]);

  const { slots: rescheduleSlots, loading: rescheduleSlotsLoading, error: rescheduleSlotsError,
    retry: retryRescheduleSlots, selectedStart: rescheduleSlotStart, select: setRescheduleSlotStart } = useAvailableSlots({
    slug, date: rescheduleDate, serviceIds: rescheduleTarget?.items.map((item) => item.service_id) || [],
    staffId: rescheduleKeepStaff ? rescheduleTarget?.staff_id : null, enabled: Boolean(rescheduleTarget && user),
    bookingId: rescheduleTarget?.id, preferredStart: rescheduleTarget?.start_time,
  });

  const serviceById = React.useMemo(() => {
    const map = new Map<string, string>();
    for (const s of tenant?.services || []) map.set(s.id, s.name);
    return map;
  }, [tenant]);

  if (!tenant) return null;
  const themeColor = "var(--brand-color)";

  const handleCancel = async (bookingId: string): Promise<void> => {
    if (cancelFlight.current) return;
    cancelFlight.current = true;
    const identity = mutationIdentity;
    setCancellingId(bookingId);
    setError(null);
    setSuccessMsg(null);
    try {
      const updated = await cancelCustomerBooking(slug, bookingId);
      if (liveIdentity.current !== identity) return;
      setCancelTarget(null);
      setLinkedBooking((previous) => previous?.id === updated.id ? updated : previous);
      await latestLoad.current();
      setSuccessMsg("Đã hủy lịch hẹn.");
    } catch (err) {
      if (liveIdentity.current !== identity) return;
      setCancelTarget(null);
      setError(
        err instanceof Error
          ? err.message
          : "Không thể hủy lịch (Lưu ý: chỉ được hủy trước giờ hẹn tối thiểu 2 giờ)."
      );
    } finally {
      cancelFlight.current = false;
      setCancellingId(null);
    }
  };

  const openRescheduleModal = (booking: BookingRecord): void => {
    setRescheduleError(null);
    setRescheduleTarget(booking);
    setRescheduleDate(formatDateISOInVN(new Date(booking.start_time)));
    setRescheduleKeepStaff(true);
    setRescheduleNote(booking.note || "");
  };

  const handleConfirmReschedule = async (
    e: React.FormEvent<HTMLFormElement>
  ): Promise<void> => {
    e.preventDefault();
    if (rescheduleFlight.current) return;
    if (!rescheduleTarget || !rescheduleSlotStart) {
      setRescheduleError("Vui lòng chọn khung giờ trống mới.");
      return;
    }

    rescheduleFlight.current = true;
    setRescheduleSubmitting(true);
    setRescheduleError(null);
    try {
      const updated = await rescheduleCustomerBooking(slug, rescheduleTarget.id, {
        start_time: rescheduleSlotStart,
        staff_id: rescheduleKeepStaff ? rescheduleTarget.staff_id : null,
        note: rescheduleNote.trim() || null,
      });

      setRescheduleTarget(null);
      setLinkedBooking((previous) => previous?.id === updated.id ? updated : previous);
      setSuccessMsg(
        `Đã dời lịch hẹn thành công sang ${formatDateTimeVN(rescheduleSlotStart)}!`
      );
      await latestLoad.current();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) retryRescheduleSlots();
      setRescheduleError(
        err instanceof Error
          ? err.message
          : "Không thể đổi lịch hẹn. Vui lòng thử lại hoặc chọn khung giờ khác."
      );
      await latestLoad.current();
    } finally {
      rescheduleFlight.current = false;
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
            href={customerAuthHref(slug, "login", `/${slug}/appointments`)}
            className="inline-flex min-h-11 items-center justify-center rounded-xl px-5 text-xs font-bold text-white shadow"
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
            "min-h-11 rounded-lg py-2 text-sm transition",
            scope === "upcoming"
              ? "neu-surface bg-card text-foreground shadow-sm"
              : "text-muted-foreground"
          )}
        >
          Sắp tới
        </button>
        <button
          type="button"
          onClick={() => setScope("history")}
          className={cn(
            "min-h-11 rounded-lg py-2 text-sm transition",
            scope === "history"
              ? "neu-surface bg-card text-foreground shadow-sm"
              : "text-muted-foreground"
          )}
        >
          Lịch sử
        </button>
      </div>

      {linkedError && <p role="alert" className="rounded-lg border p-3 text-sm">{linkedError}</p>}
      {linkedBooking && <section aria-label="Lịch hẹn được mở" className="space-y-2 rounded-xl border-2 border-primary neu-surface bg-card p-4">
        <h2 className="font-bold">Lịch hẹn của bạn</h2>
        <p>{formatDateTimeVN(linkedBooking.start_time)} • {BOOKING_STATUS_META[(bookings.find((item) => item.id === linkedBooking.id) || linkedBooking).status].label}</p>
        <p className="text-sm">{linkedBooking.items.map((item) => item.service_name || serviceById.get(item.service_id) || "Dịch vụ").join(", ")}</p>
        <p className="text-sm">Nhân viên: {linkedBooking.staff_name || "Spa tự sắp xếp"}</p>
        <CalendarDownload booking={bookings.find((item) => item.id === linkedBooking.id) || linkedBooking} />
        <p className="text-xs text-muted-foreground">Xem và quản lý lịch trong danh sách Sắp tới hoặc Lịch sử bên dưới.</p>
      </section>}
      {!loading && <div className="space-y-2 text-xs" aria-live="polite">
        <p>{lastUpdated > 0 && !error ? "Cập nhật lúc " + new Date(lastUpdated).toLocaleTimeString("vi-VN", {hour: "2-digit", minute: "2-digit"}) + " · " : ""}Đã tải {bookings.length} lịch{list.nextOffset !== null ? "; còn dữ liệu" : ""}.</p>
        {list.nextOffset !== null && <Button variant="outline" disabled={list.moreLoading} onClick={() => void loadBookings(true)}>{list.moreLoading ? "Đang tải thêm..." : "Tải thêm lịch"}</Button>}
        {list.moreError && <p role="alert">{list.moreError} — Nhấn tải thêm để thử lại.</p>}
      </div>}
      {loading ? (
        <Card>
          <CardContent className="p-8 text-center text-xs text-muted-foreground">
            Đang tải lịch hẹn...
          </CardContent>
        </Card>
      ) : error && bookings.length === 0 ? <div className="space-y-2 rounded-xl border p-4"><p>Chưa kiểm tra được danh sách lịch. Thử tải lại trước khi đặt lịch mới.</p><Button variant="outline" onClick={() => void loadBookings()}>Thử tải lại lịch hẹn</Button></div> : bookings.length === 0 ? (
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
                className="inline-flex min-h-11 items-center justify-center rounded-lg px-4 text-xs font-semibold text-white"
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
              <Card key={b.id} data-testid={`customer-booking-${b.id}`} className="overflow-hidden">
                <CardContent className={cn("p-4 space-y-2.5", meta.cardClass)}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-900">
                        <Clock className="h-3.5 w-3.5 text-primary" />
                        {formatDateTimeVN(b.start_time)}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Tổng thời lượng: {b.total_duration_minutes} phút
                      </p>
                      <p className="break-words text-xs">KTV: {b.staff_name || (b.staff_id ? "Chưa có tên KTV" : "Spa tự sắp xếp")}</p>
                    </div>
                    <span
                      className={cn(
                        "rounded-full border px-2.5 py-0.5 text-xs font-semibold",
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
                        className="flex min-w-0 items-center justify-between gap-2 rounded bg-white/80 px-2.5 py-1 text-xs border border-border/60"
                      >
                        <span className="min-w-0 break-words font-medium text-foreground">
                          {item.service_name || serviceById.get(item.service_id) || "Chưa có tên dịch vụ"} (
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
                    <p className="rounded bg-white/60 px-2.5 py-1 text-xs italic text-slate-600">
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
                          onClick={() => setCancelTarget(b)}
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

      <Modal open={Boolean(cancelTarget)} onClose={() => setCancelTarget(null)}
        title="Hủy lịch hẹn này?" pending={Boolean(cancellingId)} historyGuard>
        {cancelTarget && <div className="space-y-4">
          <p className="font-semibold">{formatDateTimeVN(cancelTarget.start_time)}</p>
          <p className="text-sm">{cancelTarget.items.map((item) => item.service_name || serviceById.get(item.service_id) || "Dịch vụ").join(", ")}</p>
          <p className="text-sm text-muted-foreground">Sau khi hủy, khung giờ này có thể được người khác đặt. Khoản tiền đã thu (nếu có) cần liên hệ spa để đối chiếu.</p>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" disabled={Boolean(cancellingId)} onClick={() => setCancelTarget(null)}>Giữ lịch hẹn</Button>
            <Button variant="destructive" disabled={Boolean(cancellingId)} onClick={() => void handleCancel(cancelTarget.id)}>{cancellingId ? "Đang hủy..." : "Xác nhận hủy lịch"}</Button>
          </div>
        </div>}
      </Modal>
      {/* Reschedule Booking Modal */}
      <Modal
        open={Boolean(rescheduleTarget)}
        onClose={() => setRescheduleTarget(null)}
        title="Đổi ngày / giờ buổi hẹn"
        pending={rescheduleSubmitting}
        dirty={Boolean(rescheduleTarget && (rescheduleNote !== (rescheduleTarget.note || "") || rescheduleDate !== formatDateISOInVN(new Date(rescheduleTarget.start_time)) || !rescheduleKeepStaff || (rescheduleSlotStart && new Date(rescheduleSlotStart).getTime() !== new Date(rescheduleTarget.start_time).getTime())))}
        description="Chọn ngày và khung giờ trống mới. Buổi thẻ liệu trình (nếu có) sẽ được tự động chuyển sang lịch mới."
      >
        {rescheduleTarget && (
          <form
            onSubmit={(e) => void handleConfirmReschedule(e)}
            className="space-y-4"
          >
            <fieldset disabled={rescheduleSubmitting} className="space-y-4">
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
              <ReschedulePreview booking={rescheduleTarget} start={rescheduleSlotStart}
                staffName={rescheduleKeepStaff ? rescheduleTarget.staff_name || "KTV hiện tại" : "Spa tự sắp xếp"} />
              {rescheduleSlotsLoading ? (
                <p className="rounded-lg border border-border p-3 text-center text-xs text-muted-foreground">
                  Đang tìm khung giờ trống ngày {rescheduleDate}...
                </p>
              ) : rescheduleSlotsError ? (
                <div role="alert" className="space-y-2 rounded-lg border p-3 text-center text-sm">
                  <p>{rescheduleSlotsError}</p><Button type="button" variant="outline" onClick={retryRescheduleSlots}>Thử lại khung giờ</Button>
                </div>
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
                            ? "border-transparent text-white shadow-sm"
                            : "border-border neu-surface bg-card text-foreground hover:bg-muted/60"
                        )}
                        style={
                          active ? { backgroundColor: themeColor, color: "var(--brand-foreground)" } : undefined
                        }
                      >
                        <span>{formatTimeVN(slot.start_time)}</span>
                        <span
                          className={cn(
                            "text-xs",
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
                type="submit"
                disabled={rescheduleSubmitting || rescheduleSlotsLoading || !rescheduleSlotStart}
                style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
              >
                {rescheduleSubmitting
                  ? "Đang dời lịch..."
                  : "Xác nhận đổi lịch"}
              </Button>
            </div>
          </fieldset>
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
