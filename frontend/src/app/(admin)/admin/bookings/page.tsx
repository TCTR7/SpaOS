"use client";

import * as React from "react";
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  Clock,
  Plus,
  RefreshCw,
  Ticket,
  UserPlus,
} from "lucide-react";
import {
  createBooking,
  createCustomer,
  fetchAvailableSlots,
  fetchBookings,
  fetchCustomerPackages,
  fetchCustomers,
  fetchServices,
  fetchStaffList,
  updateBookingStatus,
} from "@/lib/api";
import type {
  BookingRecord,
  BookingStatus,
  CustomerPackageItem,
  ServiceItem,
  SlotItem,
  UserDetail,
} from "@/lib/types";
import {
  addDaysISO,
  BOOKING_STATUS_META,
  cn,
  formatCurrency,
  formatDateISOInVN,
  formatTimeVN,
  getWeekDaysISO,
} from "@/lib/utils";
import { useAdminAuth } from "@/components/admin/auth-context";
import { Button } from "@/components/ui/button";
import { Badge, Card, CardContent } from "@/components/ui/card";
import { Input, Label, Textarea } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";

interface SelectedServiceLine {
  service_id: string;
  customer_package_id: string | null;
}

export default function AdminBookingsPage(): React.ReactElement {
  const { user } = useAdminAuth();

  const [viewMode, setViewMode] = React.useState<"day" | "week">("day");
  const [selectedDate, setSelectedDate] = React.useState<string>(() =>
    formatDateISOInVN()
  );
  const [filterStaffId, setFilterStaffId] = React.useState<string>("");
  const [filterStatus, setFilterStatus] = React.useState<BookingStatus | "">(
    ""
  );

  const [bookings, setBookings] = React.useState<BookingRecord[]>([]);
  const [services, setServices] = React.useState<ServiceItem[]>([]);
  const [customers, setCustomers] = React.useState<UserDetail[]>([]);
  const [staffList, setStaffList] = React.useState<UserDetail[]>([]);
  const [loading, setLoading] = React.useState<boolean>(true);
  const [error, setError] = React.useState<string | null>(null);
  const [statusBusyId, setStatusBusyId] = React.useState<string | null>(null);

  // Manual Booking Modal State
  const [modalOpen, setModalOpen] = React.useState<boolean>(false);
  const [modalCustomerId, setModalCustomerId] = React.useState<string>("");
  const [quickNewCustomer, setQuickNewCustomer] =
    React.useState<boolean>(false);
  const [newCustomerName, setNewCustomerName] = React.useState<string>("");
  const [newCustomerPhone, setNewCustomerPhone] = React.useState<string>("");
  const [newCustomerNotes, setNewCustomerNotes] = React.useState<string>("");
  const [customerPackages, setCustomerPackages] = React.useState<
    CustomerPackageItem[]
  >([]);

  const [selectedLines, setSelectedLines] = React.useState<
    SelectedServiceLine[]
  >([]);
  const [modalStaffId, setModalStaffId] = React.useState<string>("");
  const [modalDate, setModalDate] = React.useState<string>(() =>
    formatDateISOInVN()
  );
  const [availableSlots, setAvailableSlots] = React.useState<SlotItem[]>([]);
  const [slotsLoading, setSlotsLoading] = React.useState<boolean>(false);
  const [selectedSlotStart, setSelectedSlotStart] = React.useState<string>("");
  const [modalNote, setModalNote] = React.useState<string>("");
  const [modalError, setModalError] = React.useState<string | null>(null);
  const [creatingBooking, setCreatingBooking] = React.useState<boolean>(false);

  const serviceMap = React.useMemo(() => {
    const map = new Map<string, ServiceItem>();
    for (const s of services) map.set(s.id, s);
    return map;
  }, [services]);

  const customerMap = React.useMemo(() => {
    const map = new Map<string, UserDetail>();
    for (const c of customers) map.set(c.id, c);
    return map;
  }, [customers]);

  const staffMap = React.useMemo(() => {
    const map = new Map<string, UserDetail>();
    for (const st of staffList) map.set(st.id, st);
    return map;
  }, [staffList]);

  const weekDays = React.useMemo(
    () => getWeekDaysISO(selectedDate),
    [selectedDate]
  );

  const loadReferenceData = React.useCallback(async (): Promise<void> => {
    try {
      const [svcData, custData] = await Promise.all([
        fetchServices(),
        fetchCustomers({ limit: 200 }),
      ]);
      setServices(svcData);
      setCustomers(custData);

      if (user?.role === "ADMIN") {
        const stData = await fetchStaffList();
        setStaffList(stData);
      } else if (user) {
        setStaffList([
          {
            id: user.id,
            tenant_id: user.tenant_id,
            role: user.role,
            full_name: user.full_name,
            phone_number: user.phone_number,
            notes: null,
            is_active: user.is_active,
            created_at: new Date().toISOString(),
          },
        ]);
      }
    } catch {
      // ignore initial reference error
    }
  }, [user]);

  const loadBookings = React.useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const dateFrom = viewMode === "day" ? selectedDate : weekDays[0];
      const dateTo = viewMode === "day" ? selectedDate : weekDays[6];
      const data = await fetchBookings({
        date_from: dateFrom,
        date_to: dateTo,
        staff_id: filterStaffId || undefined,
        status: filterStatus || undefined,
        limit: 200,
      });
      // Sort chronologically by start_time
      const sorted = [...data].sort(
        (a, b) =>
          new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
      );
      setBookings(sorted);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Không thể tải danh sách lịch hẹn"
      );
    } finally {
      setLoading(false);
    }
  }, [viewMode, selectedDate, weekDays, filterStaffId, filterStatus]);

  React.useEffect(() => {
    void loadReferenceData();
  }, [loadReferenceData]);

  React.useEffect(() => {
    void loadBookings();
  }, [loadBookings]);

  // Load customer's active packages when selecting a customer in Manual Booking modal
  React.useEffect(() => {
    if (!modalCustomerId) {
      setCustomerPackages([]);
      return;
    }
    void (async () => {
      try {
        const pkgs = await fetchCustomerPackages(modalCustomerId);
        setCustomerPackages(
          pkgs.filter((p) => p.status === "ACTIVE" && p.remaining_sessions > 0)
        );
      } catch {
        setCustomerPackages([]);
      }
    })();
  }, [modalCustomerId]);

  // Automatically fetch available-slots when modalDate, selectedLines, or modalStaffId changes
  React.useEffect(() => {
    if (!modalOpen || selectedLines.length === 0 || !modalDate) {
      setAvailableSlots([]);
      setSelectedSlotStart("");
      return;
    }
    let cancelled = false;
    setSlotsLoading(true);
    void (async () => {
      try {
        const res = await fetchAvailableSlots({
          date: modalDate,
          service_ids: selectedLines.map((l) => l.service_id),
          staff_id: modalStaffId || null,
        });
        if (!cancelled) {
          setAvailableSlots(res.slots);
          if (
            res.slots.length > 0 &&
            !res.slots.some((s) => s.start_time === selectedSlotStart)
          ) {
            setSelectedSlotStart(res.slots[0].start_time);
          } else if (res.slots.length === 0) {
            setSelectedSlotStart("");
          }
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
  }, [modalOpen, modalDate, selectedLines, modalStaffId, selectedSlotStart]);

  const handleStatusChange = async (
    bookingId: string,
    nextStatus: BookingStatus
  ): Promise<void> => {
    setStatusBusyId(bookingId);
    setError(null);
    try {
      const updated = await updateBookingStatus(bookingId, nextStatus);
      setBookings((prev) =>
        prev.map((b) => (b.id === bookingId ? updated : b))
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Không thể cập nhật trạng thái lịch hẹn"
      );
    } finally {
      setStatusBusyId(null);
    }
  };

  const openCreateModal = (): void => {
    setModalError(null);
    setQuickNewCustomer(false);
    setModalCustomerId(customers[0]?.id || "");
    setNewCustomerName("");
    setNewCustomerPhone("");
    setNewCustomerNotes("");
    setSelectedLines([]);
    setModalStaffId("");
    setModalDate(selectedDate);
    setSelectedSlotStart("");
    setModalNote("");
    setModalOpen(true);
  };

  const toggleServiceSelection = (
    serviceId: string,
    packageId: string | null = null
  ): void => {
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

  const handleCreateManualBooking = async (
    e: React.FormEvent<HTMLFormElement>
  ): Promise<void> => {
    e.preventDefault();
    setModalError(null);

    if (selectedLines.length === 0) {
      setModalError("Vui lòng chọn ít nhất 1 dịch vụ hoặc buổi liệu trình.");
      return;
    }
    if (!selectedSlotStart) {
      setModalError("Vui lòng chọn khung giờ trống khả dụng.");
      return;
    }

    setCreatingBooking(true);
    try {
      let customerId = modalCustomerId;
      if (quickNewCustomer) {
        if (!newCustomerName.trim() || !newCustomerPhone.trim()) {
          setModalError("Vui lòng nhập họ tên và số điện thoại khách mới.");
          setCreatingBooking(false);
          return;
        }
        const createdCust = await createCustomer({
          full_name: newCustomerName.trim(),
          phone_number: newCustomerPhone.trim(),
          notes: newCustomerNotes.trim() || null,
        });
        setCustomers((prev) => [createdCust, ...prev]);
        customerId = createdCust.id;
      }

      if (!customerId) {
        setModalError("Vui lòng chọn khách hàng.");
        setCreatingBooking(false);
        return;
      }

      await createBooking({
        customer_id: customerId,
        staff_id: modalStaffId || null,
        start_time: selectedSlotStart,
        note: modalNote.trim() || null,
        items: selectedLines,
      });

      setModalOpen(false);
      await loadBookings();
    } catch (err) {
      setModalError(
        err instanceof Error ? err.message : "Tạo lịch hẹn thất bại"
      );
    } finally {
      setCreatingBooking(false);
    }
  };

  const activeServices = React.useMemo(
    () => services.filter((s) => s.is_active),
    [services]
  );

  const renderBookingCard = (booking: BookingRecord): React.ReactElement => {
    const meta = BOOKING_STATUS_META[booking.status];
    const customer = customerMap.get(booking.customer_id);
    const staff = booking.staff_id ? staffMap.get(booking.staff_id) : undefined;
    const hasPackageItem = booking.items.some(
      (i) => i.customer_package_id !== null
    );

    return (
      <div
        key={booking.id}
        className={cn(
          "rounded-lg border border-border p-3.5 shadow-xs transition hover:shadow-md",
          meta.cardClass
        )}
      >
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 text-xs font-bold text-slate-900">
                <Clock className="h-3.5 w-3.5 text-primary" />
                {formatTimeVN(booking.start_time)} –{" "}
                {formatTimeVN(booking.end_time)}
              </span>
              <span className="text-[11px] text-muted-foreground">
                ({booking.total_duration_minutes} phút)
              </span>
              {hasPackageItem && (
                <Badge variant="default" className="gap-1">
                  <Ticket className="h-3 w-3" />
                  Trừ thẻ liệu trình
                </Badge>
              )}
            </div>
            <p className="mt-1 text-sm font-semibold text-foreground">
              Khách:{" "}
              {customer
                ? `${customer.full_name} (${customer.phone_number})`
                : booking.customer_id.slice(0, 8)}
            </p>
            <p className="text-xs text-slate-600">
              KTV phụ trách:{" "}
              <strong>
                {staff
                  ? staff.full_name
                  : booking.staff_id
                    ? `KTV #${booking.staff_id.slice(0, 6)}`
                    : "Chưa gán"}
              </strong>
            </p>
          </div>

          <div className="flex flex-col items-end gap-1">
            <span
              className={cn(
                "rounded-full border px-2.5 py-0.5 text-[11px] font-semibold",
                meta.badgeClass
              )}
            >
              {meta.label}
            </span>
            <span className="text-xs font-bold text-foreground">
              {formatCurrency(booking.total_price)}
            </span>
          </div>
        </div>

        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {booking.items.map((item) => {
            const svc = serviceMap.get(item.service_id);
            return (
              <span
                key={item.id}
                className="inline-flex items-center gap-1 rounded bg-white/80 px-2 py-0.5 text-[11px] text-slate-700 border border-border"
              >
                {svc ? svc.name : "Dịch vụ"} ({item.duration_minutes}p •{" "}
                {item.customer_package_id
                  ? "Thẻ 0₫"
                  : formatCurrency(item.price)}
                )
              </span>
            );
          })}
        </div>

        {booking.note && (
          <p className="mt-2 rounded bg-white/60 px-2.5 py-1 text-xs italic text-slate-600">
            Ghi chú: {booking.note}
          </p>
        )}

        {meta.next.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-border/60 pt-2.5">
            <span className="text-[11px] font-medium text-muted-foreground mr-1">
              Đổi trạng thái nhanh:
            </span>
            {meta.next.map((nextSt) => {
              const nextMeta = BOOKING_STATUS_META[nextSt];
              return (
                <button
                  key={nextSt}
                  type="button"
                  disabled={statusBusyId === booking.id}
                  onClick={() => void handleStatusChange(booking.id, nextSt)}
                  className={cn(
                    "rounded-md border px-2.5 py-1 text-[11px] font-semibold transition hover:opacity-85 disabled:opacity-50",
                    nextMeta.badgeClass
                  )}
                >
                  → {nextMeta.label}
                </button>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-5">
      {/* Header & Actions */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">
            Lịch hẹn & Điều phối Kỹ thuật viên
          </h1>
          <p className="text-xs text-muted-foreground">
            Theo dõi lịch theo Ngày / Tuần, đổi trạng thái nhanh (tự động trừ
            buổi thẻ liệu trình khi Hoàn thành)
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => void loadBookings()}
          >
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
            Làm mới
          </Button>
          <Button size="sm" onClick={openCreateModal}>
            <Plus className="h-4 w-4" />
            Tạo lịch hẹn thủ công
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-lg border border-border bg-muted p-0.5">
              <button
                type="button"
                onClick={() => setViewMode("day")}
                className={cn(
                  "rounded-md px-3 py-1 text-xs font-semibold transition",
                  viewMode === "day"
                    ? "bg-card text-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                Theo Ngày
              </button>
              <button
                type="button"
                onClick={() => setViewMode("week")}
                className={cn(
                  "rounded-md px-3 py-1 text-xs font-semibold transition",
                  viewMode === "week"
                    ? "bg-card text-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                Theo Tuần
              </button>
            </div>

            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="icon"
                onClick={() =>
                  setSelectedDate(
                    addDaysISO(selectedDate, viewMode === "day" ? -1 : -7)
                  )
                }
                aria-label="Trước"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="w-40"
              />
              <Button
                variant="outline"
                size="icon"
                onClick={() =>
                  setSelectedDate(
                    addDaysISO(selectedDate, viewMode === "day" ? 1 : 7)
                  )
                }
                aria-label="Sau"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedDate(formatDateISOInVN())}
              >
                Hôm nay
              </Button>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={filterStaffId}
              onChange={(e) => setFilterStaffId(e.target.value)}
              className="h-9 rounded-md border border-input bg-background px-3 text-xs font-medium"
            >
              <option value="">Tất cả Kỹ thuật viên</option>
              {staffList.map((st) => (
                <option key={st.id} value={st.id}>
                  KTV: {st.full_name}
                </option>
              ))}
            </select>

            <select
              value={filterStatus}
              onChange={(e) =>
                setFilterStatus(e.target.value as BookingStatus | "")
              }
              className="h-9 rounded-md border border-input bg-background px-3 text-xs font-medium"
            >
              <option value="">Mọi trạng thái</option>
              {(Object.keys(BOOKING_STATUS_META) as BookingStatus[]).map(
                (st) => (
                  <option key={st} value={st}>
                    {BOOKING_STATUS_META[st].label} ({st})
                  </option>
                )
              )}
            </select>
          </div>
        </CardContent>
      </Card>

      {error && (
        <div className="rounded-lg border border-rose-300 bg-rose-50 px-4 py-2.5 text-xs font-medium text-rose-700">
          {error}
        </div>
      )}

      {/* Status Legend */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {(Object.keys(BOOKING_STATUS_META) as BookingStatus[]).map((st) => (
          <span
            key={st}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium",
              BOOKING_STATUS_META[st].badgeClass
            )}
          >
            {BOOKING_STATUS_META[st].label}
          </span>
        ))}
      </div>

      {/* Calendar Body */}
      {loading ? (
        <Card>
          <CardContent className="p-10 text-center text-sm text-muted-foreground">
            Đang tải lịch hẹn...
          </CardContent>
        </Card>
      ) : viewMode === "day" ? (
        <div className="space-y-3">
          {bookings.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center gap-2 py-12 text-center">
                <CalendarIcon className="h-8 w-8 text-muted-foreground" />
                <p className="text-sm font-medium text-foreground">
                  Không có lịch hẹn nào trong ngày {selectedDate}
                </p>
                <p className="text-xs text-muted-foreground">
                  Nhấn &ldquo;Tạo lịch hẹn thủ công&rdquo; để đặt lịch cho khách
                  gọi Hotline hoặc khách vãng lai.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {bookings.map((b) => renderBookingCard(b))}
            </div>
          )}
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-7">
          {weekDays.map((dayISO) => {
            const dayBookings = bookings.filter(
              (b) => formatDateISOInVN(new Date(b.start_time)) === dayISO
            );
            const isToday = dayISO === formatDateISOInVN();
            return (
              <div
                key={dayISO}
                className={cn(
                  "flex flex-col rounded-xl border border-border bg-card p-2.5 min-h-[260px]",
                  isToday && "ring-2 ring-primary/40"
                )}
              >
                <div className="mb-2 flex items-center justify-between border-b border-border pb-1.5">
                  <span className="text-xs font-bold text-foreground">
                    {dayISO.slice(5)}
                  </span>
                  <Badge variant={dayBookings.length > 0 ? "default" : "outline"}>
                    {dayBookings.length} lịch
                  </Badge>
                </div>
                <div className="space-y-2 flex-1">
                  {dayBookings.length === 0 ? (
                    <p className="py-6 text-center text-[11px] text-muted-foreground">
                      Trống
                    </p>
                  ) : (
                    dayBookings.map((b) => renderBookingCard(b))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Manual Booking Modal */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Tạo lịch hẹn thủ công tại quầy"
        description="Dành cho khách gọi Hotline hoặc khách vãng lai. Tự động kiểm tra ca làm việc KTV & giờ trống."
        maxWidthClass="max-w-2xl"
      >
        <form
          onSubmit={(e) => void handleCreateManualBooking(e)}
          className="space-y-4"
        >
          {modalError && (
            <div className="rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">
              {modalError}
            </div>
          )}

          {/* 1. Customer Selection or Quick Create */}
          <div className="space-y-2 rounded-lg border border-border bg-muted/30 p-3">
            <div className="flex items-center justify-between">
              <Label>1. Chọn Khách hàng</Label>
              <button
                type="button"
                onClick={() => setQuickNewCustomer(!quickNewCustomer)}
                className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
              >
                <UserPlus className="h-3.5 w-3.5" />
                {quickNewCustomer
                  ? "Chọn từ danh sách có sẵn"
                  : "+ Tạo nhanh khách mới"}
              </button>
            </div>

            {quickNewCustomer ? (
              <div className="grid gap-2 sm:grid-cols-2">
                <Input
                  placeholder="Họ và tên khách hàng *"
                  value={newCustomerName}
                  onChange={(e) => setNewCustomerName(e.target.value)}
                  required
                />
                <Input
                  placeholder="Số điện thoại (9-15 số) *"
                  value={newCustomerPhone}
                  onChange={(e) => setNewCustomerPhone(e.target.value)}
                  required
                />
                <Input
                  placeholder="Ghi chú da / dị ứng (tùy chọn)"
                  value={newCustomerNotes}
                  onChange={(e) => setNewCustomerNotes(e.target.value)}
                  className="sm:col-span-2"
                />
              </div>
            ) : (
              <select
                value={modalCustomerId}
                onChange={(e) => {
                  setModalCustomerId(e.target.value);
                  setSelectedLines((prev) =>
                    prev.filter((l) => l.customer_package_id === null)
                  );
                }}
                className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                required
              >
                <option value="">-- Chọn khách hàng --</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.full_name} — {c.phone_number}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* 2. Customer Active Packages (if any) */}
          {!quickNewCustomer && customerPackages.length > 0 && (
            <div className="space-y-2 rounded-lg border border-primary/30 bg-primary/5 p-3">
              <Label className="text-primary">
                Thẻ liệu trình đang hoạt động của khách (Chọn để trừ buổi, giá =
                0₫)
              </Label>
              <div className="grid gap-2 sm:grid-cols-2">
                {customerPackages.map((pkg) => {
                  const checked = selectedLines.some(
                    (l) =>
                      l.service_id === pkg.service_id &&
                      l.customer_package_id === pkg.id
                  );
                  return (
                    <label
                      key={pkg.id}
                      className={cn(
                        "flex cursor-pointer items-center justify-between rounded-md border p-2 text-xs transition",
                        checked
                          ? "border-primary bg-primary/10 font-semibold"
                          : "border-border bg-card hover:bg-muted/50"
                      )}
                    >
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() =>
                            toggleServiceSelection(pkg.service_id, pkg.id)
                          }
                          className="h-4 w-4 accent-primary"
                        />
                        <div>
                          <p>{pkg.package_name}</p>
                          <p className="text-[11px] text-muted-foreground">
                            Đã dùng {pkg.used_sessions}/{pkg.total_sessions} •
                            Còn {pkg.remaining_sessions} buổi
                          </p>
                        </div>
                      </div>
                      <Badge variant="success">0 ₫</Badge>
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          {/* 3. Services Selection */}
          <div className="space-y-2">
            <Label>
              2. Chọn Dịch vụ lẻ ({selectedLines.length} mục đã chọn)
            </Label>
            <div className="max-h-44 overflow-y-auto grid gap-2 sm:grid-cols-2 rounded-lg border border-border p-2.5">
              {activeServices.map((svc) => {
                const checked = selectedLines.some(
                  (l) =>
                    l.service_id === svc.id && l.customer_package_id === null
                );
                return (
                  <label
                    key={svc.id}
                    className={cn(
                      "flex cursor-pointer items-center justify-between rounded-md border p-2 text-xs transition",
                      checked
                        ? "border-primary bg-primary/10 font-semibold"
                        : "border-border bg-card hover:bg-muted/50"
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleServiceSelection(svc.id, null)}
                        className="h-4 w-4 accent-primary"
                      />
                      <div>
                        <p className="text-foreground">{svc.name}</p>
                        <p className="text-[11px] text-muted-foreground">
                          {svc.duration_minutes} phút •{" "}
                          {formatCurrency(svc.price)}
                        </p>
                      </div>
                    </div>
                  </label>
                );
              })}
            </div>
          </div>

          {/* 4. Date & Staff */}
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="modalDate">3. Ngày hẹn</Label>
              <Input
                id="modalDate"
                type="date"
                value={modalDate}
                onChange={(e) => setModalDate(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="modalStaff">
                4. Kỹ thuật viên (Để trống = Spa tự sắp xếp)
              </Label>
              <select
                id="modalStaff"
                value={modalStaffId}
                onChange={(e) => setModalStaffId(e.target.value)}
                className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="">✨ Spa tự sắp xếp KTV rảnh</option>
                {staffList
                  .filter((s) => s.is_active)
                  .map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.full_name} ({s.phone_number})
                    </option>
                  ))}
              </select>
            </div>
          </div>

          {/* 5. Available Slots */}
          <div className="space-y-2">
            <Label>5. Chọn Khung giờ trống khả dụng (Available Slots)</Label>
            {selectedLines.length === 0 ? (
              <p className="rounded-lg border border-dashed border-border p-3 text-center text-xs text-muted-foreground">
                Hãy chọn ít nhất 1 dịch vụ ở trên để hệ thống tính toán giờ
                trống.
              </p>
            ) : slotsLoading ? (
              <p className="rounded-lg border border-border p-3 text-center text-xs text-muted-foreground">
                Đang tìm khung giờ trống...
              </p>
            ) : availableSlots.length === 0 ? (
              <p className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-center text-xs text-amber-800">
                Không còn khung giờ trống nào trong ngày {modalDate} phù hợp với
                thời lượng dịch vụ đã chọn.
              </p>
            ) : (
              <div className="max-h-40 overflow-y-auto grid grid-cols-3 gap-2 sm:grid-cols-5 rounded-lg border border-border p-2.5">
                {availableSlots.map((slot) => {
                  const active = selectedSlotStart === slot.start_time;
                  return (
                    <button
                      key={slot.start_time}
                      type="button"
                      onClick={() => setSelectedSlotStart(slot.start_time)}
                      className={cn(
                        "flex flex-col items-center rounded-md border px-2 py-1.5 text-xs font-medium transition",
                        active
                          ? "border-primary bg-primary text-primary-foreground shadow-xs"
                          : "border-border bg-card text-foreground hover:bg-accent"
                      )}
                    >
                      <span>{formatTimeVN(slot.start_time)}</span>
                      <span
                        className={cn(
                          "text-[10px]",
                          active
                            ? "text-primary-foreground/80"
                            : "text-muted-foreground"
                        )}
                      >
                        {slot.available_staff_ids.length} KTV rảnh
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* 6. Note */}
          <div className="space-y-1.5">
            <Label htmlFor="modalNote">Ghi chú lịch hẹn</Label>
            <Textarea
              id="modalNote"
              placeholder="Yêu cầu đặc biệt của khách..."
              value={modalNote}
              onChange={(e) => setModalNote(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setModalOpen(false)}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              disabled={creatingBooking || !selectedSlotStart}
            >
              {creatingBooking ? "Đang lưu lịch..." : "Xác nhận tạo lịch"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
