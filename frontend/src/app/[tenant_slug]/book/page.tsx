"use client";

import * as React from "react";
import { GuestBooking } from "@/components/customer/guest-booking";
import { StaffAvatar } from "@/components/admin/staff-avatar";
import { useCustomerBookingRequest } from "@/lib/use-customer-booking-request";
import { useNearestAvailableDay } from "@/lib/use-nearest-available-day";
import { useAvailableSlots } from "@/lib/use-available-slots";
import { ApiError } from "@/lib/api";
import { useRouter, useSearchParams } from "@/lib/spa-navigation";
import { Calendar, Check, ChevronLeft, ChevronRight, Clock, Sparkles } from "lucide-react";
import { fetchPublicTenant } from "@/lib/customer-api";
import type { ServiceItem } from "@/lib/types";
import { addDaysISO, cn, formatCurrency, formatDateISOInVN, formatDateTimeVN, formatTimeVN } from "@/lib/utils";
import { useCustomerTenant } from "@/components/customer/customer-context";
import { Button } from "@/components/ui/button";
import { Badge, Card, CardContent } from "@/components/ui/card";
import { Input, Label, Textarea } from "@/components/ui/input";

interface StaffChoice { id: string; full_name: string; photo_url?: string | null }

function BookingWizardInner(): React.ReactElement | null {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { slug, tenant, user } = useCustomerTenant();

  const [step, setStep] = React.useState<1 | 2 | 3>(1);
  const bookingRequest = useCustomerBookingRequest(slug, user?.id);
  const bookingFlight = React.useRef(false);
  const [selectedIds, setSelectedIds] = React.useState<string[]>([]);
  const [selectedDate, setSelectedDate] = React.useState<string>(() => formatDateISOInVN());
  const [selectedStaffId, setSelectedStaffId] = React.useState<string | null>(null);
  const [slotsOpen, setSlotsOpen] = React.useState(true);
  const [staffPickerOpen, setStaffPickerOpen] = React.useState(false);
  const { slots: availableSlots, loading: slotsLoading, error: slotsError, retry: retrySlots,
    selectedStart: selectedSlotStart, select: setSelectedSlotStart } = useAvailableSlots({
    slug, date: selectedDate, serviceIds: selectedIds,
    staffId: selectedStaffId, enabled: Boolean(tenant) && selectedDate >= formatDateISOInVN(), autoSelect: false,
  });
  const nearest = useNearestAvailableDay({ slug, date: selectedDate,
    serviceIds: selectedIds, staffId: selectedStaffId,
    enabled: Boolean(tenant) && step === 2 && !slotsLoading && selectedIds.length > 0,
    onFound: setSelectedDate });
  const [note, setNote] = React.useState<string>("");
  const [submitting, setSubmitting] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string | null>(null);

  // Consume a valid deep link once; background tenant refresh must not reset the draft.
  const appliedLink = React.useRef("");
  React.useEffect(() => {
    if (!tenant) return;
    const serviceId = searchParams.get("service_id");
    if (!serviceId || !tenant.services.some((service) => service.id === serviceId)) return;
    const key = JSON.stringify([slug, serviceId]);
    if (appliedLink.current === key) return;
    appliedLink.current = key;
    setSelectedIds([serviceId]);
    setStep(2);
  }, [tenant, slug, searchParams]);

  const [staffDirectory, setStaffDirectory] = React.useState<StaffChoice[]>([]);
  const [staffAttempt, setStaffAttempt] = React.useState(0);
  const [staffLoadError, setStaffLoadError] = React.useState(false);
  React.useEffect(() => {
    let alive = true;
    setStaffDirectory([]); setStaffLoadError(false); setSelectedStaffId(null);
    void fetchPublicTenant(slug, selectedDate)
      .then((value) => { if (alive) setStaffDirectory(value.staff || []); })
      .catch(() => { if (alive) setStaffLoadError(true); });
    return () => { alive = false; };
  }, [slug, selectedDate, staffAttempt]);

  // A chosen time is collapsed so the page stays short; reopen when it is cleared.
  React.useEffect(() => { setSlotsOpen(!selectedSlotStart); }, [selectedSlotStart]);

  const serviceById = React.useMemo(() => {
    const map = new Map<string, ServiceItem>();
    for (const s of tenant?.services || []) map.set(s.id, s);
    return map;
  }, [tenant]);

  const totalDuration = selectedIds.reduce((acc, id) => acc + (serviceById.get(id)?.duration_minutes ?? 0), 0);
  const totalPrice = selectedIds.reduce((acc, id) => acc + parseFloat(serviceById.get(id)?.price ?? "0"), 0);

  if (!tenant) return null;
  const themeColor = "var(--brand-color)";
  const lines = selectedIds.map((id) => ({ service_id: id, customer_package_id: null }));
  const selectedStaff = staffDirectory.find((person) => person.id === selectedStaffId);

  const toggleService = (serviceId: string): void => {
    setSelectedIds((prev) => {
      if (prev.includes(serviceId)) return prev.filter((id) => id !== serviceId);
      return prev.length >= 10 ? prev : [...prev, serviceId];
    });
    setSelectedSlotStart("");
  };

  const handleConfirmBooking = async (): Promise<void> => {
    if (bookingFlight.current) return;
    if (!user) { setError("Vui lòng nhập họ tên và số điện thoại để gửi yêu cầu."); return; }
    if (selectedIds.length === 0 || !selectedSlotStart) {
      setError("Vui lòng chọn đầy đủ dịch vụ và khung giờ hẹn.");
      return;
    }
    bookingFlight.current = true;
    setSubmitting(true);
    setError(null);
    try {
      const created = await bookingRequest.submit({
        start_time: selectedSlotStart,
        staff_id: selectedStaffId,
        note: note.trim() || null,
        items: lines,
      });
      if (created) router.push(`/${slug}/appointments?booked=1&booking_id=${encodeURIComponent(created.id)}`);
      else { bookingFlight.current = false; setSubmitting(false); }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể hoàn tất đặt lịch, vui lòng chọn khung giờ khác.");
      if (err instanceof ApiError && err.status === 409) { setStep(2); retrySlots(); }
      bookingFlight.current = false;
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      {(bookingRequest.uncertain || bookingRequest.message) && (
        <section aria-label="Kiểm tra kết quả đặt lịch" className="space-y-2 rounded-xl border p-4">
          <p role="status">{bookingRequest.message || "Có một yêu cầu đặt lịch cần kiểm tra kết quả."}</p>
          {bookingRequest.uncertain && (
            <div className="flex flex-wrap gap-2">
              <Button disabled={bookingRequest.busy} onClick={async () => { const booking = await bookingRequest.check(); if (booking) router.push("/" + slug + "/appointments?booking_id=" + booking.id); }}>Kiểm tra lịch đã đặt</Button>
              {bookingRequest.canRetry && (
                <Button variant="outline" disabled={bookingRequest.busy} onClick={async () => { try { const booking = await bookingRequest.retry(); if (booking) router.push("/" + slug + "/appointments?booking_id=" + booking.id); } catch { /* recovery state remains visible */ } }}>Gửi lại đúng yêu cầu này</Button>
              )}
            </div>
          )}
        </section>
      )}
      <fieldset disabled={bookingRequest.uncertain || bookingRequest.busy || submitting} className="m-0 min-w-0 space-y-4 border-0 p-0">
        <div className="rounded-2xl border border-border neu-surface bg-card p-3.5 shadow-sm">
          <nav aria-label="Các bước đặt lịch" className="grid grid-cols-3 gap-1 text-xs font-semibold">
            {[
              { num: 1, label: "1. Dịch vụ" },
              { num: 2, label: "2. Ngày giờ / KTV" },
              { num: 3, label: "3. Xác nhận" },
            ].map((s) => {
              const isCurrent = step === s.num;
              const isDone = step > s.num;
              return (
                <button
                  key={s.num}
                  type="button"
                  aria-current={isCurrent ? "step" : undefined}
                  disabled={submitting || (s.num > 1 && selectedIds.length === 0) || (s.num === 3 && !selectedSlotStart)}
                  onClick={() => setStep(s.num as 1 | 2 | 3)}
                  className={cn(
                    "flex min-h-11 min-w-0 items-center justify-center gap-1 rounded-lg px-1 py-2 transition disabled:opacity-50 [overflow-wrap:anywhere]",
                    isCurrent ? "font-bold text-white shadow-sm" : isDone ? "font-semibold text-emerald-700" : "text-muted-foreground"
                  )}
                  style={isCurrent ? { backgroundColor: themeColor, color: "var(--brand-foreground)" } : undefined}
                >
                  {isDone && <Check className="h-3.5 w-3.5" />}
                  <span>{s.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {error && (
          <div role="alert" className="rounded-xl border border-rose-300 bg-rose-50 px-3.5 py-2.5 text-sm font-medium text-rose-700 [overflow-wrap:anywhere]">
            {error}
          </div>
        )}

        {step === 1 && (
          <div className="space-y-2.5">
            <h2 className="text-sm font-bold text-foreground">Chọn 1 hoặc nhiều dịch vụ ({selectedIds.length} đã chọn)</h2>
            {tenant.services.length === 0 && <p className="rounded-lg border p-3 text-sm">Spa chưa có dịch vụ nhận lịch trực tuyến. Hãy liên hệ chi nhánh để được hỗ trợ.</p>}
            {tenant.services.map((svc) => {
              const checked = selectedIds.includes(svc.id);
              return (
                <button
                  type="button"
                  aria-pressed={checked}
                  key={svc.id}
                  onClick={() => toggleService(svc.id)}
                  className={cn(
                    "flex w-full min-w-0 cursor-pointer items-center justify-between gap-3 rounded-xl border neu-surface bg-card p-3.5 text-left transition [overflow-wrap:anywhere]",
                    checked ? "border-primary shadow-sm ring-2 ring-primary" : "border-border hover:bg-muted/40"
                  )}
                >
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-sm font-bold text-foreground">{svc.name}</span>
                      {svc.is_package && <Badge variant="default">Liệu trình {svc.total_sessions} buổi</Badge>}
                    </div>
                    {svc.description && <p className="line-clamp-2 text-xs text-muted-foreground">{svc.description}</p>}
                    <p className="text-xs font-medium text-slate-600">
                      ⏱ {svc.duration_minutes} phút{svc.is_package ? "/buổi" : ""} •{" "}
                      <strong style={{ color: "var(--brand-text)" }}>{formatCurrency(svc.price)}</strong>
                    </p>
                    {svc.is_package && <p className="text-xs text-muted-foreground">Bạn đặt lịch cho buổi đầu tiên.</p>}
                  </div>
                  <div
                    className={cn("flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-bold", checked ? "border-transparent text-white" : "border-slate-300 text-transparent")}
                    style={checked ? { backgroundColor: themeColor, color: "var(--brand-foreground)" } : undefined}
                  >
                    ✓
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {step === 2 && (
          <div className="space-y-3">
            <div className="flex min-w-0 flex-wrap items-center justify-between gap-2 rounded-lg border p-3 text-sm [overflow-wrap:anywhere]">
              <span className="min-w-0 max-w-full">{selectedIds.map((id) => serviceById.get(id)?.name || "Dịch vụ").join(", ")} • {totalDuration} phút</span>
              <Button type="button" variant="outline" onClick={() => setStep(1)}>Đổi dịch vụ</Button>
            </div>
            <Card>
              <CardContent className="space-y-3 p-4">
                <Label htmlFor="wizDate" className="flex items-center gap-1.5">
                  <Calendar className="h-4 w-4 text-primary" />
                  Chọn ngày hẹn
                </Label>
                <div className="flex flex-wrap gap-2">
                  <Button type="button" variant="outline" onClick={() => setSelectedDate(formatDateISOInVN())}>Hôm nay</Button>
                  <Button type="button" variant="outline" onClick={() => setSelectedDate(addDaysISO(formatDateISOInVN(), 1))}>Ngày mai</Button>
                </div>
                <div className="flex items-center gap-2">
                  <Button type="button" variant="outline" size="icon" aria-label="Ngày trước" disabled={selectedDate <= formatDateISOInVN()} onClick={() => setSelectedDate(addDaysISO(selectedDate, -1))}>
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <Input id="wizDate" type="date" min={formatDateISOInVN()} value={selectedDate}
                    onChange={(e) => { if (e.target.value >= formatDateISOInVN()) setSelectedDate(e.target.value); }} className="min-w-0 flex-1" />
                  <Button type="button" variant="outline" size="icon" aria-label="Ngày tiếp theo" onClick={() => setSelectedDate(addDaysISO(selectedDate, 1))}>
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>

            <details className="rounded-xl border p-3" open={slotsOpen} onToggle={(event) => setSlotsOpen(event.currentTarget.open)}>
              <summary className="min-h-11 cursor-pointer py-3 text-sm font-semibold">
                {selectedSlotStart ? "Giờ hẹn: " + formatTimeVN(selectedSlotStart) : `Khung giờ còn trống (${availableSlots.length})`}
              </summary>
              {slotsLoading ? (
                <p className="p-6 text-center text-xs text-muted-foreground">Đang kiểm tra lịch trống...</p>
              ) : slotsError ? (
                <div role="alert" className="space-y-2 rounded-lg border p-3 text-center text-sm">
                  <p>{slotsError}</p>
                  <Button type="button" variant="outline" onClick={retrySlots}>Thử lại khung giờ</Button>
                </div>
              ) : availableSlots.length === 0 ? (
                <p className="rounded-xl bg-amber-50 p-6 text-center text-xs text-amber-800">
                  Rất tiếc, ngày {selectedDate} không còn khung giờ trống nào đủ {totalDuration} phút. Hãy tìm ngày khác hoặc đổi nhân viên.
                </p>
              ) : (
                <div className="grid grid-cols-3 gap-2 pb-1">
                  {availableSlots.map((slot) => {
                    const isSelected = selectedSlotStart === slot.start_time;
                    return (
                      <button
                        key={slot.start_time}
                        type="button"
                        aria-pressed={isSelected}
                        onClick={() => setSelectedSlotStart(slot.start_time)}
                        className={cn(
                          "flex min-h-11 flex-col items-center rounded-xl border px-2 py-2.5 text-xs font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                          isSelected ? "border-transparent text-white shadow" : "border-border neu-surface bg-card text-foreground hover:bg-muted/60"
                        )}
                        style={isSelected ? { backgroundColor: themeColor, color: "var(--brand-foreground)" } : undefined}
                      >
                        <span className="text-sm font-bold">{formatTimeVN(slot.start_time)}</span>
                      </button>
                    );
                  })}
                </div>
              )}
              <div className="space-y-2 pt-2">
                <Button type="button" variant="outline" className="h-auto min-h-11 max-w-full whitespace-normal text-left" disabled={nearest.searching || slotsLoading} onClick={() => void nearest.search()}>
                  {nearest.searching ? "Đang tìm ngày còn chỗ..." : "Tìm ngày còn chỗ trong 7 ngày tiếp theo"}
                </Button>
                {nearest.message && <p role="status" className="text-sm text-muted-foreground">{nearest.message}</p>}
              </div>
            </details>

            <details className="rounded-xl border p-3" open={staffPickerOpen} onToggle={(event) => setStaffPickerOpen(event.currentTarget.open)}>
              <summary className="min-h-11 cursor-pointer py-3 text-sm font-semibold">
                {selectedStaffId ? "Nhân viên: " + (selectedStaff?.full_name || "Đã chọn") : "Spa tự sắp xếp · Chọn nhân viên quen"}
              </summary>
              <div className="space-y-2">
                <button
                  type="button"
                  aria-pressed={selectedStaffId === null}
                  onClick={() => setSelectedStaffId(null)}
                  className={cn("flex w-full min-w-0 items-center justify-between gap-2 rounded-xl border neu-surface bg-card p-3.5 text-left transition", selectedStaffId === null ? "border-primary ring-2 ring-primary" : "border-border")}
                >
                  <span className="flex min-w-0 items-center gap-3">
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-white" style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}>
                      <Sparkles className="h-5 w-5" />
                    </span>
                    <span>
                      <span className="block text-sm font-bold text-foreground">Spa tự sắp xếp</span>
                      <span className="block text-xs text-muted-foreground">Spa chọn nhân viên phù hợp với giờ bạn đặt</span>
                    </span>
                  </span>
                  {selectedStaffId === null && <Badge variant="success">Đang chọn</Badge>}
                </button>
                {staffLoadError && <p role="alert" className="text-sm">Chưa tải được nhân viên theo ngày. <button type="button" className="underline" onClick={() => setStaffAttempt((v) => v + 1)}>Thử lại</button></p>}
                {staffDirectory.map((person) => {
                  const active = selectedStaffId === person.id;
                  return (
                    <button
                      type="button"
                      aria-pressed={active}
                      key={person.id}
                      onClick={() => { setSelectedStaffId(person.id); setSelectedSlotStart(""); }}
                      className={cn("flex w-full min-w-0 items-center justify-between gap-2 rounded-xl border neu-surface bg-card p-3 text-left transition", active ? "border-primary ring-2 ring-primary" : "border-border")}
                    >
                      <span className="flex min-w-0 items-center gap-3">
                        <StaffAvatar name={person.full_name} src={person.photo_url} className="h-10 w-10 text-base" />
                        <span className="min-w-0 text-sm font-semibold text-foreground [overflow-wrap:anywhere]">{person.full_name}</span>
                      </span>
                      {active && <Badge variant="success">Đang chọn</Badge>}
                    </button>
                  );
                })}
              </div>
            </details>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <Card>
              <CardContent className="space-y-3 p-4 text-sm [overflow-wrap:anywhere] [&>div]:flex [&>div]:min-w-0 [&>div]:flex-wrap [&>div]:gap-3">
                <h3 className="border-b border-border pb-2 text-sm font-bold text-foreground">Xác nhận lịch hẹn</h3>
                <div className="justify-between"><span className="text-muted-foreground">Cơ sở Spa:</span><strong>{tenant.name}</strong></div>
                <div className="justify-between"><span className="text-muted-foreground">Thời gian hẹn:</span><strong>{selectedSlotStart ? formatDateTimeVN(selectedSlotStart) : "Chưa chọn giờ"}</strong></div>
                <div className="justify-between"><span className="text-muted-foreground">Kỹ thuật viên:</span><strong>{selectedStaffId ? selectedStaff?.full_name || "Chưa có tên KTV" : "Spa tự sắp xếp"}</strong></div>
                <div className="space-y-1.5 border-t border-border pt-2">
                  {selectedIds.map((id) => {
                    const svc = serviceById.get(id);
                    return (
                      <div key={id} className="min-w-0 flex-wrap items-center justify-between gap-2 rounded bg-muted/50 px-2.5 py-1.5">
                        <span>{svc?.name || "Dịch vụ"} ({svc?.duration_minutes}p){svc?.is_package ? " · buổi đầu tiên" : ""}</span>
                        <span className="font-bold">{formatCurrency(svc?.price || 0)}</span>
                      </div>
                    );
                  })}
                </div>
                <div className="items-center justify-between border-t border-border pt-2.5">
                  <span className="font-bold">Tổng dự kiến ({totalDuration} phút):</span>
                  <span className="text-base font-extrabold" style={{ color: "var(--brand-text)" }}>{formatCurrency(totalPrice)}</span>
                </div>
                <div className="block space-y-1 pt-2">
                  <Label htmlFor="wizNote">Ghi chú cho Lễ tân / KTV</Label>
                  <Textarea id="wizNote" placeholder="VD: Mình muốn phòng yên tĩnh, da đang hơi khô..." value={note} disabled={submitting} onChange={(e) => setNote(e.target.value)} />
                </div>
              </CardContent>
            </Card>
            {!user && <GuestBooking slug={slug} start={selectedSlotStart} services={selectedIds} staff={selectedStaffId} note={note} />}
          </div>
        )}

        <div className="space-y-2.5 rounded-2xl border border-border neu-surface bg-card p-3.5 shadow-md">
          <div className="flex min-w-0 flex-wrap items-center justify-between gap-2 text-xs">
            <span className="inline-flex items-center gap-1 text-muted-foreground">
              <Clock className="h-3.5 w-3.5" />
              Tổng thời gian: <strong className="text-foreground">{totalDuration} phút</strong>
            </span>
            <span className="font-bold text-foreground">
              Tạm tính: <strong className="text-sm" style={{ color: "var(--brand-text)" }}>{formatCurrency(totalPrice)}</strong>
            </span>
          </div>
          <div className="flex items-center justify-between gap-2">
            {step > 1 ? (
              <Button type="button" variant="outline" size="sm" disabled={submitting} onClick={() => setStep((s) => (s - 1) as 1 | 2 | 3)}>
                <ChevronLeft className="h-4 w-4" />
                Quay lại
              </Button>
            ) : <div />}
            {step < 3 ? (
              <Button
                type="button"
                size="sm"
                disabled={(step === 1 && selectedIds.length === 0) || (step === 2 && (slotsLoading || !selectedSlotStart))}
                style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
                onClick={() => setStep((s) => (s + 1) as 1 | 2 | 3)}
              >
                Tiếp tục
                <ChevronRight className="h-4 w-4" />
              </Button>
            ) : (
              <Button
                type={user ? "button" : "submit"}
                form={user ? undefined : "guest-request-form"}
                size="sm"
                disabled={submitting || slotsLoading || !selectedSlotStart || (!!user && !bookingRequest.ready)}
                style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
                onClick={user ? () => void handleConfirmBooking() : undefined}
              >
                {submitting ? "Đang gửi lịch hẹn..." : user ? "Xác nhận Đặt lịch" : "Gửi yêu cầu đặt lịch"}
              </Button>
            )}
          </div>
        </div>
      </fieldset>
    </div>
  );
}

export default function CustomerBookingWizardPage(): React.ReactElement {
  return (
    <React.Suspense fallback={<div className="p-8 text-center text-xs text-muted-foreground">Đang khởi tạo luồng đặt lịch...</div>}>
      <BookingWizardInner />
    </React.Suspense>
  );
}
