"use client";

import * as React from "react";
import { useCustomerBookingRequest } from "@/lib/use-customer-booking-request";
import { PasswordInput } from "@/components/ui/password-input";
import { useNearestAvailableDay } from "@/lib/use-nearest-available-day";
import { useAvailableSlots } from "@/lib/use-available-slots";
import { ApiError } from "@/lib/api";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Calendar,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock,
  Sparkles,
  Ticket,
  UserCheck,
} from "lucide-react";
import {
  createCustomerBooking,
  fetchMyCustomerPackages,
  loginCustomer,
  registerCustomer,
  saveCustomerToken,
} from "@/lib/customer-api";
import type { MyCustomerPackageItem, ServiceItem } from "@/lib/types";
import {
  addDaysISO,
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

interface SelectedWizardLine {
  service_id: string;
  customer_package_id: string | null;
}

function BookingWizardInner(): React.ReactElement | null {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { slug, tenant, user, refreshCustomer } = useCustomerTenant();

  const [step, setStep] = React.useState<1 | 2 | 3>(1);
  const bookingRequest = useCustomerBookingRequest(slug, user?.id);
  const bookingFlight = React.useRef(false);
  const [selectedLines, setSelectedLines] = React.useState<
    SelectedWizardLine[]
  >([]);
  const [myPackages, setMyPackages] = React.useState<MyCustomerPackageItem[]>([]);
  const [selectedDate, setSelectedDate] = React.useState<string>(() =>
    formatDateISOInVN()
  );
  const [selectedStaffId, setSelectedStaffId] = React.useState<string | null>(
    null
  );
  const { slots: availableSlots, loading: slotsLoading, error: slotsError, retry: retrySlots,
    selectedStart: selectedSlotStart, select: setSelectedSlotStart } = useAvailableSlots({
    slug, date: selectedDate, serviceIds: selectedLines.map((line) => line.service_id),
    staffId: selectedStaffId, enabled: Boolean(tenant) && selectedDate >= formatDateISOInVN(), autoSelect: false,
  });
  const nearest = useNearestAvailableDay({ slug, date: selectedDate,
    serviceIds: selectedLines.map((line) => line.service_id), staffId: selectedStaffId,
    enabled: Boolean(tenant) && step === 2 && !slotsLoading && selectedLines.length > 0,
    onFound: setSelectedDate });
  const [note, setNote] = React.useState<string>("");

  // Quick Auth in the confirmation step keeps the booking draft in memory.
  const [authMode, setAuthMode] = React.useState<"login" | "register">("login");
  const [authName, setAuthName] = React.useState<string>("");
  const [authPhone, setAuthPhone] = React.useState<string>("");
  const [authPassword, setAuthPassword] = React.useState<string>("");
  const [authBusy, setAuthBusy] = React.useState<boolean>(false);

  const [submitting, setSubmitting] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string | null>(null);

  // Consume a valid deep link once; background tenant refresh must not reset the draft.
  const appliedLink = React.useRef("");
  React.useEffect(() => {
    if (!tenant) return;
    const serviceId = searchParams.get("service_id");
    const packageId = searchParams.get("package_id");
    if (packageId || !serviceId || !tenant.services.some((service) => service.id === serviceId)) return;
    const key = JSON.stringify([slug, serviceId]);
    if (appliedLink.current === key) return;
    appliedLink.current = key;
    setSelectedLines([{ service_id: serviceId, customer_package_id: null }]);
    setStep(2);
  }, [tenant, slug, searchParams]);

  // Load customer active packages when logged in
  React.useEffect(() => {
    if (!user) {
      setMyPackages([]);
      return;
    }
    let cancelled = false;
    setMyPackages([]);
    void (async () => {
      try {
        const pkgs = await fetchMyCustomerPackages(slug);
        if (!cancelled) {
          const usable = pkgs.filter((p) => p.available_sessions > 0);
          setMyPackages(usable);
          const packageId = searchParams.get("package_id");
          const serviceId = searchParams.get("service_id");
          const key = JSON.stringify([slug, user.id, serviceId, packageId]);
          if (packageId && appliedLink.current !== key) {
            const selected = usable.find((pkg) => pkg.id === packageId && pkg.service_id === serviceId);
            appliedLink.current = key;
            if (selected) { setSelectedLines([{ service_id: selected.service_id, customer_package_id: selected.id }]); setStep(2); }
            else setError("Thẻ này chưa thể dùng để đặt lịch. Vui lòng chọn thẻ khác hoặc liên hệ spa.");
          }
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Không thể tải thẻ liệu trình.");
      }
    })();
    return () => { cancelled = true; };
  }, [slug, user, searchParams]);

  const staffDirectory = tenant?.staff || [];

  const serviceById = React.useMemo(() => {
    const map = new Map<string, ServiceItem>();
    for (const s of tenant?.services || []) map.set(s.id, s);
    return map;
  }, [tenant]);

  const totalDuration = React.useMemo(() => {
    return selectedLines.reduce((acc, line) => {
      const svc = serviceById.get(line.service_id);
      return acc + (svc?.duration_minutes ?? 0);
    }, 0);
  }, [selectedLines, serviceById]);

  const totalPrice = React.useMemo(() => {
    return selectedLines.reduce((acc, line) => {
      if (line.customer_package_id) return acc;
      const svc = serviceById.get(line.service_id);
      return acc + (svc ? parseFloat(svc.price) : 0);
    }, 0);
  }, [selectedLines, serviceById]);

  if (!tenant) return null;
  const themeColor = "var(--brand-color)";

  const toggleLine = (serviceId: string, packageId: string | null): void => {
    setSelectedLines((prev) => {
      const exists = prev.some(
        (l) =>
          l.service_id === serviceId && l.customer_package_id === packageId
      );
      if (exists) {
        return prev.filter(
          (l) =>
            !(
              l.service_id === serviceId && l.customer_package_id === packageId
            )
        );
      }
      if (prev.length >= 10) return prev;
      return [
        ...prev,
        { service_id: serviceId, customer_package_id: packageId },
      ];
    });
  };

  const handleInlineAuth = async (
    e: React.FormEvent<HTMLFormElement>
  ): Promise<void> => {
    e.preventDefault();
    setError(null);
    setAuthBusy(true);
    try {
      const res =
        authMode === "login"
          ? await loginCustomer(slug, {
              phone_number: authPhone.trim(),
              password: authPassword,
            })
          : await registerCustomer(slug, {
              full_name: authName.trim(),
              phone_number: authPhone.trim(),
              password: authPassword,
            });
      saveCustomerToken(slug, res.access_token);
      await refreshCustomer();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Xác thực tài khoản thất bại"
      );
    } finally {
      setAuthBusy(false);
    }
  };

  const handleConfirmBooking = async (): Promise<void> => {
    if (bookingFlight.current) return;
    if (!user) {
      setError("Vui lòng đăng nhập hoặc đăng ký nhanh ở trên trước khi đặt lịch.");
      return;
    }
    if (selectedLines.length === 0 || !selectedSlotStart) {
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
        items: selectedLines,
      });
      if (created) router.push(`/${slug}/appointments?booked=1&booking_id=${encodeURIComponent(created.id)}`);
      else { bookingFlight.current = false; setSubmitting(false); }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Không thể hoàn tất đặt lịch, vui lòng chọn khung giờ khác."
      );
      if (err instanceof ApiError && err.status === 409) {
        setStep(2);
        retrySlots();
      }
      bookingFlight.current = false;
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      {(bookingRequest.uncertain || bookingRequest.message) && <section aria-label="Kiểm tra kết quả đặt lịch" className="space-y-2 rounded-xl border p-4">
        <p role="status">{bookingRequest.message || "Có một yêu cầu đặt lịch cần kiểm tra kết quả."}</p>
        {bookingRequest.uncertain && <div className="flex flex-wrap gap-2"><Button disabled={bookingRequest.busy} onClick={async () => { const booking = await bookingRequest.check(); if (booking) router.push("/" + slug + "/appointments?booking_id=" + booking.id); }}>Kiểm tra lịch đã đặt</Button>
        {bookingRequest.canRetry && <Button variant="outline" disabled={bookingRequest.busy} onClick={async () => { try { const booking = await bookingRequest.retry(); if (booking) router.push("/" + slug + "/appointments?booking_id=" + booking.id); } catch { /* recovery state remains visible */ } }}>Gửi lại đúng yêu cầu này</Button>}</div>}
      </section>}
      <fieldset disabled={bookingRequest.uncertain || bookingRequest.busy || submitting} className="m-0 min-w-0 space-y-4 border-0 p-0">
      {/* Stepper Header */}
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
                disabled={submitting || (s.num > 1 && selectedLines.length === 0) || (s.num === 3 && !selectedSlotStart)}
                onClick={() => {
                  setStep(s.num as 1 | 2 | 3);
                }}
                className={cn(
                  "flex min-h-11 min-w-0 items-center justify-center gap-1 rounded-lg px-1 py-2 transition disabled:opacity-50 [overflow-wrap:anywhere]",
                  isCurrent
                    ? "font-bold text-white shadow-sm"
                    : isDone
                      ? "text-emerald-700 font-semibold"
                      : "text-muted-foreground"
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

      {/* STEP 1: Select Services or Active Treatment Packages */}
      {step === 1 && (
        <div className="space-y-4">
          {user && myPackages.length > 0 && (
            <Card className="border-primary/30 bg-primary/5">
              <CardContent className="p-4 space-y-2.5">
                <div className="flex items-center gap-1.5 text-xs font-bold text-primary">
                  <Ticket className="h-4 w-4" />
                  Thẻ liệu trình của bạn — Đặt lịch bằng buổi trong thẻ
                </div>
                <div className="space-y-2">
                  {myPackages.map((pkg) => {
                    const checked = selectedLines.some(
                      (l) =>
                        l.service_id === pkg.service_id &&
                        l.customer_package_id === pkg.id
                    );
                    return (
                      <button
                        type="button"
                        aria-pressed={checked}
                        key={pkg.id}
                        onClick={() => toggleLine(pkg.service_id, pkg.id)}
                        className={cn(
                          "flex w-full min-w-0 flex-wrap cursor-pointer items-center justify-between gap-2 rounded-xl border p-3 text-left text-sm transition [overflow-wrap:anywhere]",
                          checked
                            ? "border-primary neu-surface bg-card shadow-sm"
                            : "border-border neu-surface bg-card/70"
                        )}
                      >
                        <div>
                          <p className="font-bold text-foreground">
                            {pkg.package_name}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            Đã dùng {pkg.used_sessions}/{pkg.total_sessions} •
                            Còn <strong>{pkg.available_sessions} buổi</strong>
                          </p>
                        </div>
                        <Badge variant={checked ? "success" : "outline"}>
                          {checked ? "✓ Đã chọn 1 buổi" : "Dùng 1 buổi trong thẻ"}
                        </Badge>
                      </button>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}

          <div className="space-y-2.5">
            <h2 className="text-sm font-bold text-foreground">
              Chọn 1 hoặc nhiều dịch vụ ({selectedLines.length} đã chọn)
            </h2>
            {tenant.services.length === 0 && <p className="rounded-lg border p-3 text-sm">Spa chưa có dịch vụ nhận lịch trực tuyến. Hãy liên hệ chi nhánh để được hỗ trợ.</p>}
            {tenant.services.map((svc) => {
              const checked = selectedLines.some(
                (l) =>
                  l.service_id === svc.id && l.customer_package_id === null
              );
              return (
                <button
                  type="button"
                  aria-pressed={checked}
                  key={svc.id}
                  onClick={() => toggleLine(svc.id, null)}
                  className={cn(
                    "flex w-full min-w-0 cursor-pointer items-center justify-between gap-3 rounded-xl border neu-surface bg-card p-3.5 text-left transition [overflow-wrap:anywhere]",
                    checked
                      ? "ring-2 ring-primary border-primary shadow-sm"
                      : "border-border hover:bg-muted/40"
                  )}
                >
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-sm font-bold text-foreground">
                        {svc.name}
                      </span>
                      {svc.is_package && (
                        <Badge variant="default">
                          Gói {svc.total_sessions} buổi · giá cả gói
                        </Badge>
                      )}
                    </div>
                    {svc.description && (
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {svc.description}
                      </p>
                    )}
                    <p className="text-xs font-medium text-slate-600">
                      ⏱ {svc.duration_minutes} phút{svc.is_package ? "/buổi" : ""} •{" "}
                      <strong style={{ color: "var(--brand-text)" }}>
                        {formatCurrency(svc.price)}
                      </strong>
                    </p>
                  </div>
                  <div
                    className={cn(
                      "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-bold",
                      checked
                        ? "border-transparent text-white"
                        : "border-slate-300 text-transparent"
                    )}
                    style={
                      checked ? { backgroundColor: themeColor, color: "var(--brand-foreground)" } : undefined
                    }
                  >
                    ✓
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* STEP 2: Select Technician or Auto-assign */}
      {step === 2 && (
        <div className="space-y-3">
          <div className="flex min-w-0 flex-wrap items-center justify-between gap-2 rounded-lg border p-3 text-sm [overflow-wrap:anywhere]">
            <span className="min-w-0 max-w-full">{selectedLines.map((line) => tenant.services.find((service) => service.id === line.service_id)?.name || "Dịch vụ").join(", ")} • {totalDuration} phút</span>
            <Button type="button" variant="outline" onClick={() => setStep(1)}>Đổi dịch vụ</Button>
          </div>
          {/* Date and technician belong to the same step. */}
          <Card>
            <CardContent className="p-4 space-y-3">
              <Label htmlFor="wizDate" className="flex items-center gap-1.5">
                <Calendar className="h-4 w-4 text-primary" />
                Chọn ngày hẹn (Múi giờ Việt Nam)
              </Label>
              <div className="flex flex-wrap gap-2">
                <Button type="button" variant="outline" onClick={() => setSelectedDate(formatDateISOInVN())}>Hôm nay</Button>
                <Button type="button" variant="outline" onClick={() => setSelectedDate(addDaysISO(formatDateISOInVN(), 1))}>Ngày mai</Button>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  aria-label="Ngày trước"
                  disabled={selectedDate <= formatDateISOInVN()}
                  onClick={() =>
                    setSelectedDate(addDaysISO(selectedDate, -1))
                  }
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Input
                  id="wizDate"
                  type="date"
                  min={formatDateISOInVN()}
                  value={selectedDate}
                  onChange={(e) => { if (e.target.value >= formatDateISOInVN()) setSelectedDate(e.target.value); }}
                  className="min-w-0 flex-1"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  aria-label="Ngày tiếp theo"
                  onClick={() =>
                    setSelectedDate(addDaysISO(selectedDate, 1))
                  }
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-foreground">
                Khung giờ còn trống ({availableSlots.length})
              </h3>
              <span className="text-xs text-muted-foreground">
                Tổng {totalDuration} phút
              </span>
            </div>

            {slotsLoading ? (
              <Card>
                <CardContent className="p-8 text-center text-xs text-muted-foreground">
                  Đang kiểm tra lịch trống của Kỹ thuật viên...
                </CardContent>
              </Card>
            ) : slotsError ? (
              <div role="alert" className="space-y-2 rounded-lg border p-3 text-center text-sm">
                <p>{slotsError}</p><Button type="button" variant="outline" onClick={retrySlots}>Thử lại khung giờ</Button>
              </div>
            ) : availableSlots.length === 0 ? (
              <Card>
                <CardContent className="p-6 text-center text-xs text-amber-800 bg-amber-50 rounded-xl">
                  Rất tiếc, ngày {selectedDate} không còn khung giờ trống nào đủ{" "}
                  {totalDuration} phút. Hãy tìm ngày khác hoặc đổi nhân viên.
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-3 gap-2">
                {availableSlots.map((slot) => {
                  const isSelected = selectedSlotStart === slot.start_time;
                  return (
                    <button
                      key={slot.start_time}
                      type="button"
                      aria-pressed={isSelected}
                      onClick={() => setSelectedSlotStart(slot.start_time)}
                      className={cn(
                        "flex min-h-11 flex-col items-center rounded-xl border py-2.5 px-2 text-xs font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                        isSelected
                          ? "border-transparent text-white shadow"
                          : "border-border neu-surface bg-card text-foreground hover:bg-muted/60"
                      )}
                      style={
                        isSelected
                          ? { backgroundColor: themeColor, color: "var(--brand-foreground)" }
                          : undefined
                      }
                    >
                      <span className="text-sm font-bold">
                        {formatTimeVN(slot.start_time)}
                      </span>
                      <span
                        className={cn(
                          "text-xs",
                          isSelected
                            ? "text-inherit"
                            : "text-muted-foreground"
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
          <div className="space-y-2">
            <Button type="button" variant="outline" className="h-auto min-h-11 max-w-full whitespace-normal text-left" disabled={nearest.searching || slotsLoading} onClick={() => void nearest.search()}>{nearest.searching ? "Đang tìm ngày còn chỗ..." : "Tìm ngày còn chỗ trong 7 ngày tiếp theo"}</Button>
            {nearest.message && <p role="status" className="text-sm text-muted-foreground">{nearest.message}</p>}
          </div>
          <details className="rounded-xl border p-3" open={selectedStaffId !== null || undefined}>
            <summary className="min-h-11 cursor-pointer py-3 text-sm font-semibold">{selectedStaffId ? "Nhân viên: " + (staffDirectory.find((staff) => staff.id === selectedStaffId)?.full_name || "Đã chọn") : "Spa tự sắp xếp · Chọn nhân viên quen"}</summary>
          <h2 className="text-sm font-bold text-foreground">
            Chọn nhân viên thực hiện
          </h2>
          <p className="text-xs text-muted-foreground">
            Bạn có thể để Spa tự động sắp xếp Kỹ thuật viên có ca trống hoặc
            chọn đích danh Kỹ thuật viên yêu thích.
          </p>

          <button
            type="button"
            aria-pressed={selectedStaffId === null}
            onClick={() => setSelectedStaffId(null)}
            className={cn(
              "flex w-full min-w-0 flex-wrap cursor-pointer items-center justify-between gap-2 rounded-xl border neu-surface bg-card p-4 text-left transition [overflow-wrap:anywhere]",
              selectedStaffId === null
                ? "ring-2 ring-primary border-primary"
                : "border-border"
            )}
          >
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <div
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-white"
                style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
              >
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-bold text-foreground">
                  Spa tự sắp xếp
                </p>
                <p className="text-xs text-muted-foreground">
                  Spa chọn nhân viên phù hợp với giờ bạn đặt
                </p>
              </div>
            </div>
            {selectedStaffId === null && (
              <Badge variant="success">Đang chọn</Badge>
            )}
          </button>

          {staffDirectory.length > 0 && (
            <div className="space-y-2 pt-2">
              <p className="text-xs font-semibold text-muted-foreground">
                Hoặc chọn Kỹ thuật viên; giờ trống được kiểm tra theo ngày:
              </p>
              {staffDirectory.map(({ id: sid, full_name }) => {
                const active = selectedStaffId === sid;
                return (
                  <button
                    type="button"
                    aria-pressed={active}
                    key={sid}
                    onClick={() => setSelectedStaffId(sid)}
                    className={cn(
                      "flex w-full min-w-0 items-center justify-between gap-2 rounded-xl border neu-surface bg-card p-3.5 text-left transition",
                      active
                        ? "ring-2 ring-primary border-primary"
                        : "border-border"
                    )}
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-muted text-slate-700">
                        <UserCheck className="h-4 w-4" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-foreground [overflow-wrap:anywhere]">
                          {full_name}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Chọn ngày để xem giờ còn trống
                        </p>
                      </div>
                    </div>
                    {active && <Badge variant="success">Đang chọn</Badge>}
                  </button>
                );
              })}
            </div>
          )}
          </details>
        </div>
      )}

      {/* STEP 3: Review & Confirm Booking */}
      {step === 3 && (
        <div className="space-y-4">
          <Card>
            <CardContent className="p-4 space-y-3 text-sm [overflow-wrap:anywhere] [&>div]:min-w-0 [&>div]:gap-3 [&>div]:flex-wrap">
              <h3 className="text-sm font-bold text-foreground border-b border-border pb-2">
                Xác nhận lịch hẹn
              </h3>

              <div className="flex justify-between">
                <span className="text-muted-foreground">Cơ sở Spa:</span>
                <strong className="text-foreground">{tenant.name}</strong>
              </div>

              <div className="flex justify-between">
                <span className="text-muted-foreground">Thời gian hẹn:</span>
                <strong className="text-foreground">
                  {selectedSlotStart
                    ? formatDateTimeVN(selectedSlotStart)
                    : "Chưa chọn giờ"}
                </strong>
              </div>

              <div className="flex justify-between">
                <span className="text-muted-foreground">Tổng thời lượng:</span>
                <strong className="text-foreground">
                  {totalDuration} phút
                </strong>
              </div>

              <div className="flex justify-between">
                <span className="text-muted-foreground">Kỹ thuật viên:</span>
                <strong className="text-foreground">
                  {selectedStaffId
                    ? staffDirectory.find((person) => person.id === selectedStaffId)?.full_name || "Chưa có tên KTV"
                    : "Spa tự sắp xếp"}
                </strong>
              </div>

              <div className="border-t border-border pt-2 space-y-1.5">
                <p className="font-semibold text-foreground">
                  Dịch vụ đã chọn ({selectedLines.length}):
                </p>
                {selectedLines.map((line, i) => {
                  const svc = serviceById.get(line.service_id);
                  return (
                    <div
                      key={`${line.service_id}-${i}`}
                      className="flex min-w-0 flex-wrap items-center justify-between gap-2 rounded bg-muted/50 px-2.5 py-1.5"
                    >
                      <span>
                        {svc?.name || "Dịch vụ"} ({svc?.duration_minutes}p)
                      </span>
                      <span className="font-bold">
                        {line.customer_package_id
                          ? "Dùng 1 buổi trong thẻ"
                          : formatCurrency(svc?.price || 0)}
                      </span>
                    </div>
                  );
                })}
              </div>

              <div className="flex items-center justify-between border-t border-border pt-2.5 text-sm">
                <span className="font-bold">{selectedLines.some((line) => line.customer_package_id)
                  ? "Dự kiến thu thêm ngoài thẻ:" : "Tổng thanh toán dự kiến:"}</span>
                <span
                  className="text-base font-extrabold"
                  style={{ color: "var(--brand-text)" }}
                >
                  {formatCurrency(totalPrice)}
                </span>
              </div>

              <div className="space-y-1 pt-2">
                <Label htmlFor="wizNote">Ghi chú cho Lễ tân / KTV</Label>
                <Textarea
                  id="wizNote"
                  placeholder="VD: Mình muốn phòng yên tĩnh, da đang hơi khô..."
                  value={note}
                  disabled={submitting}
                  onChange={(e) => setNote(e.target.value)}
                />
              </div>
            </CardContent>
          </Card>

          {/* Inline Auth if Customer is not logged in */}
          {!user && (
            <Card className="border-primary/40">
              <CardContent className="p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-bold text-foreground">
                    {authMode === "login"
                      ? "Đăng nhập nhanh để hoàn tất đặt lịch"
                      : "Đăng ký nhanh tài khoản khách hàng"}
                  </p>
                  <button
                    type="button"
                    onClick={() =>
                      setAuthMode(authMode === "login" ? "register" : "login")
                    }
                    className="text-xs font-semibold underline"
                    style={{ color: "var(--brand-text)" }}
                  >
                    {authMode === "login"
                      ? "Chưa có TK? Đăng ký"
                      : "Đã có TK? Đăng nhập"}
                  </button>
                </div>

                <form
                  onSubmit={(e) => void handleInlineAuth(e)}
                  className="space-y-2.5"
                >
                  {authMode === "register" && (
                    <div className="space-y-1.5">
                      <Label htmlFor="wizAuthName">Họ và tên *</Label>
                      <Input
                        id="wizAuthName"
                        name="full_name"
                        autoComplete="name"
                        placeholder="Họ và tên của bạn"
                        value={authName}
                        onChange={(e) => setAuthName(e.target.value)}
                        required
                      />
                    </div>
                  )}
                  <div className="space-y-1.5">
                    <Label htmlFor="wizAuthPhone">Số điện thoại *</Label>
                    <Input
                      id="wizAuthPhone"
                      name="phone_number"
                      type="tel"
                      inputMode="tel"
                      autoComplete="username"
                      value={authPhone}
                      onChange={(e) => setAuthPhone(e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="wizAuthPassword">Mật khẩu *</Label>
                    <PasswordInput
                      id="wizAuthPassword"
                      name="password"
                      type="password"
                      autoComplete={authMode === "register" ? "new-password" : "current-password"}
                      placeholder="Ít nhất 6 ký tự"
                      value={authPassword}
                      onChange={(e) => setAuthPassword(e.target.value)}
                      required
                    />
                  </div>
                  <Button
                    type="submit"
                    size="sm"
                    className="w-full"
                    style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
                    disabled={authBusy}
                  >
                    {authBusy
                      ? "Đang xác thực..."
                      : authMode === "login"
                        ? "Đăng nhập & Tiếp tục"
                        : "Đăng ký & Tiếp tục"}
                  </Button>
                </form>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Bottom Sticky Summary & Wizard Navigation */}
      <div className="rounded-2xl border border-border neu-surface bg-card p-3.5 shadow-md space-y-2.5">
        <div className="flex min-w-0 flex-wrap items-center justify-between gap-2 text-xs">
          <span className="inline-flex items-center gap-1 text-muted-foreground">
            <Clock className="h-3.5 w-3.5" />
            Tổng thời gian: <strong className="text-foreground">{totalDuration} phút</strong>
          </span>
          <span className="font-bold text-foreground">
            Tạm tính:{" "}
            <strong className="text-sm" style={{ color: "var(--brand-text)" }}>
              {formatCurrency(totalPrice)}
            </strong>
          </span>
        </div>

        <div className="flex items-center justify-between gap-2">
          {step > 1 ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={submitting}
              onClick={() => setStep((s) => (s - 1) as 1 | 2 | 3)}
            >
              <ChevronLeft className="h-4 w-4" />
              Quay lại
            </Button>
          ) : (
            <div />
          )}

          {step < 3 ? (
            <Button
              type="button"
              size="sm"
              disabled={
                (step === 1 && selectedLines.length === 0) ||
                (step === 2 && (slotsLoading || !selectedSlotStart))
              }
              style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
              onClick={() => setStep((s) => (s + 1) as 1 | 2 | 3)}
            >
              Tiếp tục
              <ChevronRight className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              type="button"
              size="sm"
              disabled={submitting || slotsLoading || !user || !selectedSlotStart || !bookingRequest.ready}
              style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
              onClick={() => void handleConfirmBooking()}
            >
              {submitting ? "Đang gửi lịch hẹn..." : "Xác nhận Đặt lịch"}
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
    <React.Suspense
      fallback={
        <div className="p-8 text-center text-xs text-muted-foreground">
          Đang khởi tạo luồng đặt lịch...
        </div>
      }
    >
      <BookingWizardInner />
    </React.Suspense>
  );
}
