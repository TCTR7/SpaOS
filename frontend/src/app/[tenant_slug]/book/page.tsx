"use client";

import * as React from "react";
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
  fetchCustomerAvailableSlots,
  fetchMyCustomerPackages,
  loginCustomer,
  registerCustomer,
  saveCustomerToken,
} from "@/lib/customer-api";
import type { MyCustomerPackageItem, ServiceItem, SlotItem } from "@/lib/types";
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

  const [step, setStep] = React.useState<1 | 2 | 3 | 4>(1);
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
  const [availableSlots, setAvailableSlots] = React.useState<SlotItem[]>([]);
  const [slotsLoading, setSlotsLoading] = React.useState<boolean>(false);
  const [selectedSlotStart, setSelectedSlotStart] = React.useState<string>("");
  const [note, setNote] = React.useState<string>("");

  // Quick Auth state in Step 4 if not logged in
  const [authMode, setAuthMode] = React.useState<"login" | "register">("login");
  const [authName, setAuthName] = React.useState<string>("");
  const [authPhone, setAuthPhone] = React.useState<string>("");
  const [authPassword, setAuthPassword] = React.useState<string>("");
  const [authBusy, setAuthBusy] = React.useState<boolean>(false);

  const [submitting, setSubmitting] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string | null>(null);

  // Preselect service_id or package_id from query params
  React.useEffect(() => {
    if (!tenant) return;
    const preSvcId = searchParams.get("service_id");
    const prePkgId = searchParams.get("package_id");
    if (preSvcId && tenant.services.some((s) => s.id === preSvcId)) {
      setSelectedLines([
        {
          service_id: preSvcId,
          customer_package_id: prePkgId || null,
        },
      ]);
    }
  }, [tenant, searchParams]);

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
        if (!cancelled) setMyPackages(pkgs.filter((p) => p.available_sessions > 0));
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Không thể tải thẻ liệu trình.");
      }
    })();
    return () => { cancelled = true; };
  }, [slug, user]);

  // Fetch available slots when selectedLines, selectedDate, or selectedStaffId changes
  React.useEffect(() => {
    if (!tenant || selectedLines.length === 0 || !selectedDate) {
      setAvailableSlots([]);
      setSelectedSlotStart("");
      return;
    }
    let cancelled = false;
    setSlotsLoading(true);
    setSelectedSlotStart("");
    setAvailableSlots([]);
    void (async () => {
      try {
        const res = await fetchCustomerAvailableSlots(slug, {
          date: selectedDate,
          service_ids: selectedLines.map((l) => l.service_id),
          staff_id: selectedStaffId,
        });
        if (!cancelled) {
          setAvailableSlots(res.slots);
          setSelectedSlotStart(res.slots[0]?.start_time || "");
        }
      } catch {
        if (!cancelled) {
          setAvailableSlots([]);
          setSelectedSlotStart("");
        }
      } finally {
        if (!cancelled) setSlotsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [tenant, slug, selectedLines, selectedDate, selectedStaffId]);

  // Discover distinct available staff IDs from current day's slots
  const discoveredStaffIds = React.useMemo(() => {
    const ids = new Set<string>();
    for (const s of availableSlots) {
      for (const sid of s.available_staff_ids) {
        ids.add(sid);
      }
    }
    return Array.from(ids);
  }, [availableSlots]);

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
    if (!user) {
      setError("Vui lòng đăng nhập hoặc đăng ký nhanh ở trên trước khi đặt lịch.");
      return;
    }
    if (selectedLines.length === 0 || !selectedSlotStart) {
      setError("Vui lòng chọn đầy đủ dịch vụ và khung giờ hẹn.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await createCustomerBooking(slug, {
        start_time: selectedSlotStart,
        staff_id: selectedStaffId,
        note: note.trim() || null,
        items: selectedLines,
      });
      router.push(`/${slug}/appointments?booked=1`);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Không thể hoàn tất đặt lịch, vui lòng chọn khung giờ khác."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Stepper Header */}
      <div className="rounded-2xl border border-border bg-card p-3.5 shadow-xs">
        <div className="flex items-center justify-between text-xs font-semibold">
          {[
            { num: 1, label: "1. Dịch vụ" },
            { num: 2, label: "2. Kỹ thuật viên" },
            { num: 3, label: "3. Ngày & Giờ" },
            { num: 4, label: "4. Xác nhận" },
          ].map((s) => {
            const isCurrent = step === s.num;
            const isDone = step > s.num;
            return (
              <button
                key={s.num}
                type="button"
                onClick={() => {
                  if (s.num === 1 || selectedLines.length > 0) {
                    setStep(s.num as 1 | 2 | 3 | 4);
                  }
                }}
                className={cn(
                  "flex items-center gap-1 rounded-lg px-2 py-1 transition",
                  isCurrent
                    ? "font-bold text-white shadow-xs"
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
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-300 bg-rose-50 px-3.5 py-2.5 text-xs font-medium text-rose-700">
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
                      <div
                        key={pkg.id}
                        onClick={() => toggleLine(pkg.service_id, pkg.id)}
                        className={cn(
                          "flex min-w-0 flex-wrap cursor-pointer items-center justify-between gap-2 rounded-xl border p-3 text-xs transition [overflow-wrap:anywhere]",
                          checked
                            ? "border-primary bg-card shadow-xs"
                            : "border-border bg-card/70"
                        )}
                      >
                        <div>
                          <p className="font-bold text-foreground">
                            {pkg.package_name}
                          </p>
                          <p className="text-[11px] text-muted-foreground">
                            Đã dùng {pkg.used_sessions}/{pkg.total_sessions} •
                            Còn <strong>{pkg.available_sessions} buổi</strong>
                          </p>
                        </div>
                        <Badge variant={checked ? "success" : "outline"}>
                          {checked ? "✓ Đã chọn 1 buổi" : "Dùng 1 buổi trong thẻ"}
                        </Badge>
                      </div>
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
            {tenant.services.map((svc) => {
              const checked = selectedLines.some(
                (l) =>
                  l.service_id === svc.id && l.customer_package_id === null
              );
              return (
                <div
                  key={svc.id}
                  onClick={() => toggleLine(svc.id, null)}
                  className={cn(
                    "flex cursor-pointer items-center justify-between gap-3 rounded-xl border bg-card p-3.5 transition",
                    checked
                      ? "ring-2 ring-primary border-primary shadow-sm"
                      : "border-border hover:bg-muted/40"
                  )}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm font-bold text-foreground">
                        {svc.name}
                      </span>
                      {svc.is_package && (
                        <Badge variant="default">
                          Gói {svc.total_sessions} buổi
                        </Badge>
                      )}
                    </div>
                    {svc.description && (
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {svc.description}
                      </p>
                    )}
                    <p className="text-xs font-medium text-slate-600">
                      ⏱ {svc.duration_minutes} phút •{" "}
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
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* STEP 2: Select Technician or Auto-assign */}
      {step === 2 && (
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-foreground">
            Chọn Kỹ thuật viên thực hiện
          </h2>
          <p className="text-xs text-muted-foreground">
            Bạn có thể để Spa tự động sắp xếp Kỹ thuật viên có ca trống hoặc
            chọn đích danh Kỹ thuật viên yêu thích.
          </p>

          <div
            onClick={() => setSelectedStaffId(null)}
            className={cn(
              "flex cursor-pointer items-center justify-between rounded-xl border bg-card p-4 transition",
              selectedStaffId === null
                ? "ring-2 ring-primary border-primary"
                : "border-border"
            )}
          >
            <div className="flex items-center gap-3">
              <div
                className="flex h-10 w-10 items-center justify-center rounded-full text-white"
                style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
              >
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-bold text-foreground">
                  Spa tự sắp xếp Kỹ thuật viên (Khuyên dùng)
                </p>
                <p className="text-xs text-muted-foreground">
                  Nhiều khung giờ trống nhất, hệ thống tự động gán KTV rảnh
                </p>
              </div>
            </div>
            {selectedStaffId === null && (
              <Badge variant="success">Đang chọn</Badge>
            )}
          </div>

          {discoveredStaffIds.length > 0 && (
            <div className="space-y-2 pt-2">
              <p className="text-xs font-semibold text-muted-foreground">
                Hoặc chọn Kỹ thuật viên đang có ca trống trong ngày:
              </p>
              {discoveredStaffIds.map((sid, idx) => {
                const active = selectedStaffId === sid;
                return (
                  <div
                    key={sid}
                    onClick={() => setSelectedStaffId(sid)}
                    className={cn(
                      "flex cursor-pointer items-center justify-between rounded-xl border bg-card p-3.5 transition",
                      active
                        ? "ring-2 ring-primary border-primary"
                        : "border-border"
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-full bg-muted text-slate-700">
                        <UserCheck className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-foreground">
                          Kỹ thuật viên #{idx + 1} ({sid.slice(0, 6)})
                        </p>
                        <p className="text-[11px] text-muted-foreground">
                          Đang có lịch làm việc khả dụng
                        </p>
                      </div>
                    </div>
                    {active && <Badge variant="success">Đang chọn</Badge>}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* STEP 3: Select Date & Available Time Slot */}
      {step === 3 && (
        <div className="space-y-4">
          <Card>
            <CardContent className="p-4 space-y-3">
              <Label htmlFor="wizDate" className="flex items-center gap-1.5">
                <Calendar className="h-4 w-4 text-primary" />
                Chọn ngày hẹn (Múi giờ Việt Nam)
              </Label>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  aria-label="Ngày trước"
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
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="flex-1"
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
            ) : availableSlots.length === 0 ? (
              <Card>
                <CardContent className="p-6 text-center text-xs text-amber-800 bg-amber-50 rounded-xl">
                  Rất tiếc, ngày {selectedDate} không còn khung giờ trống nào đủ{" "}
                  {totalDuration} phút. Vui lòng chọn ngày tiếp theo!
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
                          : "border-border bg-card text-foreground hover:bg-muted/60"
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
                          "text-[10px]",
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
        </div>
      )}

      {/* STEP 4: Review & Confirm Booking */}
      {step === 4 && (
        <div className="space-y-4">
          <Card>
            <CardContent className="p-4 space-y-3 text-xs">
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
                    ? `KTV #${selectedStaffId.slice(0, 6)}`
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
                      className="flex items-center justify-between rounded bg-muted/50 px-2.5 py-1.5"
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
                    <Input
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
      <div className="rounded-2xl border border-border bg-card p-3.5 shadow-md space-y-2.5">
        <div className="flex items-center justify-between text-xs">
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
              onClick={() => setStep((s) => (s - 1) as 1 | 2 | 3 | 4)}
            >
              <ChevronLeft className="h-4 w-4" />
              Quay lại
            </Button>
          ) : (
            <div />
          )}

          {step < 4 ? (
            <Button
              type="button"
              size="sm"
              disabled={
                (step === 1 && selectedLines.length === 0) ||
                (step === 3 && (slotsLoading || !selectedSlotStart))
              }
              style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
              onClick={() => setStep((s) => (s + 1) as 1 | 2 | 3 | 4)}
            >
              Tiếp tục
              <ChevronRight className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              type="button"
              size="sm"
              disabled={submitting || slotsLoading || !user || !selectedSlotStart}
              style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
              onClick={() => void handleConfirmBooking()}
            >
              {submitting ? "Đang gửi lịch hẹn..." : "Xác nhận Đặt lịch"}
            </Button>
          )}
        </div>
      </div>
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
