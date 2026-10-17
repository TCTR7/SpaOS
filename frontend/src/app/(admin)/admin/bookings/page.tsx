"use client";

import * as React from "react";
import {
  Calendar as CalendarIcon,
  CalendarClock,
  CalendarPlus,
  ChevronLeft,
  ChevronRight,
  Clock,
  Plus,
  RefreshCw,
  Sparkles,
  Ticket,
  Trash2,
  UserPlus,
} from "lucide-react";
import {
  createBooking,
  rescheduleBooking,
  createCustomer,
  fetchAvailableSlots,
  fetchBookings,
  fetchCustomerPackages,
  fetchCustomers,
  fetchServices,
  fetchStaffList,
  issueCustomerPackage,
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
  formatDateTimeVN,
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

interface ScheduledSessionRow {
  rowId: string;
  date: string;
  slots: SlotItem[];
  slotsLoading: boolean;
  selectedSlotStart: string;
}

function createEmptySessionRow(dateISO: string): ScheduledSessionRow {
  return {
    rowId: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    date: dateISO,
    slots: [],
    slotsLoading: false,
    selectedSlotStart: "",
  };
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
  const [intervalDays, setIntervalDays] = React.useState<number>(7);
  const [sessionRows, setSessionRows] = React.useState<ScheduledSessionRow[]>(
    () => [createEmptySessionRow(formatDateISOInVN())]
  );
  const [modalNote, setModalNote] = React.useState<string>("");
  const [modalError, setModalError] = React.useState<string | null>(null);
  const [creatingBooking, setCreatingBooking] = React.useState<boolean>(false);

  const [transferCustomer, setTransferCustomer] = React.useState(false);

  // Reschedule / Edit Booking Modal State
  const [rescheduleTarget, setRescheduleTarget] =
    React.useState<BookingRecord | null>(null);
  const [rescheduleDate, setRescheduleDate] = React.useState<string>(() =>
    formatDateISOInVN()
  );
  const [rescheduleStaffId, setRescheduleStaffId] =
    React.useState<string>("");
  const [rescheduleSlots, setRescheduleSlots] = React.useState<SlotItem[]>([]);
  const [rescheduleSlotsLoading, setRescheduleSlotsLoading] =
    React.useState<boolean>(false);
  const [rescheduleSlotStart, setRescheduleSlotStart] =
    React.useState<string>("");
  const [rescheduleNote, setRescheduleNote] = React.useState<string>("");
  const [rescheduleError, setRescheduleError] = React.useState<string | null>(
    null
  );
  const [rescheduleSaving, setRescheduleSaving] =
    React.useState<boolean>(false);

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

  // Calculate max sessions allowed by selected treatment package(s) or multi-session service(s)
  const maxCourseSessions = React.useMemo((): number => {
    if (selectedLines.length === 0) return 1;
    let maxSessions = 1;
    for (const line of selectedLines) {
      if (line.customer_package_id) {
        const pkg = customerPackages.find(
          (p) => p.id === line.customer_package_id
        );
        if (pkg && pkg.remaining_sessions > maxSessions) {
          maxSessions = pkg.remaining_sessions;
        }
      } else {
        const svc = serviceMap.get(line.service_id);
        if (svc && svc.is_package && svc.total_sessions > maxSessions) {
          maxSessions = svc.total_sessions;
        }
      }
    }
    return Math.min(maxSessions, 20);
  }, [selectedLines, customerPackages, serviceMap]);

  const hasMultiSessionSelection = maxCourseSessions > 1;

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
      const scopedData = data;
      const sorted = [...scopedData].sort(
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
  }, [viewMode, selectedDate, weekDays, filterStaffId, filterStatus, user]);

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

  const selectedServiceIdsKey = React.useMemo(
    () => selectedLines.map((l) => l.service_id).join(","),
    [selectedLines]
  );

  const sessionDatesKey = React.useMemo(
    () => sessionRows.map((r) => `${r.rowId}:${r.date}`).join("|"),
    [sessionRows]
  );

  // Fetch available slots for each scheduled session row whenever services, staff, or row dates change
  React.useEffect(() => {
    if (!modalOpen || selectedLines.length === 0) {
      setSessionRows((prev) =>
        prev.map((r) => ({
          ...r,
          slots: [],
          slotsLoading: false,
          selectedSlotStart: "",
        }))
      );
      return;
    }

    let cancelled = false;
    const serviceIds = selectedLines.map((l) => l.service_id);

    setSessionRows((prev) =>
      prev.map((r) => ({ ...r, slotsLoading: true }))
    );

    void (async () => {
      const results = await Promise.all(
        sessionRows.map(async (row) => {
          if (!row.date) {
            return { rowId: row.rowId, slots: [] as SlotItem[] };
          }
          try {
            const res = await fetchAvailableSlots({
              date: row.date,
              service_ids: serviceIds,
              staff_id: modalStaffId || null,
            });
            return { rowId: row.rowId, slots: res.slots };
          } catch {
            return { rowId: row.rowId, slots: [] as SlotItem[] };
          }
        })
      );

      if (cancelled) return;

      // Preferred HH:mm from the first session row if already selected
      setSessionRows((prev) => {
        const firstPreferredTime = prev[0]?.selectedSlotStart
          ? formatTimeVN(prev[0].selectedSlotStart)
          : "";

        return prev.map((row) => {
          const found = results.find((item) => item.rowId === row.rowId);
          const slots = found ? found.slots : [];
          let nextSelected = row.selectedSlotStart;

          if (slots.length === 0) {
            nextSelected = "";
          } else if (!slots.some((s) => s.start_time === nextSelected)) {
            const matchingTimeSlot = firstPreferredTime
              ? slots.find((s) => formatTimeVN(s.start_time) === firstPreferredTime)
              : undefined;
            nextSelected = matchingTimeSlot
              ? matchingTimeSlot.start_time
              : slots[0].start_time;
          }

          return {
            ...row,
            slots,
            slotsLoading: false,
            selectedSlotStart: nextSelected,
          };
        });
      });
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modalOpen, selectedServiceIdsKey, modalStaffId, sessionDatesKey]);

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
        const res = await fetchAvailableSlots({
          date: rescheduleDate,
          service_ids: rescheduleTarget.items.map((i) => i.service_id),
          staff_id: rescheduleStaffId || null,
        });
        if (!cancelled) {
          setRescheduleSlots(res.slots);
          const preferredTime = formatTimeVN(rescheduleTarget.start_time);
          const sameTimeSlot = res.slots.find(
            (s) => formatTimeVN(s.start_time) === preferredTime
          );
          setRescheduleSlotStart(
            sameTimeSlot?.start_time || res.slots[0]?.start_time || ""
          );
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
  }, [rescheduleTarget, rescheduleDate, rescheduleStaffId]);

  const openRescheduleModal = (booking: BookingRecord): void => {
    setTransferCustomer(false);
    setRescheduleError(null);
    setRescheduleTarget(booking);
    setRescheduleDate(formatDateISOInVN(new Date(booking.start_time)));
    setRescheduleStaffId(booking.staff_id || "");
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

    setRescheduleSaving(true);
    setRescheduleError(null);
    try {
      await rescheduleBooking(rescheduleTarget.id, {
        staff_id: rescheduleStaffId || null,
        transfer_customer: user?.role === "ADMIN" && transferCustomer,
        start_time: rescheduleSlotStart,
        note: rescheduleNote.trim() || null,
      });

      setRescheduleTarget(null);
      await loadBookings();
    } catch (err) {
      setRescheduleError(
        err instanceof Error
          ? err.message
          : "Không thể dời lịch hẹn. Vui lòng thử lại hoặc chọn khung giờ khác."
      );
      await loadBookings();
    } finally {
      setRescheduleSaving(false);
    }
  };

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
    setIntervalDays(7);
    setSessionRows([createEmptySessionRow(selectedDate)]);
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

  const handleSessionDateChange = (rowId: string, newDate: string): void => {
    setSessionRows((prev) =>
      prev.map((r) =>
        r.rowId === rowId ? { ...r, date: newDate, selectedSlotStart: "" } : r
      )
    );
  };

  const handleSessionSlotSelect = (rowId: string, slotStart: string): void => {
    setSessionRows((prev) =>
      prev.map((r) =>
        r.rowId === rowId ? { ...r, selectedSlotStart: slotStart } : r
      )
    );
  };

  const handleAddSessionRow = (): void => {
    setSessionRows((prev) => {
      if (prev.length >= maxCourseSessions) return prev;
      const lastDate = prev[prev.length - 1]?.date || selectedDate;
      const nextDate = addDaysISO(lastDate, intervalDays);
      return [...prev, createEmptySessionRow(nextDate)];
    });
  };

  const handleAutoGenerateCourseSessions = (count: number): void => {
    const targetCount = Math.min(Math.max(1, count), maxCourseSessions);
    setSessionRows((prev) => {
      const baseDate = prev[0]?.date || selectedDate;
      const rows: ScheduledSessionRow[] = [];
      for (let i = 0; i < targetCount; i++) {
        if (i === 0 && prev[0]) {
          rows.push(prev[0]);
        } else {
          rows.push(createEmptySessionRow(addDaysISO(baseDate, i * intervalDays)));
        }
      }
      return rows;
    });
  };

  const handleRemoveSessionRow = (rowId: string): void => {
    setSessionRows((prev) => {
      if (prev.length <= 1) return prev;
      return prev.filter((r) => r.rowId !== rowId);
    });
  };

  const handleCreateManualBooking = async (
    e: React.FormEvent<HTMLFormElement>
  ): Promise<void> => {
    e.preventDefault();
    setModalError(null);

    if (selectedLines.length === 0) {
      setModalError("Vui lòng chọn ít nhất 1 dịch vụ hoặc thẻ liệu trình.");
      return;
    }

    for (let i = 0; i < sessionRows.length; i++) {
      if (!sessionRows[i].date || !sessionRows[i].selectedSlotStart) {
        setModalError(
          `Vui lòng chọn khung giờ trống hợp lệ cho Buổi ${i + 1} (ngày ${sessionRows[i].date || "chưa chọn"}).`
        );
        return;
      }
    }

    // Check duplicate start_time across session rows
    const seenStarts = new Set<string>();
    for (let i = 0; i < sessionRows.length; i++) {
      const st = sessionRows[i].selectedSlotStart;
      if (seenStarts.has(st)) {
        setModalError(
          `Buổi ${i + 1} bị trùng ngày giờ với một buổi khác trong danh sách. Vui lòng chọn ngày/khung giờ khác nhau.`
        );
        return;
      }
      seenStarts.add(st);
    }

    if (sessionRows.length > maxCourseSessions) {
      setModalError(
        `Số buổi lên lịch (${sessionRows.length}) vượt quá số buổi khả dụng của lộ trình (${maxCourseSessions} buổi).`
      );
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

      // If any selected service is a multi-session package (is_package=true) without an existing customer_package_id,
      // automatically issue a new CustomerPackage for the customer so all sessions track under that package!
      const resolvedItems: SelectedServiceLine[] = [];
      for (const line of selectedLines) {
        const svc = serviceMap.get(line.service_id);
        if (svc && svc.is_package && !line.customer_package_id) {
          const issuedPkg = await issueCustomerPackage({
            customer_id: customerId,
            service_id: svc.id,
            package_name: svc.name,
            total_sessions: svc.total_sessions,
          });
          resolvedItems.push({
            service_id: svc.id,
            customer_package_id: issuedPkg.id,
          });
        } else {
          resolvedItems.push(line);
        }
      }

      const sortedRows = [...sessionRows].sort(
        (a, b) =>
          new Date(a.selectedSlotStart).getTime() -
          new Date(b.selectedSlotStart).getTime()
      );

      for (let i = 0; i < sortedRows.length; i++) {
        const row = sortedRows[i];
        const sessionPrefix =
          sortedRows.length > 1
            ? `[Buổi ${i + 1}/${sortedRows.length}]`
            : "";
        const combinedNote = [sessionPrefix, modalNote.trim()]
          .filter(Boolean)
          .join(" ");

        await createBooking({
          customer_id: customerId,
          staff_id: modalStaffId || null,
          start_time: row.selectedSlotStart,
          note: combinedNote || null,
          items: resolvedItems,
        });
      }

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

        {((meta.next.length > 0) || (booking.status === "PENDING" || booking.status === "CONFIRMED")) && (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-border/60 pt-2.5">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[11px] font-medium text-muted-foreground mr-1">
                Trạng thái:
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

            {(user?.role === "ADMIN" || user?.role === "STAFF") &&
              (booking.status === "PENDING" || booking.status === "CONFIRMED") && (
                <button
                  type="button"
                  onClick={() => openRescheduleModal(booking)}
                  className="inline-flex items-center gap-1 rounded-md border border-sky-300 bg-sky-50 px-2.5 py-1 text-[11px] font-semibold text-sky-700 transition hover:bg-sky-100"
                  title="Dời lịch sang ngày/giờ khác hoặc đổi KTV"
                >
                  <CalendarClock className="h-3.5 w-3.5" />
                  Đổi ngày / giờ / KTV
                </button>
              )}
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
                  <Badge
                    variant={dayBookings.length > 0 ? "default" : "outline"}
                  >
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
        description="Hỗ trợ đặt lịch đơn lẻ hoặc lên lịch hẹn nhiều ngày liên tiếp cho gói lộ trình nhiều buổi."
        maxWidthClass="max-w-3xl"
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
                0₫ — hỗ trợ đặt lịch trước nhiều ngày)
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
                            Còn <strong>{pkg.remaining_sessions} buổi</strong>
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

          {/* 3. Services & Package Courses Selection */}
          <div className="space-y-2">
            <Label>
              2. Chọn Dịch vụ lẻ hoặc Gói Liệu trình mới ({selectedLines.length}{" "}
              mục đã chọn)
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
                    <div className="flex items-center gap-2 min-w-0">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleServiceSelection(svc.id, null)}
                        className="h-4 w-4 shrink-0 accent-primary"
                      />
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <p className="text-foreground truncate">{svc.name}</p>
                          {svc.is_package && (
                            <Badge variant="default" className="text-[10px] px-1.5 py-0">
                              Lộ trình {svc.total_sessions} buổi
                            </Badge>
                          )}
                        </div>
                        <p className="text-[11px] text-muted-foreground">
                          {svc.duration_minutes} phút/buổi •{" "}
                          {formatCurrency(svc.price)}
                        </p>
                      </div>
                    </div>
                  </label>
                );
              })}
            </div>
          </div>

          {/* 4. Staff Preference & Multi-Session Course Toolbar */}
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="modalStaff">
                3. Kỹ thuật viên phụ trách (Để trống = Spa tự sắp xếp)
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

            {hasMultiSessionSelection && (
              <div className="space-y-1.5">
                <Label htmlFor="intervalSelect">
                  Chu kỳ giãn cách giữa các buổi hẹn
                </Label>
                <select
                  id="intervalSelect"
                  value={intervalDays}
                  onChange={(e) => setIntervalDays(Number(e.target.value))}
                  className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  <option value={1}>Mỗi ngày (Cách 1 ngày)</option>
                  <option value={2}>Cách 2 ngày / buổi</option>
                  <option value={3}>Cách 3 ngày / buổi</option>
                  <option value={5}>Cách 5 ngày / buổi</option>
                  <option value={7}>Hàng tuần (Cách 7 ngày / buổi)</option>
                  <option value={14}>Cách 2 tuần (14 ngày / buổi)</option>
                </select>
              </div>
            )}
          </div>

          {/* Multi-Session Quick Action Banner */}
          {hasMultiSessionSelection && (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-primary/40 bg-primary/5 px-3 py-2.5">
              <div className="flex items-center gap-2 text-xs">
                <Sparkles className="h-4 w-4 text-primary shrink-0" />
                <span>
                  Lộ trình cho phép đặt tối đa{" "}
                  <strong className="text-primary">
                    {maxCourseSessions} buổi
                  </strong>
                  . Đang lên lịch:{" "}
                  <strong>
                    {sessionRows.length}/{maxCourseSessions} buổi
                  </strong>
                  .
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                {sessionRows.length < maxCourseSessions && (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={handleAddSessionRow}
                    className="h-7 text-xs"
                  >
                    <CalendarPlus className="h-3.5 w-3.5" />+ Thêm ngày hẹn
                    (Buổi {sessionRows.length + 1})
                  </Button>
                )}
                {maxCourseSessions >= 3 && (
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() =>
                      handleAutoGenerateCourseSessions(
                        Math.min(3, maxCourseSessions)
                      )
                    }
                    className="h-7 text-xs"
                  >
                    Rải nhanh 3 buổi
                  </Button>
                )}
                <Button
                  type="button"
                  size="sm"
                  onClick={() =>
                    handleAutoGenerateCourseSessions(
                      Math.min(maxCourseSessions, 10)
                    )
                  }
                  className="h-7 text-xs"
                >
                  ⚡ Lên lịch đủ {Math.min(maxCourseSessions, 10)} buổi
                </Button>
              </div>
            </div>
          )}

          {/* 5. Multi-Day Session Rows (Date + Available Slots per Session) */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>
                4. Chọn Ngày hẹn & Khung giờ trống khả dụng cho từng buổi (
                {sessionRows.length} buổi)
              </Label>
            </div>

            {selectedLines.length === 0 ? (
              <p className="rounded-lg border border-dashed border-border p-3 text-center text-xs text-muted-foreground">
                Hãy chọn ít nhất 1 dịch vụ hoặc thẻ liệu trình ở trên để hệ
                thống tính toán ngày và giờ trống.
              </p>
            ) : (
              <div className="max-h-80 space-y-3 overflow-y-auto pr-1">
                {sessionRows.map((row, index) => (
                  <div
                    key={row.rowId}
                    className="rounded-lg border border-border bg-card p-3 space-y-2.5 shadow-2xs"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="default">
                          Buổi {index + 1}
                          {sessionRows.length > 1
                            ? `/${sessionRows.length}`
                            : ""}
                        </Badge>
                        <div className="flex items-center gap-1.5">
                          <Label
                            htmlFor={
                              index === 0 ? "modalDate" : `modalDate-${index}`
                            }
                            className="text-xs whitespace-nowrap"
                          >
                            Ngày hẹn:
                          </Label>
                          <Input
                            id={
                              index === 0 ? "modalDate" : `modalDate-${index}`
                            }
                            type="date"
                            value={row.date}
                            onChange={(e) =>
                              handleSessionDateChange(row.rowId, e.target.value)
                            }
                            className="h-8 w-40 text-xs"
                            required
                          />
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {row.selectedSlotStart && (
                          <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 rounded px-2 py-0.5">
                            Đã chọn: {formatTimeVN(row.selectedSlotStart)} (
                            {row.date})
                          </span>
                        )}
                        {sessionRows.length > 1 && (
                          <button
                            type="button"
                            onClick={() => handleRemoveSessionRow(row.rowId)}
                            className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-rose-600 hover:bg-rose-50"
                            title="Xóa buổi hẹn này"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                            Xóa buổi
                          </button>
                        )}
                      </div>
                    </div>

                    {row.slotsLoading ? (
                      <p className="rounded-md border border-border p-2.5 text-center text-xs text-muted-foreground">
                        Đang tìm khung giờ trống cho ngày {row.date}...
                      </p>
                    ) : row.slots.length === 0 ? (
                      <p className="rounded-md border border-amber-300 bg-amber-50 p-2.5 text-center text-xs text-amber-800">
                        Không còn khung giờ trống nào trong ngày {row.date} phù
                        hợp với thời lượng dịch vụ. Hãy chọn ngày khác.
                      </p>
                    ) : (
                      <div className="max-h-32 overflow-y-auto grid grid-cols-3 gap-1.5 sm:grid-cols-6 rounded-md border border-border bg-muted/20 p-2">
                        {row.slots.map((slot) => {
                          const active =
                            row.selectedSlotStart === slot.start_time;
                          return (
                            <button
                              key={slot.start_time}
                              type="button"
                              onClick={() =>
                                handleSessionSlotSelect(
                                  row.rowId,
                                  slot.start_time
                                )
                              }
                              className={cn(
                                "flex flex-col items-center rounded border px-2 py-1 text-xs font-medium transition",
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
                ))}
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
              disabled={
                creatingBooking ||
                selectedLines.length === 0 ||
                sessionRows.some((r) => !r.selectedSlotStart)
              }
            >
              {creatingBooking
                ? "Đang lưu lịch..."
                : sessionRows.length > 1
                  ? `Xác nhận tạo ${sessionRows.length} buổi hẹn`
                  : "Xác nhận tạo lịch"}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Reschedule / Edit Booking Modal */}
      <Modal
        open={Boolean(rescheduleTarget)}
        onClose={() => setRescheduleTarget(null)}
        title="Chỉnh sửa & Dời lịch hẹn"
        description="Thay đổi ngày hẹn, khung giờ trống hoặc Kỹ thuật viên phụ trách. Suất thẻ liệu trình (nếu có) được bảo lưu nguyên vẹn."
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
                Khách hàng:{" "}
                {customerMap.get(rescheduleTarget.customer_id)?.full_name ||
                  rescheduleTarget.customer_id}
              </p>
              <p className="text-muted-foreground">
                Dịch vụ:{" "}
                {rescheduleTarget.items
                  .map((i) => serviceMap.get(i.service_id)?.name || "Dịch vụ")
                  .join(", ")}
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="rescheduleDateAdmin">1. Ngày hẹn mới</Label>
                <Input
                  id="rescheduleDateAdmin"
                  type="date"
                  value={rescheduleDate}
                  onChange={(e) => setRescheduleDate(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="rescheduleStaffAdmin">2. Kỹ thuật viên phụ trách</Label>
                <select
                  id="rescheduleStaffAdmin"
                  value={rescheduleStaffId}
                  onChange={(e) => { setRescheduleStaffId(e.target.value); setTransferCustomer(false); }}
                  className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  disabled={user?.role === "STAFF"}
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

            {user?.role === "ADMIN" && (
              <div className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs">
                <label className="flex items-center gap-2">
                  <input id="transferCustomer" type="checkbox" checked={transferCustomer}
                    onChange={(e) => setTransferCustomer(e.target.checked)} />
                  Chuyển quyền hồ sơ cho KTV của giờ hẹn mới
                </label>
                <p>Nếu bỏ chọn, người phụ trách hồ sơ giữ nguyên; KTV làm thay chưa được quyền xem/sửa hồ sơ khách.</p>
              </div>
            )}
            <div className="space-y-2">
              <Label>3. Chọn khung giờ trống mới</Label>
              {rescheduleSlotsLoading ? (
                <p className="rounded-lg border border-border p-3 text-center text-xs text-muted-foreground">
                  Đang tìm khung giờ trống ngày {rescheduleDate}...
                </p>
              ) : rescheduleSlots.length === 0 ? (
                <p className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-center text-xs text-amber-800">
                  Không còn khung giờ trống nào trong ngày {rescheduleDate}. Vui lòng chọn ngày khác.
                </p>
              ) : (
                <div className="max-h-40 overflow-y-auto grid grid-cols-3 gap-2 sm:grid-cols-5 rounded-lg border border-border p-2">
                  {rescheduleSlots.map((slot) => {
                    const active = rescheduleSlotStart === slot.start_time;
                    return (
                      <button
                        key={slot.start_time}
                        type="button"
                        onClick={() => setRescheduleSlotStart(slot.start_time)}
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

            <div className="space-y-1.5">
              <Label htmlFor="rescheduleNoteAdmin">Ghi chú dời lịch</Label>
              <Textarea
                id="rescheduleNoteAdmin"
                value={rescheduleNote}
                onChange={(e) => setRescheduleNote(e.target.value)}
                placeholder="Lý do đổi lịch, yêu cầu của khách..."
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setRescheduleTarget(null)}
              >
                Hủy
              </Button>
              <Button
                type="submit"
                disabled={rescheduleSaving || rescheduleSlotsLoading || !rescheduleSlotStart}
              >
                {rescheduleSaving ? "Đang lưu..." : "Xác nhận đổi lịch"}
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
