"use client";

import * as React from "react";
import { GuestInbox } from "@/components/admin/guest-inbox";
import { BookingHandover } from "@/components/admin/booking-handover";
import { customerDetail } from "@/lib/experience-api";
import { useRefreshOnReturn } from "@/lib/use-refresh-on-return";
import { eligibleStaff } from "@/lib/staff-skills";
import { AvailabilityFinder } from "@/components/admin/availability-finder";
import { useManualBatch } from "@/lib/use-manual-batch";
import { useAvailableSlots } from "@/lib/use-available-slots";
import { ReschedulePreview } from "@/components/reschedule-preview";
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
  ApiError,
  rescheduleBooking,
  fetchAvailableSlots,
  fetchBookingPage,
  fetchBookingDetail,
  fetchCustomerPage,
  fetchCustomerPackages,
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
  slotsError: string | null;
  slotsScope: string;
  selectedSlotStart: string;
}

function createEmptySessionRow(dateISO: string): ScheduledSessionRow {
  return {
    rowId: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    date: dateISO,
    slots: [],
    slotsLoading: false,
    slotsError: null,
    slotsScope: "",
    selectedSlotStart: "",
  };
}

export default function AdminBookingsPage(): React.ReactElement {
  const { user } = useAdminAuth();

  const [showAvailability, setShowAvailability] = React.useState(false);
  const [staffScope, setStaffScope] = React.useState<"performing" | "accessible">("performing");
  const [viewMode, setViewMode] = React.useState<"day" | "week">("day");
  const [selectedDate, setSelectedDate] = React.useState<string>(() =>
    formatDateISOInVN()
  );
  const [filterStaffId, setFilterStaffId] = React.useState<string>("");
  const [filterStatus, setFilterStatus] = React.useState<BookingStatus | "">(
    ""
  );

  const effectiveStaffId = user?.role === "STAFF" && staffScope === "performing" ? user.id : filterStaffId;
  const scopeKey = JSON.stringify([user?.tenant_id, user?.id, user?.role,
    viewMode, selectedDate, effectiveStaffId, filterStatus]);
  const referenceScope = JSON.stringify([user?.tenant_id, user?.id, user?.role]);
  const scopeRef = React.useRef(scopeKey);
  const referenceScopeRef = React.useRef(referenceScope);
  scopeRef.current = scopeKey;
  referenceScopeRef.current = referenceScope;
  const bookingRequest = React.useRef(0);
  const referenceRequest = React.useRef(0);
  const calendarReturnPosition = React.useRef<{ scope: string; x: number; y: number } | null>(null);
  const mounted = React.useRef(true);
  const [bookingState, setBookingState] = React.useState<{
    scope: string; rows: BookingRecord[]; loading: boolean; error: string | null;
  }>({ scope: "", rows: [], loading: true, error: null });
  const [bookingPage, setBookingPage] = React.useState({ scope: "", nextOffset: null as number | null, loading: false, error: null as string | null });
  const bookingPageRef = React.useRef(bookingPage);
  bookingPageRef.current = bookingPage;
  const [referenceData, setReferenceData] = React.useState<{
    scope: string; services: ServiceItem[]; customers: UserDetail[]; staff: UserDetail[];
    loading: boolean; errors: string[]; servicesReady: boolean; customersReady: boolean; staffReady: boolean;
  }>({ scope: "", services: [], customers: [], staff: [], loading: true, errors: [],
    servicesReady: false, customersReady: false, staffReady: false });
  const bookings = bookingState.scope === scopeKey ? bookingState.rows : [];
  const loading = bookingState.scope !== scopeKey || bookingState.loading;
  const bookingLoadError = bookingState.scope === scopeKey ? bookingState.error : null;
  const services = referenceData.scope === referenceScope ? referenceData.services : [];
  const customers = referenceData.scope === referenceScope ? referenceData.customers : [];
  const staffList = referenceData.scope === referenceScope ? referenceData.staff : [];
  const referencesReady = referenceData.scope === referenceScope && !referenceData.loading
    && referenceData.servicesReady && referenceData.customersReady && referenceData.staffReady;
  const canReschedule = referenceData.scope === referenceScope && !referenceData.loading
    && referenceData.servicesReady && referenceData.staffReady;
  const weekScroller = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      bookingRequest.current += 1;
      referenceRequest.current += 1;
    };
  }, []);
  React.useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const day = params.get("date");
    const status = params.get("status");
    if (day && /^\d{4}-\d{2}-\d{2}$/.test(day)) {
      const parsed = new Date(day + "T00:00:00Z");
      if (Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === day) setSelectedDate(day);
    }
    if (status && Object.prototype.hasOwnProperty.call(BOOKING_STATUS_META, status)) setFilterStatus(status as BookingStatus);
  }, []);
  const [error, setError] = React.useState<string | null>(null);
  const [manualNotice, setManualNotice] = React.useState({ scope: "", text: "" });
  const [statusBusyId, setStatusBusyId] = React.useState<string | null>(null);
  const [detailTarget, setDetailTarget] = React.useState<BookingRecord | null>(null);
  React.useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("booking_id");
    if (!user || !id) return;
    let cancelled = false;
    void fetchBookingDetail(id).then((booking) => { if (!cancelled) setDetailTarget(booking); })
      .catch(() => { if (!cancelled) setError("Không mở được lịch này. Lịch có thể không còn trong phạm vi bạn được xem. Hãy làm mới lịch hoặc liên hệ chủ spa."); });
    return () => { cancelled = true; };
  }, [user?.id, user?.tenant_id]);
  const [statusConfirmation, setStatusConfirmation] = React.useState<BookingStatus | null>(null);

  // Manual Booking Modal State
  const [showCourse, setShowCourse] = React.useState(false);
  const [handoverDirty, setHandoverDirty] = React.useState(false);
  const [handoverBusy, setHandoverBusy] = React.useState(false);
  const [updatedAt, setUpdatedAt] = React.useState("");
  const [modalOpen, setModalOpen] = React.useState<boolean>(false);
  const [modalCustomerId, setModalCustomerId] = React.useState<string>("");
  const [customerQuery, setCustomerQuery] = React.useState("");
  const customerLookupRequest = React.useRef(0);
  const [customerPage, setCustomerPage] = React.useState({ query: "", nextOffset: null as number | null, loading: false, error: null as string | null });
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

  const [transferCustomer, setTransferCustomer] = React.useState(false);

  // Reschedule / Edit Booking Modal State
  const [rescheduleTarget, setRescheduleTarget] =
    React.useState<BookingRecord | null>(null);
  const [rescheduleDate, setRescheduleDate] = React.useState<string>(() =>
    formatDateISOInVN()
  );
  const [rescheduleStaffId, setRescheduleStaffId] =
    React.useState<string>("");
  const [rescheduleNote, setRescheduleNote] = React.useState<string>("");
  const [rescheduleError, setRescheduleError] = React.useState<string | null>(
    null
  );
  const [rescheduleSaving, setRescheduleSaving] =
    React.useState<boolean>(false);
  const rescheduleFlight = React.useRef(false);

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
    const limits: number[] = [];
    for (const line of selectedLines) {
      if (line.customer_package_id) {
        const pkg = customerPackages.find((item) => item.id === line.customer_package_id);
        if (pkg) limits.push(pkg.available_sessions ?? pkg.remaining_sessions);
      } else {
        const service = serviceMap.get(line.service_id);
        if (service?.is_package) limits.push(service.total_sessions);
      }
    }
    return limits.length ? Math.min(20, ...limits) : 1;
  }, [selectedLines, customerPackages, serviceMap]);

  const hasMultiSessionSelection = maxCourseSessions > 1;

  const loadReferenceData = React.useCallback(async (): Promise<void> => {
    if (!user || !mounted.current || referenceScopeRef.current !== referenceScope) return;
    const request = ++referenceRequest.current;
    customerLookupRequest.current += 1;
    setReferenceData((previous) => ({ ...previous, scope: referenceScope,
      services: previous.scope === referenceScope ? previous.services : [],
      customers: previous.scope === referenceScope ? previous.customers : [],
      staff: previous.scope === referenceScope ? previous.staff : [],
      loading: true, errors: [], servicesReady: false, customersReady: false, staffReady: false }));
    const staffTask = user.role === "ADMIN" ? fetchStaffList() : Promise.resolve<UserDetail[]>([{
      id: user.id, tenant_id: user.tenant_id, role: user.role, full_name: user.full_name,
      phone_number: user.phone_number, notes: null, is_active: user.is_active,
      created_at: new Date().toISOString(),
    }]);
    const [svc, cust, staff] = await Promise.allSettled([
      fetchServices(), fetchCustomerPage({ limit: 50 }), staffTask,
    ]);
    if (!mounted.current || request !== referenceRequest.current
        || referenceScopeRef.current !== referenceScope) return;
    const errors: string[] = [];
    if (svc.status === "rejected") errors.push("Danh mục dịch vụ");
    if (cust.status === "rejected") errors.push("Tên khách hàng");
    if (staff.status === "rejected") errors.push("Danh sách KTV");
    setReferenceData({ scope: referenceScope, loading: false, errors,
      services: svc.status === "fulfilled" ? svc.value : [],
      customers: cust.status === "fulfilled" ? cust.value.items : [],
      staff: staff.status === "fulfilled" ? staff.value : [],
      servicesReady: svc.status === "fulfilled", customersReady: cust.status === "fulfilled",
      staffReady: staff.status === "fulfilled" });
    setCustomerPage({ query: "", nextOffset: cust.status === "fulfilled" ? cust.value.nextOffset : null, loading: false, error: null });
  }, [user, referenceScope]);

  const liveCustomerPage = React.useRef(customerPage); liveCustomerPage.current = customerPage;
  React.useEffect(() => {
    if (!modalOpen || quickNewCustomer || !referencesReady || customerQuery.trim() === customerPage.query) return;
    const timer = window.setTimeout(() => { if (customerQuery.trim() !== liveCustomerPage.current.query) void searchCustomers(); }, 300);
    return () => window.clearTimeout(timer);
    // Only typing starts this search; result updates must not start a crawl.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customerQuery, modalOpen, quickNewCustomer, referencesReady]);
  const searchCustomers = async (append = false): Promise<void> => {
    if (!referencesReady || (append && customerPage.loading)) return;
    const query = append ? customerPage.query : customerQuery.trim();
    const offset = append ? customerPage.nextOffset : 0;
    if (offset === null) return;
    const request = ++customerLookupRequest.current;
    setCustomerPage((previous) => ({ ...previous, query, nextOffset: append ? previous.nextOffset : null, loading: true, error: null }));
    if (!append) {
      setModalCustomerId(""); setCustomerPackages([]);
      setReferenceData((previous) => ({ ...previous, customers: [] }));
      setSelectedLines((previous) => previous.filter((line) => !line.customer_package_id));
    }
    try {
      const result = await fetchCustomerPage({ q: query, limit: 50, offset });
      if (!mounted.current || referenceScopeRef.current !== referenceScope || request !== customerLookupRequest.current) return;
      setReferenceData((previous) => ({ ...previous, customers: Array.from(new Map([
        ...(append ? previous.customers : []), ...result.items,
      ].map((customer) => [customer.id, customer])).values()) }));
      setCustomerPage({ query, nextOffset: result.nextOffset, loading: false, error: null });
    } catch (error) {
      if (!mounted.current || referenceScopeRef.current !== referenceScope || request !== customerLookupRequest.current) return;
      setCustomerPage((previous) => ({ ...previous, loading: false, error: error instanceof Error ? error.message : "Không tìm được khách" }));
    }
  };

  const loadBookings = React.useCallback(async (append = false): Promise<void> => {
    // A mutation may finish after the user changed filters. Its old callback
    // must not start a request for that previous scope.
    if (!mounted.current || scopeRef.current !== scopeKey) return;
    const page = bookingPageRef.current;
    if (append && (page.scope !== scopeKey || page.loading || page.nextOffset === null)) return;
    const offset = append ? page.nextOffset! : 0;
    const request = ++bookingRequest.current;
    if (!append) setBookingState({ scope: scopeKey, rows: [], loading: true, error: null });
    setBookingPage({ scope: scopeKey, nextOffset: append ? offset : null, loading: true, error: null });
    setError(null);
    try {
      const dateFrom = viewMode === "day" ? selectedDate : weekDays[0];
      const dateTo = viewMode === "day" ? selectedDate : weekDays[6];
      const data = await fetchBookingPage({
        date_from: dateFrom,
        date_to: dateTo,
        staff_id: effectiveStaffId || undefined,
        status: filterStatus || undefined,
        limit: 200,
        offset,
      });
      if (!mounted.current || request !== bookingRequest.current || scopeRef.current !== scopeKey) return;
      setBookingState((previous) => {
        const rows = Array.from(new Map([...(append && previous.scope === scopeKey ? previous.rows : []), ...data.items].map((row) => [row.id, row])).values());
        rows.sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime() || a.id.localeCompare(b.id));
        return { scope: scopeKey, rows, loading: false, error: null };
      });
      setUpdatedAt(new Date().toISOString());
      setBookingPage({ scope: scopeKey, nextOffset: data.nextOffset, loading: false, error: null });
    } catch (err) {
      if (!mounted.current || request !== bookingRequest.current || scopeRef.current !== scopeKey) return;
      if (append) {
        setBookingPage({ scope: scopeKey, nextOffset: offset, loading: false, error: err instanceof Error ? err.message : "Không tải thêm được lịch" });
        return;
      }
      setBookingPage({ scope: scopeKey, nextOffset: null, loading: false, error: null });
      setBookingState({ scope: scopeKey, rows: [], loading: false,
        error: err instanceof Error ? err.message : "Không thể tải danh sách lịch hẹn" });
    }
  }, [scopeKey, viewMode, selectedDate, weekDays, effectiveStaffId, filterStatus]);

  // A write belongs to its original identity, but invalidates the currently
  // displayed filters. Never replay the old filter callback after a commit.
  const latestLoadBookings = React.useRef(loadBookings);
  React.useLayoutEffect(() => {
    latestLoadBookings.current = loadBookings;
  }, [loadBookings]);
  const refreshAfterMutation = React.useCallback(async (): Promise<void> => {
    if (!mounted.current || referenceScopeRef.current !== referenceScope) return;
    await latestLoadBookings.current();
  }, [referenceScope]);

  const manualBatch = useManualBatch(user ? `spaos_manual_batch_${user.tenant_id}_${user.id}` : null,
    (result) => {
      setManualNotice({ scope: referenceScope, text: `Đã lưu ${result.booking_ids.length} buổi hẹn. Kiểm tra kết quả không tạo thêm khách, thẻ hoặc lịch.` });
      setModalOpen(false); void refreshAfterMutation(); void loadReferenceData();
    },
    () => setModalOpen(true), (body) => {
      setModalError(null);setCustomerQuery("");
      if (!body) {
        // Legacy/expired recovery IDs still allow checking their result, but
        // must not reuse the customer and services of another open draft.
        setModalCustomerId("");setQuickNewCustomer(false);
        setNewCustomerName("");setNewCustomerPhone("");setNewCustomerNotes("");
        setSelectedLines([]);setModalStaffId(user?.role === "STAFF" ? user.id : "");
        setModalNote("");setSessionRows([createEmptySessionRow(selectedDate)]);
        return;
      }
      setModalCustomerId(body.customer_id || ""); setQuickNewCustomer(!!body.new_customer);
      setNewCustomerName(body.new_customer?.full_name || ""); setNewCustomerPhone(body.new_customer?.phone_number || "");
      setNewCustomerNotes(body.new_customer?.notes || ""); setSelectedLines(body.items.map(i => ({ service_id:i.service_id, customer_package_id:i.customer_package_id || null })));
      setModalStaffId(body.staff_id || ""); setModalNote(body.note || "");
      setSessionRows(body.start_times.map(start => ({...createEmptySessionRow(formatDateISOInVN(new Date(start))),selectedSlotStart:start})));
    });
  const creatingBooking = manualBatch.busy;
  const manualUncertain = manualBatch.uncertain;

  React.useEffect(() => {
    void loadReferenceData();
  }, [loadReferenceData]);

  React.useEffect(() => {
    void loadBookings();
  }, [loadBookings]);

  React.useLayoutEffect(() => {
    const position = calendarReturnPosition.current;
    if (!position) return;
    if (position.scope !== scopeKey) { calendarReturnPosition.current = null; return; }
    if (!loading) {
      window.scrollTo(position.x, position.y);
      calendarReturnPosition.current = null;
    }
  }, [loading, scopeKey, bookingState]);

  React.useEffect(() => {
    const region = weekScroller.current;
    if (!region || loading || viewMode !== "week" || !window.matchMedia("(min-width: 1024px)").matches) return;
    const selectedDay = region.querySelector<HTMLElement>(`[data-day="${selectedDate}"]`);
    if (selectedDay) region.scrollLeft += selectedDay.getBoundingClientRect().left - region.getBoundingClientRect().left;
  }, [loading, viewMode, selectedDate]);

  // Load customer's active packages when selecting a customer in Manual Booking modal
  React.useEffect(() => {
    if (!modalCustomerId) {
      setCustomerPackages([]);
      return;
    }
    let cancelled = false;
    setCustomerPackages([]);
    void (async () => {
      try {
        const pkgs = await fetchCustomerPackages(modalCustomerId);
        if (!cancelled) setCustomerPackages(
          pkgs.filter((p) => p.status === "ACTIVE" && p.remaining_sessions > 0)
        );
      } catch {
        if (!cancelled) setCustomerPackages([]);
      }
    })();
    return () => { cancelled = true; };
  }, [modalCustomerId]);

  const selectedServiceIdsKey = React.useMemo(
    () => selectedLines.map((l) => l.service_id).join(","),
    [selectedLines]
  );
  const [slotsAttempt, setSlotsAttempt] = React.useState(0);
  const [freeStaff, setFreeStaff] = React.useState<string[] | null>(null);
  const [staffAvailabilityError, setStaffAvailabilityError] = React.useState(false);
  const staffTimeKey = JSON.stringify(sessionRows.map(r=>[r.date,r.selectedSlotStart]));
  React.useEffect(()=>{
    if (!modalOpen || !selectedLines.length || user?.role !== "ADMIN") { setFreeStaff(null); return; }
    let alive=true; setFreeStaff(null); setStaffAvailabilityError(false);
    void Promise.all(sessionRows.map(async row=>{
      const result=await fetchAvailableSlots({date:row.date,service_ids:selectedLines.map(l=>l.service_id),all_staff:true});
      return new Set(result.slots.filter(slot=>!row.selectedSlotStart || new Date(slot.start_time).getTime()===new Date(row.selectedSlotStart).getTime()).flatMap(slot=>slot.available_staff_ids));
    })).then(sets=>{if(alive)setFreeStaff(staffList.filter(s=>sets.every(ids=>ids.has(s.id))).map(s=>s.id));})
      .catch(()=>{if(alive){setFreeStaff([]);setStaffAvailabilityError(true);}});
    return ()=>{alive=false;};
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[modalOpen,selectedServiceIdsKey,staffTimeKey,staffList,slotsAttempt,user?.role]);
  const staffChoices = eligibleStaff(staffList.filter(s=>freeStaff===null || freeStaff.includes(s.id)), selectedLines.map((l) => l.service_id));
  // Bỏ KTV đã chọn nếu sau khi đổi dịch vụ họ không còn phù hợp.
  React.useEffect(() => {
    if (!modalStaffId || selectedLines.length === 0) return;
    const choices = eligibleStaff(staffList, selectedLines.map(l=>l.service_id));
    const allowed = [...choices.matching, ...choices.undeclared, ...choices.other];
    if (staffList.length > 0 && !allowed.some((member) => member.id === modalStaffId)) setModalStaffId("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedServiceIdsKey, staffList]);

  const sessionDatesKey = React.useMemo(
    () => sessionRows.map((r) => `${r.rowId}:${r.date}`).join("|"),
    [sessionRows]
  );

  const sessionSlotScope = (row: ScheduledSessionRow): string => JSON.stringify([row.date, selectedServiceIdsKey, modalStaffId]);
  const sessionSlotVerified = (row: ScheduledSessionRow): boolean => !row.slotsLoading && !row.slotsError && row.slotsScope === sessionSlotScope(row) && row.slots.some((slot) => slot.start_time === row.selectedSlotStart);

  // Fetch available slots for each scheduled session row whenever services, staff, or row dates change
  React.useEffect(() => {
    if (!modalOpen || selectedLines.length === 0) {
      setSessionRows((prev) =>
        prev.map((r) => ({
          ...r,
          slots: [],
          slotsLoading: false,
          slotsError: null,
          slotsScope: "",
          selectedSlotStart: "",
        }))
      );
      return;
    }

    let cancelled = false;
    const serviceIds = selectedLines.map((l) => l.service_id);

    setSessionRows((prev) =>
      prev.map((r) => ({ ...r, slotsLoading: true, slotsError: null }))
    );

    void (async () => {
      const results = await Promise.all(
        sessionRows.map(async (row) => {
          if (!row.date) {
            return { rowId: row.rowId, slots: [] as SlotItem[], error: null };
          }
          try {
            const res = await fetchAvailableSlots({
              date: row.date,
              service_ids: serviceIds,
              staff_id: modalStaffId || null,
            });
            return { rowId: row.rowId, slots: res.slots, error: null };
          } catch {
            return { rowId: row.rowId, slots: [] as SlotItem[], error: "Không tải được khung giờ. Kiểm tra kết nối và thử lại." };
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

          if (found?.error) {
            // Retain the draft choice for retry, but never permit submission.
          } else if (slots.length === 0) {
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
            slotsError: found?.error || null,
            slotsScope: sessionSlotScope(row),
            selectedSlotStart: nextSelected,
          };
        });
      });
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modalOpen, selectedServiceIdsKey, modalStaffId, sessionDatesKey, slotsAttempt]);

  const { slots: rescheduleSlots, loading: rescheduleSlotsLoading, error: rescheduleSlotsError,
    retry: retryRescheduleSlots, selectedStart: rescheduleSlotStart, select: setRescheduleSlotStart } = useAvailableSlots({
    date: rescheduleDate, serviceIds: rescheduleTarget?.items.map((item) => item.service_id) || [],
    staffId: rescheduleStaffId || null, enabled: Boolean(rescheduleTarget && user),
    preferredStart: rescheduleTarget?.start_time,
    bookingId: rescheduleTarget?.id,
  });

  const openRescheduleModal = (booking: BookingRecord): void => {
    if (!canReschedule) return;
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
    if (rescheduleFlight.current) return;
    if (!rescheduleTarget || !rescheduleSlotStart) {
      setRescheduleError("Vui lòng chọn khung giờ trống mới.");
      return;
    }

    rescheduleFlight.current = true;
    setRescheduleSaving(true);
    calendarReturnPosition.current = { scope: scopeKey, x: window.scrollX, y: window.scrollY };
    setRescheduleError(null);
    try {
      await rescheduleBooking(rescheduleTarget.id, {
        staff_id: rescheduleStaffId || null,
        transfer_customer: user?.role === "ADMIN" && transferCustomer,
        start_time: rescheduleSlotStart,
        note: rescheduleNote.trim() || null,
      });

      setRescheduleTarget(null);
      await refreshAfterMutation();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) retryRescheduleSlots();
      setRescheduleError(
        err instanceof Error
          ? err.message
          : "Không thể dời lịch hẹn. Vui lòng thử lại hoặc chọn khung giờ khác."
      );
      await refreshAfterMutation();
    } finally {
      rescheduleFlight.current = false;
      setRescheduleSaving(false);
    }
  };

  const handleStatusChange = async (
    bookingId: string,
    nextStatus: BookingStatus
  ): Promise<void> => {
    setStatusBusyId(bookingId);
    calendarReturnPosition.current = { scope: scopeKey, x: window.scrollX, y: window.scrollY };
    setError(null);
    try {
      const updated = await updateBookingStatus(bookingId, nextStatus);
      if (mounted.current && referenceScopeRef.current === referenceScope) {
        setDetailTarget((previous) => previous?.id === updated.id ? updated : previous);
        setStatusConfirmation(null);
      }
      await refreshAfterMutation();
    } catch (err) {
      // A failed response may still follow a committed write. Reconcile the
      // current list first, then keep the failure visible in this identity.
      await refreshAfterMutation();
      if (mounted.current && referenceScopeRef.current === referenceScope) setError(
        err instanceof Error
          ? err.message
          : "Không thể cập nhật trạng thái lịch hẹn"
      );
    } finally {
      setStatusBusyId((busyId) => busyId === bookingId ? null : busyId);
    }
  };

  const openCreateModal = (): void => {
    if (!referencesReady) return;
    if (manualUncertain) { setModalOpen(true); return; }
    // A new form gets a new operation; an older request remains in the queue
    // for reconciliation, including after a check returned 404.
    manualBatch.defer();
    setModalError(null);
    setShowCourse(false);
    setQuickNewCustomer(false);
    setModalCustomerId("");
    setNewCustomerName("");
    setNewCustomerPhone("");
    setNewCustomerNotes("");
    setSelectedLines([]);
    setModalStaffId(user?.role === "STAFF" ? user.id : "");
    setIntervalDays(7);
    setSessionRows([createEmptySessionRow(selectedDate)]);
    setModalNote("");
    setModalOpen(true);
  };

  const consumedCustomerLink = React.useRef("");
  React.useEffect(() => {
    if (!referencesReady) return;
    const id = new URLSearchParams(window.location.search).get("customer_id");
    const key = referenceScope + ":" + id;
    if (!id || consumedCustomerLink.current === key) return;
    consumedCustomerLink.current = key;
    if (manualUncertain || creatingBooking) { setError("Hãy kiểm tra hoặc hoàn tất lịch đang lưu trước khi đặt cho khách khác."); return; }
    let cancelled = false;
    void customerDetail(id).then((customer) => {
      if (cancelled || referenceScopeRef.current !== referenceScope) return;
      openCreateModal();
      setReferenceData((old) => ({ ...old, customers: [...old.customers.filter((item) => item.id !== customer.id), customer] }));
      setModalCustomerId(customer.id);
    }).catch(() => { if (!cancelled) setError("Chưa mở được khách đã chọn. Hãy tìm khách hoặc thử lại từ hồ sơ."); });
    return () => { cancelled = true; };
    // The link is consumed once; changes inside the modal must not reopen it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [referencesReady, referenceScope]);
  useRefreshOnReturn(() => { void loadBookings(); void loadReferenceData(); }, !statusBusyId && !modalOpen && !detailTarget && !rescheduleTarget);
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
    if (creatingBooking || manualUncertain) return;
    setModalError(null);

    if (!referencesReady) {
      setModalError("Chưa tải đủ thông tin khách, dịch vụ hoặc KTV. Vui lòng thử tải lại thông tin.");
      return;
    }

    if (selectedLines.length === 0) {
      setModalError("Vui lòng chọn ít nhất 1 dịch vụ hoặc thẻ liệu trình.");
      return;
    }

    for (let i = 0; i < sessionRows.length; i++) {
      if (!sessionRows[i].date || !sessionSlotVerified(sessionRows[i])) {
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

    if (quickNewCustomer && (!newCustomerName.trim() || !newCustomerPhone.trim())) {
      setModalError("Vui lòng nhập tên và số điện thoại khách mới."); return;
    }
    if (!quickNewCustomer && !modalCustomerId) return;
    calendarReturnPosition.current = { scope: scopeKey, x: window.scrollX, y: window.scrollY };
    await manualBatch.submit({
      ...(quickNewCustomer ? { new_customer: { full_name: newCustomerName.trim(),
        phone_number: newCustomerPhone.trim(), notes: newCustomerNotes.trim() || null } } : { customer_id: modalCustomerId }),
      staff_id: modalStaffId || null, items: selectedLines,
      start_times: sessionRows.map((row) => row.selectedSlotStart), note: modalNote.trim() || null,
    });
  };

  const activeServices = React.useMemo(
    () => services.filter((s) => s.is_active),
    [services]
  );

  const requestStatusChange = (booking: BookingRecord, next: BookingStatus): void => {
    if (["COMPLETED", "CANCELLED", "NO_SHOW"].includes(next)) {
      setDetailTarget(booking); setStatusConfirmation(next);
    } else void handleStatusChange(booking.id, next);
  };
  const renderBookingCard = (booking: BookingRecord, compact = false, full = false): React.ReactElement => {
    const meta = BOOKING_STATUS_META[booking.status];
    const customer = customerMap.get(booking.customer_id);
    const staff = booking.staff_id ? staffMap.get(booking.staff_id) : undefined;
    const hasPackageItem = booking.items.some(
      (i) => i.customer_package_id !== null
    );
    const DetailContainer = compact ? "details" : "div";

    return (
      <div
        key={booking.id}
        data-testid={`${full ? "booking-detail" : "booking-card"}-${booking.id}`}
        data-layout-card="booking"
        className={cn(
          "min-w-0 max-w-full rounded-lg border border-border p-3.5 shadow-sm transition hover:shadow-md [overflow-wrap:anywhere]",
          meta.cardClass
        )}
      >
        <div className={cn("flex gap-2", compact ? "flex-col" : "flex-wrap items-start justify-between")}>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1 whitespace-nowrap text-xs font-bold text-slate-900">
                <Clock className="h-3.5 w-3.5 shrink-0 text-primary" />
                {formatTimeVN(booking.start_time)} –{" "}
                {formatTimeVN(booking.end_time)}
              </span>
              {!compact && <span className="text-xs text-muted-foreground">
                ({booking.total_duration_minutes} phút)
              </span>}
              {!compact && hasPackageItem && (
                <Badge variant="default" className="max-w-full gap-1 whitespace-normal">
                  <Ticket className="h-3 w-3 shrink-0" />
                  Trừ thẻ liệu trình
                </Badge>
              )}
            </div>
            <p className="mt-1 text-sm font-semibold text-foreground">
              Khách:{" "}
              {booking.customer_name || customer?.full_name || "Chưa có tên khách"}
            </p>
            <p className="text-xs text-slate-600">
              KTV thực hiện:{" "}
              <strong>
                {booking.staff_name || staff?.full_name || (booking.staff_id ? "Chưa có tên KTV" : "Chưa gán")}
              </strong>
            </p>
          </div>

          <div className={cn("flex max-w-full gap-1", compact ? "w-full flex-wrap items-center justify-between" : "flex-col items-end")}>
            <span
              className={cn(
                "max-w-full rounded-full border px-2.5 py-0.5 text-xs font-semibold",
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

        {full && booking.can_manage === false && <p className="mt-3 rounded-lg bg-muted p-3 text-sm">Bạn được giao thực hiện lịch này. Chủ spa hoặc người phụ trách khách sẽ xác nhận trạng thái và cập nhật buổi liệu trình.</p>}
        {full && <BookingHandover key={booking.id} bookingId={booking.id} canManage={booking.can_manage !== false} onDirtyChange={setHandoverDirty} onBusyChange={setHandoverBusy} />}
        <DetailContainer>
        {compact && <summary className="mt-2 min-h-11 cursor-pointer rounded-md py-3 text-xs font-semibold text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          Thông tin dịch vụ
        </summary>}
        {compact && <p className="mt-2 text-xs text-muted-foreground">
          {booking.total_duration_minutes} phút{customer ? ` • SĐT: ${customer.phone_number}` : ""}
        </p>}
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {booking.items.map((item) => {
            const svc = serviceMap.get(item.service_id);
            return (
              <span
                key={item.id}
                className="inline-block max-w-full whitespace-normal rounded bg-white/80 px-2 py-0.5 text-xs text-slate-700 border border-border [overflow-wrap:anywhere]"
              >
                {item.service_name || svc?.name || "Chưa có tên dịch vụ"} ({item.duration_minutes}p •{" "}
                {item.customer_package_id
                  ? "Dùng 1 buổi trong thẻ"
                  : formatCurrency(item.price)}
                )
              </span>
            );
          })}
        </div>

        {booking.note && (
          <p className="mt-2 whitespace-pre-wrap rounded bg-white/60 px-2.5 py-1 text-xs italic text-slate-600 [overflow-wrap:anywhere]">
            Ghi chú: {booking.note}
          </p>
        )}
        </DetailContainer>

        {(!full || (booking.can_manage !== false && meta.next.length > 0)) && (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-border/60 pt-2.5">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs font-medium text-muted-foreground mr-1">
                Trạng thái:
              </span>
              {(booking.can_manage === false ? [] : full ? meta.next : meta.next.slice(0, 1)).map((nextSt) => {
                const nextMeta = BOOKING_STATUS_META[nextSt];
                return (
                  <Button
                    key={nextSt}
                    type="button"
                    disabled={!!statusBusyId || (full && !!statusConfirmation)}
                    onClick={() => requestStatusChange(booking, nextSt)}
                    className={cn(
                      "h-auto min-h-11 whitespace-normal rounded-md border px-3 py-2 text-sm font-semibold transition disabled:opacity-50",
                      nextMeta.badgeClass
                    )}
                  >
                    {({ CONFIRMED: "Xác nhận lịch", IN_PROGRESS: "Bắt đầu phục vụ", COMPLETED: "Hoàn thành buổi", CANCELLED: "Hủy lịch", NO_SHOW: "Khách không đến", PENDING: "Chờ xác nhận" })[nextSt]}
                  </Button>
                );
              })}
            </div>

            {!full && <Button type="button" variant="outline" onClick={() => { setDetailTarget(booking); setStatusConfirmation(null); }}>
              Chi tiết lịch hẹn
            </Button>}
            {full && booking.can_manage !== false && (user?.role === "ADMIN" || user?.role === "STAFF") &&
              (booking.status === "PENDING" || booking.status === "CONFIRMED") && (
                <button
                  type="button"
                  disabled={!canReschedule || !!statusBusyId || !!statusConfirmation}
                  onClick={() => { setDetailTarget(null); setStatusConfirmation(null); openRescheduleModal(booking); }}
                  className="inline-flex min-h-11 items-center gap-1 rounded-md border border-sky-300 bg-sky-50 px-3 py-2 text-sm font-semibold text-sky-700 transition hover:bg-sky-100"
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
    <div className="min-w-0 max-w-full space-y-5">
      {manualNotice.scope === referenceScope && manualNotice.text && <p role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900 [overflow-wrap:anywhere]">{manualNotice.text}</p>}
      {/* Header & Actions */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">
            {user?.role === "STAFF" ? "Lịch làm việc của tôi" : "Lịch hẹn"}
          </h1>
          <p className="text-xs text-muted-foreground">
            Theo dõi lịch theo Ngày / Tuần, đổi trạng thái nhanh (tự động trừ
            buổi thẻ liệu trình khi Hoàn thành)
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {user?.role === "ADMIN" && <Button variant="outline" disabled={!canReschedule} onClick={() => setShowAvailability((value) => !value)}>{showAvailability ? "Đóng giờ trống" : "Xem giờ trống"}</Button>}
          <Button
            variant="outline"
            size="sm"
            onClick={() => void loadBookings()}
          >
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
            Làm mới
          </Button>
          <Button size="sm" onClick={openCreateModal} disabled={!referencesReady}>
            <Plus className="h-4 w-4" />
            Tạo lịch hẹn
          </Button>
        </div>
      </div>
      <GuestInbox services={services} onSaved={()=>{void refreshAfterMutation();void loadReferenceData();}}/>
      {manualBatch.queue.length > 0 && <details className="rounded-xl border bg-card p-4" open>
        <summary className="cursor-pointer font-semibold">Yêu cầu cần đối chiếu ({manualBatch.queue.length})</summary>
        <p className="my-2 text-sm text-muted-foreground">Các yêu cầu này chưa chắc đã thành lịch. Bạn vẫn có thể tạo lịch cho khách khác. Bản nháp trong tab được giữ tối đa 8 giờ.</p>
        {manualBatch.queue.map(entry => <div key={entry.id} className="flex flex-wrap items-center justify-between gap-2 border-t py-3">
          <span className="text-sm">{entry.body?.new_customer?.full_name || customerMap.get(entry.body?.customer_id || "")?.full_name || "Yêu cầu tạo lịch"} · {entry.id.slice(0,8)}</span>
          <Button variant="outline" disabled={creatingBooking || modalOpen} onClick={()=>manualBatch.resume(entry.id)}>Mở lại và kiểm tra</Button>
        </div>)}
      </details>}
      {updatedAt && <p className="text-xs text-muted-foreground">Lần tải thành công: {formatTimeVN(updatedAt)} · Làm mới khi cần kiểm tra thay đổi.</p>}

      {showAvailability && user?.role === "ADMIN" && <AvailabilityFinder key={referenceScope} services={services} staff={staffList}
        onChoose={(serviceId, day, staffId, start) => {
          if (!referencesReady || manualUncertain || creatingBooking) { setError("Hãy hoàn tất hoặc kiểm tra lịch đang lưu trước khi tạo lịch mới."); return; }
          openCreateModal(); setSelectedLines([{ service_id: serviceId, customer_package_id: null }]);
          setModalStaffId(staffId); setSessionRows([{ ...createEmptySessionRow(day), selectedSlotStart: start }]);
        }} />}
      {/* Filter Bar */}
      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-lg border border-border bg-muted p-0.5">
              <button
                type="button"
                onClick={() => setViewMode("day")}
                className={cn(
                  "min-h-11 rounded-md px-3 py-1 text-sm font-semibold transition sm:min-h-0 sm:text-xs",
                  viewMode === "day"
                    ? "neu-surface bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                Theo Ngày
              </button>
              <button
                type="button"
                onClick={() => setViewMode("week")}
                className={cn(
                  "min-h-11 rounded-md px-3 py-1 text-sm font-semibold transition sm:min-h-0 sm:text-xs",
                  viewMode === "week"
                    ? "neu-surface bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                Theo Tuần
              </button>
            </div>

            <div className="flex min-w-0 flex-wrap items-center gap-1">
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
                aria-label="Ngày xem lịch"
                type="date"
                value={selectedDate}
                onChange={(e) => { if (e.target.value) setSelectedDate(e.target.value); }}
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

          <div className="flex w-full min-w-0 max-w-full flex-wrap items-center gap-2 xl:w-auto">
            <select
              aria-label={user?.role === "STAFF" ? "Phạm vi lịch của tôi" : "Lọc KTV"}
              value={user?.role === "STAFF" ? staffScope : filterStaffId}
              onChange={(e) => { if (user?.role === "STAFF") setStaffScope(e.target.value as "performing" | "accessible"); else setFilterStaffId(e.target.value); }}
              className="h-11 w-full max-w-full min-w-0 rounded-md border border-input bg-background px-3 text-base font-medium sm:h-9 sm:w-auto sm:text-xs"
            >
              {user?.role === "STAFF" ? <><option value="performing">Lịch tôi thực hiện</option><option value="accessible">Lịch khách tôi phụ trách và được giao</option></> : <option value="">Tất cả Kỹ thuật viên</option>}
              {(user?.role === "STAFF" ? [] : staffList).map((st) => (
                <option key={st.id} value={st.id}>
                  KTV: {st.full_name}
                </option>
              ))}
            </select>

            <select
              aria-label="Lọc trạng thái lịch"
              value={filterStatus}
              onChange={(e) =>
                setFilterStatus(e.target.value as BookingStatus | "")
              }
              className="h-11 w-full max-w-full min-w-0 rounded-md border border-input bg-background px-3 text-base font-medium sm:h-9 sm:w-auto sm:text-xs"
            >
              <option value="">Mọi trạng thái</option>
              {(Object.keys(BOOKING_STATUS_META) as BookingStatus[]).map(
                (st) => (
                  <option key={st} value={st}>
                    {BOOKING_STATUS_META[st].label}
                  </option>
                )
              )}
            </select>
          </div>
        </CardContent>
      </Card>

      {(error || bookingLoadError) && (
        <div role="alert" className="rounded-lg border border-rose-300 bg-rose-50 px-4 py-2.5 text-xs font-medium text-rose-700">
          {error || bookingLoadError}
          {bookingLoadError && <Button className="ml-2" variant="outline" size="sm" onClick={() => void loadBookings()}>Thử tải lại lịch</Button>}
        </div>
      )}
      {!loading && !bookingLoadError && <div className="flex flex-wrap items-center gap-2 text-sm" aria-live="polite">
        <span>Đã tải {bookings.length} lịch trong khoảng đang xem{bookingPage.scope === scopeKey && bookingPage.nextOffset !== null ? "; còn dữ liệu" : ""}.</span>
        {bookingPage.scope === scopeKey && bookingPage.nextOffset !== null && <Button variant="outline" disabled={bookingPage.loading} onClick={() => void loadBookings(true)}>
          {bookingPage.loading ? "Đang tải thêm..." : "Tải thêm lịch"}
        </Button>}
        {bookingPage.scope === scopeKey && bookingPage.error && <p role="alert">{bookingPage.error} — Nhấn tải thêm để thử lại.</p>}
      </div>}
      {referenceData.scope === referenceScope && referenceData.errors.length > 0 && (
        <div role="alert" data-testid="calendar-reference-error" className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          Chưa tải được: {referenceData.errors.join(", ")}. Lịch đã tải vẫn có thể xem; thao tác cần thông tin này tạm khóa.
          <Button className="mt-2" variant="outline" size="sm" disabled={referenceData.loading} onClick={() => void loadReferenceData()}>Thử tải lại thông tin</Button>
        </div>
      )}

      {/* Status Legend: chú thích màu của thẻ lịch, không phải bộ lọc */}
      <details className="text-xs">
        <summary className="inline-flex min-h-11 cursor-pointer items-center text-muted-foreground">Chú thích màu trạng thái</summary>
      <div className="flex flex-wrap items-center gap-2 pb-1 text-xs">
        {(Object.keys(BOOKING_STATUS_META) as BookingStatus[]).map((st) => (
          <span
            key={st}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
              BOOKING_STATUS_META[st].badgeClass
            )}
          >
            {BOOKING_STATUS_META[st].label}
          </span>
        ))}
      </div>
      </details>

      {/* Calendar Body */}
      {loading ? (
        <Card>
          <CardContent className="p-10 text-center text-sm text-muted-foreground">
            Đang tải lịch hẹn...
          </CardContent>
        </Card>
      ) : bookingLoadError ? (
        <p className="py-8 text-center text-sm text-muted-foreground">Chưa tải được lịch của ngày hoặc bộ lọc đã chọn.</p>
      ) : viewMode === "day" ? (
        <div className="space-y-3">
          {bookings.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center gap-2 py-12 text-center">
                <CalendarIcon className="h-8 w-8 text-muted-foreground" />
                <p className="text-sm font-medium text-foreground">
                  Không có lịch hẹn nào trong ngày {selectedDate}
                </p>
                {(filterStaffId || filterStatus) && <Button variant="outline" onClick={() => { setFilterStaffId(""); setFilterStatus(""); }}>Bỏ bộ lọc lịch</Button>}
                <p className="text-xs text-muted-foreground">
                  Nhấn &ldquo;Tạo lịch hẹn&rdquo; để đặt lịch cho khách
                  gọi Hotline hoặc khách vãng lai.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid min-w-0 gap-3 xl:grid-cols-2">
              {bookings.map((b) => renderBookingCard(b))}
            </div>
          )}
        </div>
      ) : (
        <section aria-label="Lịch tuần" className="min-w-0 max-w-full">
        <p className="mb-2 hidden text-xs text-muted-foreground lg:block">Cuộn ngang để xem đủ 7 ngày; cuộn trong từng ngày để xem thêm lịch.</p>
        <div ref={weekScroller} data-calendar-scroll role="region" aria-label="Các ngày trong tuần" tabIndex={0}
          className="min-w-0 max-w-full rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring lg:overflow-x-auto lg:pb-3">
        <div data-testid="calendar-container" className="grid min-w-0 gap-3 lg:min-w-[1680px] lg:grid-cols-7 lg:items-start">
          {weekDays.map((dayISO) => {
            const dayBookings = bookings.filter(
              (b) => formatDateISOInVN(new Date(b.start_time)) === dayISO
            );
            const isToday = dayISO === formatDateISOInVN();
            return (
              <div
                key={dayISO}
                data-day={dayISO}
                className={cn(
                  "flex min-w-0 flex-col rounded-xl border border-border neu-surface bg-card p-2.5",
                  isToday && "ring-2 ring-primary/40"
                )}
              >
                <div className={cn("flex items-center justify-between gap-2", dayBookings.length > 0 && "mb-2 border-b border-border pb-1.5")}>
                  <span className="text-xs font-bold text-foreground">
                    {dayISO.slice(8, 10)}/{dayISO.slice(5, 7)}
                  </span>
                  <Badge
                    variant={dayBookings.length > 0 ? "default" : "outline"}
                  >
                    {dayBookings.length} lịch
                  </Badge>
                </div>
                {dayBookings.length > 0 && <div role="region" aria-label={`Lịch ngày ${dayISO}`} tabIndex={0}
                  className="min-w-0 space-y-2 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring lg:max-h-[65vh] lg:overflow-y-auto lg:pr-1">
                  {dayBookings.map((b) => renderBookingCard(b, true))}
                </div>}
              </div>
            );
          })}
        </div>
        </div>
        </section>
      )}

      {/* Manual Booking Modal */}
      <Modal open={!!detailTarget} title="Chi tiết lịch hẹn" dirty={handoverDirty} pending={!!statusBusyId || handoverBusy}
        onClose={() => { setDetailTarget(null); setStatusConfirmation(null); }} maxWidthClass="max-w-xl">
        {error && <p role="alert" className="mb-3 text-sm text-rose-700">{error}</p>}
        {detailTarget && <>
          <p className="mb-3 text-sm">{formatDateTimeVN(detailTarget.start_time)}</p>
          {renderBookingCard(detailTarget, false, true)}
          {statusConfirmation && <section aria-label="Xác nhận đổi trạng thái" className="mt-4 space-y-3 rounded-xl border p-4">
            <p className="font-semibold">Xác nhận: {BOOKING_STATUS_META[statusConfirmation].label}</p>
            <p className="text-sm">{detailTarget.customer_name || customerMap.get(detailTarget.customer_id)?.full_name || "Chưa có tên khách"} • {formatDateTimeVN(detailTarget.start_time)}</p>
            <p className="text-sm">{statusConfirmation === "COMPLETED" && detailTarget.items.some((item) => item.customer_package_id)
              ? "Hoàn thành sẽ ghi nhận sử dụng buổi trong thẻ liệu trình." : "Kiểm tra đúng khách và giờ hẹn trước khi xác nhận."}</p>
            <div className="flex flex-wrap gap-2">
              <Button disabled={!!statusBusyId} onClick={() => void handleStatusChange(detailTarget.id, statusConfirmation)}>Xác nhận đổi trạng thái</Button>
              <Button disabled={!!statusBusyId} variant="outline" onClick={() => setStatusConfirmation(null)}>Giữ trạng thái hiện tại</Button>
            </div>
          </section>}
        </>}
      </Modal>
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        pending={creatingBooking || manualUncertain}
        dirty={selectedLines.length > 0 || quickNewCustomer || !!modalNote || modalStaffId !== (user?.role === "STAFF" ? user.id : "") || sessionRows.length > 1}
        historyGuard
        title="Tạo lịch hẹn tại quầy"
        description="Hỗ trợ đặt lịch đơn lẻ hoặc lên lịch hẹn nhiều ngày liên tiếp cho gói lộ trình nhiều buổi."
        maxWidthClass="max-w-3xl"
        footer={manualUncertain ? <div className="space-y-2">
          <p role="alert" className="text-sm">Chưa xác định kết quả. Kiểm tra lại không tạo thêm lịch. Chọn Kiểm tra sau để tiếp tục phục vụ khách khác.</p>
          <div className="flex flex-wrap gap-2">
            <Button type="button" disabled={creatingBooking} onClick={() => void manualBatch.check()}>Kiểm tra kết quả</Button>
            {manualBatch.canRetry && <Button type="button" disabled={creatingBooking} variant="outline" onClick={() => void manualBatch.retry()}>Thử lại</Button>}
            <Button type="button" disabled={creatingBooking} variant="outline" onClick={() => { manualBatch.defer(); setModalOpen(false); }}>Kiểm tra sau</Button>
          </div>
        </div> : <div className="space-y-2"><p className="text-xs text-muted-foreground">{quickNewCustomer ? newCustomerName || "Khách mới" : customers.find((customer) => customer.id === modalCustomerId)?.full_name || "Chưa chọn khách"} · {sessionRows.length} buổi · {selectedLines.length} dịch vụ/thẻ{sessionRows[0]?.selectedSlotStart ? " · " + formatDateTimeVN(sessionRows[0].selectedSlotStart) : ""}</p><p className="text-xs">Giá trị dự kiến: {formatCurrency(selectedLines.reduce((total, line) => total + (line.customer_package_id ? 0 : Number(serviceMap.get(line.service_id)?.price || 0) * (serviceMap.get(line.service_id)?.is_package ? 1 : sessionRows.length)), 0))} · Chưa ghi nhận thu tiền</p><Button type="submit" form="manual-booking-form" className="w-full sm:w-auto"
          disabled={creatingBooking || !referencesReady || (!quickNewCustomer && (customerPage.loading || customerQuery.trim() !== customerPage.query || !modalCustomerId)) || selectedLines.length === 0 || sessionRows.some((row) => !sessionSlotVerified(row))}>
          {creatingBooking ? "Đang lưu lịch..." : sessionRows.length > 1 ? `Xác nhận tạo ${sessionRows.length} buổi hẹn` : "Xác nhận tạo lịch"}
        </Button></div>}
      >
        <form
          id="manual-booking-form"
          ref={(element) => { element?.toggleAttribute("inert", creatingBooking || manualUncertain); }}
          onSubmit={(e) => void handleCreateManualBooking(e)}
          className="space-y-4"
        >
          {(modalError || manualBatch.error) && (
            <div className="rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">
              {modalError || manualBatch.error}
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
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1"><Label htmlFor="quickCustomerName">Họ và tên khách mới</Label>
                  <Input id="quickCustomerName" placeholder="Họ và tên khách hàng *" value={newCustomerName} onChange={(event) => setNewCustomerName(event.target.value)} required />
                </div>
                <div className="space-y-1"><Label htmlFor="quickCustomerPhone">Số điện thoại khách mới</Label>
                  <Input id="quickCustomerPhone" type="tel" inputMode="tel" placeholder="Số điện thoại (9-15 số) *" value={newCustomerPhone} onChange={(event) => setNewCustomerPhone(event.target.value)} required />
                </div>
                <div className="space-y-1 sm:col-span-2"><Label htmlFor="quickCustomerNotes">Ghi chú da hoặc dị ứng (không bắt buộc)</Label>
                  <Input id="quickCustomerNotes" placeholder="Ghi chú da / dị ứng (tùy chọn)" value={newCustomerNotes} onChange={(event) => setNewCustomerNotes(event.target.value)} />
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <Label htmlFor="manualCustomerSearch">Tìm khách theo tên hoặc số điện thoại</Label>
                <div className="flex min-w-0 gap-2">
                  <Input id="manualCustomerSearch" aria-controls="manualCustomerResults" value={customerQuery} onChange={(event) => { customerLookupRequest.current += 1; setCustomerQuery(event.target.value); setModalCustomerId(""); setSelectedLines((previous) => previous.filter((line) => !line.customer_package_id)); }} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); void searchCustomers(); } if (event.key === "ArrowDown") { event.preventDefault(); document.querySelector<HTMLButtonElement>("#manualCustomerResults button:not(:disabled)")?.focus(); } }} />
                  <Button type="button" variant="outline" disabled={customerPage.loading} onClick={() => void searchCustomers()}>Tìm khách</Button>
                </div>
              <div id="manualCustomerResults" role="group" aria-label="Khách đặt lịch" onKeyDown={(event) => { if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return; const buttons = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>("button:not(:disabled)")); const current = buttons.indexOf(document.activeElement as HTMLButtonElement); if (current >= 0) { event.preventDefault(); buttons[(current + (event.key === "ArrowDown" ? 1 : -1) + buttons.length) % buttons.length]?.focus(); } }} className="max-h-48 space-y-1 overflow-y-auto rounded-lg border p-2">
                  {customers.map((customer) => <button key={customer.id} type="button" disabled={customerPage.loading || customerQuery.trim() !== customerPage.query}
                    aria-pressed={modalCustomerId === customer.id}
                    className={cn("flex min-h-11 w-full flex-wrap items-center justify-between gap-2 rounded-lg border p-2 text-left text-sm", modalCustomerId === customer.id && "border-primary bg-primary/5")}
                    onClick={() => { if (modalCustomerId === customer.id) return; setModalCustomerId(customer.id); setSelectedLines((previous) => previous.filter((line) => line.customer_package_id === null)); }}>
                    <span>{customer.full_name}</span><span>{customer.phone_number}{modalCustomerId === customer.id ? " · Đã chọn" : ""}</span>
                  </button>)}
                  {!customerPage.loading && customers.length === 0 && <p className="p-2 text-sm">Chưa tìm thấy khách. Hãy kiểm tra số điện thoại hoặc chọn tạo khách mới.</p>}
                </div>
                <p className="text-xs text-muted-foreground">Đã tải {customers.length} khách{customerPage.nextOffset !== null ? "; còn kết quả — tìm theo tên/SĐT hoặc tải thêm" : ""}.</p>
                {customerPage.nextOffset !== null && <Button type="button" variant="outline" disabled={customerPage.loading} onClick={() => void searchCustomers(true)}>Tải thêm khách</Button>}
                {customerPage.error && <p role="alert">{customerPage.error} — Nhấn tìm khách để thử lại.</p>}
              </div>
            )}
          </div>

          {/* 2. Customer Active Packages (if any) */}
          {!quickNewCustomer && customerPackages.length > 0 && (
            <div className="space-y-2 rounded-lg border border-primary/30 bg-primary/5 p-3">
              <Label className="text-primary">
                Thẻ liệu trình của khách — chọn để dùng buổi trong thẻ
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
                          : "border-border neu-surface bg-card hover:bg-muted/50"
                      )}
                    >
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          disabled={(pkg.available_sessions ?? pkg.remaining_sessions) <= 0}
                          checked={checked}
                          onChange={() =>
                            toggleServiceSelection(pkg.service_id, pkg.id)
                          }
                          className="h-4 w-4 accent-primary"
                        />
                        <div>
                          <p>{pkg.package_name}</p>
                          <p className="text-xs text-muted-foreground">
                            Đã dùng {pkg.used_sessions}/{pkg.total_sessions} •
                            Có thể đặt <strong>{pkg.available_sessions ?? pkg.remaining_sessions} buổi</strong> · Đã đặt trước {pkg.reserved_sessions ?? 0}
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
                        : "border-border neu-surface bg-card hover:bg-muted/50"
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
                          <p className="text-foreground [overflow-wrap:anywhere]">{svc.name}</p>
                          {svc.is_package && (
                            <Badge variant="default" className="text-xs px-1.5 py-0">
                              Lộ trình {svc.total_sessions} buổi
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">
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

          {hasMultiSessionSelection && <Button type="button" variant="outline" aria-expanded={showCourse} onClick={() => setShowCourse((value) => !value)}>Tùy chọn đặt nhiều buổi</Button>}
          {/* 4. Staff Preference & Multi-Session Course Toolbar */}
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="modalStaff">
                3. Nhân viên thực hiện (không chọn = Spa sắp xếp)
              </Label>
              <select
                id="modalStaff"
                value={modalStaffId}
                disabled={selectedLines.length > 0 && user?.role === "ADMIN" && freeStaff === null}
                onChange={(e) => setModalStaffId(e.target.value)}
                className="h-11 min-w-0 w-full rounded-md border border-input bg-background px-3 text-base sm:h-9 sm:text-sm"
              >
                <option value="">✨ Spa tự sắp xếp KTV rảnh</option>
                <optgroup label="Có đủ kỹ năng phù hợp">{staffChoices.matching.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.full_name} ({s.phone_number})
                  </option>
                ))}
                </optgroup>
                {staffChoices.undeclared.length > 0 && (
                  <optgroup label="Chưa khai báo kỹ năng">
                    {staffChoices.undeclared.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.full_name} ({s.phone_number})
                      </option>
                    ))}
                  </optgroup>
                )}
                {staffChoices.other.length > 0 && <optgroup label="Nhân viên khác — chưa đủ kỹ năng">{staffChoices.other.map(s=><option key={s.id} value={s.id}>{s.full_name} ({s.phone_number})</option>)}</optgroup>}
              </select>
              {selectedLines.length > 0 && <p className="text-xs text-muted-foreground">{staffAvailabilityError ? "Chưa tải được KTV rảnh. Thử tải lại giờ trống." : freeStaff===null && user?.role==="ADMIN" ? "Đang kiểm tra nhân viên rảnh..." : "Chỉ gợi ý người có giờ trống trong từng ngày; khi đã chọn giờ, phải rảnh ở tất cả buổi đã chọn."}</p>}
              {selectedLines.length > 0 && user?.role === "ADMIN" && (
                <p className="text-xs text-muted-foreground">
                  {staffChoices.matching.length === 0
                    ? "Chưa có KTV nào có kỹ năng cho dịch vụ đã chọn. Vào Nhân sự → Hồ sơ để gán kỹ năng."
                    : "Nhóm nhân viên khác cần chủ spa xác nhận khả năng thực hiện trước khi chọn."}
                </p>
              )}
            </div>

            {hasMultiSessionSelection && showCourse && (
              <div className="space-y-1.5">
                <Label htmlFor="intervalSelect">
                  Chu kỳ giãn cách giữa các buổi hẹn
                </Label>
                <select
                  id="intervalSelect"
                  value={intervalDays}
                  onChange={(e) => setIntervalDays(Number(e.target.value))}
                  className="h-11 min-w-0 w-full rounded-md border border-input bg-background px-3 text-base sm:h-9 sm:text-sm"
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
          {hasMultiSessionSelection && showCourse && (
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
                    className="rounded-lg border border-border neu-surface bg-card p-3 space-y-2.5 shadow-2xs"
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
                        {sessionSlotVerified(row) && (
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

                    {(row.slotsLoading || (selectedLines.length > 0 && row.slotsScope !== sessionSlotScope(row))) ? (
                      <p className="rounded-md border border-border p-2.5 text-center text-xs text-muted-foreground">
                        Đang tìm khung giờ trống cho ngày {row.date}...
                      </p>
                    ) : row.slotsError ? (
                      <div role="alert" className="space-y-2 rounded-md border p-3 text-center text-sm">
                        <p>{row.slotsError}</p><Button type="button" variant="outline" onClick={() => setSlotsAttempt((previous) => previous + 1)}>Thử lại khung giờ</Button>
                      </div>
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
                                "flex min-h-11 flex-col items-center justify-center rounded border px-2 py-1 text-xs font-medium transition",
                                active
                                  ? "border-primary bg-primary text-primary-foreground shadow-sm"
                                  : "border-border neu-surface bg-card text-foreground hover:bg-accent"
                              )}
                            >
                              <span>{formatTimeVN(slot.start_time)}</span>
                              <span
                                className={cn(
                                  "text-xs",
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

        </form>
      </Modal>

      {/* Reschedule / Edit Booking Modal */}
      <Modal
        open={Boolean(rescheduleTarget)}
        pending={rescheduleSaving}
        onClose={() => setRescheduleTarget(null)}
        title="Chỉnh sửa & Dời lịch hẹn"
        dirty={Boolean(rescheduleTarget && (rescheduleNote !== (rescheduleTarget.note || "") || rescheduleDate !== formatDateISOInVN(new Date(rescheduleTarget.start_time)) || rescheduleStaffId !== (rescheduleTarget.staff_id || "") || (rescheduleSlotStart && new Date(rescheduleSlotStart).getTime() !== new Date(rescheduleTarget.start_time).getTime()) || transferCustomer))}
        description="Thay đổi ngày hẹn, khung giờ trống hoặc nhân viên thực hiện. Buổi thẻ liệu trình (nếu có) được bảo lưu nguyên vẹn."
      >
        {rescheduleTarget && (
          <form
            onSubmit={(e) => void handleConfirmReschedule(e)}
            className="space-y-4"
          >
            <fieldset disabled={rescheduleSaving} className="space-y-4">
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
                {rescheduleTarget.customer_name || customerMap.get(rescheduleTarget.customer_id)?.full_name ||
                  "Chưa có tên khách"}
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
                <Label htmlFor="rescheduleStaffAdmin">2. Nhân viên thực hiện</Label>
                <select
                  id="rescheduleStaffAdmin"
                  value={rescheduleStaffId}
                  onChange={(e) => { setRescheduleStaffId(e.target.value); setTransferCustomer(false); }}
                  className="h-11 min-w-0 w-full rounded-md border border-input bg-background px-3 text-base sm:h-9 sm:text-sm"
                  disabled={user?.role === "STAFF"}
                >
                  <option value="">✨ Spa tự sắp xếp KTV rảnh</option>
                  {rescheduleTarget.staff_id && !staffList.some((person) => person.id === rescheduleTarget.staff_id && person.is_active) &&
                    <option value={rescheduleTarget.staff_id}>{rescheduleTarget.staff_name || "KTV hiện tại"}</option>}
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
                  Giao khách cho kỹ thuật viên mới phụ trách
                </label>
                <p>Nếu bỏ chọn, người phụ trách khách vẫn giữ nguyên. Kỹ thuật viên làm thay chỉ quản lý hồ sơ khi được giao phụ trách.</p>
              </div>
            )}
            <div className="space-y-2">
              <Label>3. Chọn khung giờ trống mới</Label>
              <ReschedulePreview booking={rescheduleTarget} start={rescheduleSlotStart}
                staffName={rescheduleStaffId ? (rescheduleStaffId === rescheduleTarget.staff_id ? rescheduleTarget.staff_name : staffMap.get(rescheduleStaffId)?.full_name) || "Chưa có tên KTV" : "Spa tự sắp xếp"}
                transfer={transferCustomer} />
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
                            ? "border-primary bg-primary text-primary-foreground shadow-sm"
                            : "border-border neu-surface bg-card text-foreground hover:bg-accent"
                        )}
                      >
                        <span>{formatTimeVN(slot.start_time)}</span>
                        <span
                          className={cn(
                            "text-xs",
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
                type="submit"
                disabled={rescheduleSaving || rescheduleSlotsLoading || !rescheduleSlotStart || !canReschedule}
              >
                {rescheduleSaving ? "Đang lưu..." : "Xác nhận đổi lịch"}
              </Button>
            </div>
          </fieldset>
          </form>
        )}
      </Modal>
    </div>
  );
}
