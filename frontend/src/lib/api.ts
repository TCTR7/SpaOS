import { apiErrorMessage } from "./api-error-message";
import { withAdminWrite } from "./branch-guard";
import type {
  AvailableSlotsResponse,
  BookingCreateInput,
  BookingRecord,
  BookingStatus,
  CustomerPackageItem,
  MeResponse,
  NotificationItem,
  NotificationsListResponse,
  PackageStatus,
  ServiceItem,
  StaffPerformanceReport,
  StaffScheduleItem,
  TenantInfo,
  TokenResponse,
  UserDetail,
  VapidPublicKeyResponse,
} from "./types";
import { listPage, type ListPage } from "./list-page";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

const TOKEN_KEY = "spaos_admin_token";
const SLUG_KEY = "spaos_admin_slug";
export const ADMIN_SESSION_VERSION_KEY = "spaos_admin_session_version";
let sessionRevision = 0;
export const ADMIN_SESSION_CHANGED = "spaos:admin-session-changed";
export function invalidateAdminSessionRequests(): void { sessionRevision += 1; }

export function getAdminSessionIdentity(): string {
  return JSON.stringify([getStoredToken(), sessionRevision,
    typeof window === "undefined" ? null : window.localStorage.getItem(ADMIN_SESSION_VERSION_KEY)]);
}

export function saveVerifiedAdminSlug(slug: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(SLUG_KEY, slug);
}

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function getStoredSlug(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(SLUG_KEY);
}

export function saveAuthSession(token: string, slug: string): void {
  if (typeof window === "undefined") return;
  sessionRevision += 1;
  window.localStorage.setItem(TOKEN_KEY, token);
  window.localStorage.setItem(SLUG_KEY, slug);
  window.localStorage.setItem(ADMIN_SESSION_VERSION_KEY, window.crypto.randomUUID());
}

export function clearAuthSession(): void {
  if (typeof window === "undefined") return;
  sessionRevision += 1;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.setItem(ADMIN_SESSION_VERSION_KEY, window.crypto.randomUUID());
  window.dispatchEvent(new Event(ADMIN_SESSION_CHANGED));
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
  skipAuthRedirect?: boolean;
  onResponse?: (response: Response) => void;
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const token = getStoredToken();
  const session = getAdminSessionIdentity();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token && !headers.Authorization) {
    headers.Authorization = `Bearer ${token}`;
  }

  const send = () => {
    if (token && session !== getAdminSessionIdentity()) throw new Error("Phi\u00ean \u0111\u00e3 thay \u0111\u1ed5i. Kh\u00f4ng g\u1eedi l\u1ea1i thao t\u00e1c c\u0169.");
    return fetch(`${API_BASE_URL}${path}`, {
    method: options.method || "GET",
    headers,
    body:
      options.body !== undefined ? JSON.stringify(options.body) : undefined,
    cache: "no-store",
  });
  };
  const guardedWrite = !!token && options.method && options.method !== "GET"
    && !path.startsWith("/auth/") && !/^\/branches\/[^/]+\/switch$/.test(path)
    && path !== "/notifications/unsubscribe";
  const response = await (guardedWrite ? withAdminWrite(send) : send());

  if (response.status === 401 && !options.skipAuthRedirect && token &&
      headers.Authorization === `Bearer ${token}` && session === getAdminSessionIdentity()) {
    clearAuthSession();
    if (
      typeof window !== "undefined" &&
      !window.location.pathname.startsWith("/admin/login") &&
      !window.location.pathname.startsWith("/admin/register-tenant")
    ) {
      window.location.href = "/admin/login";
    }
  }

  if (!response.ok) {
    const data = await response.json().catch(() => null) as { detail?: unknown } | null;
    throw new ApiError(response.status, apiErrorMessage(response.status, data?.detail));
  }

  options.onResponse?.(response);
  return (await response.json()) as T;
}

// ------------------------- 2.1 Auth -------------------------
export async function loginAdmin(
  phoneNumber: string,
  password: string
): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: { phone_number: phoneNumber.trim(), password },
    skipAuthRedirect: true,
  });
}

export async function registerTenant(payload: {
  tenant_name: string;
  tenant_slug: string;
  admin_full_name: string;
  phone_number: string;
  password: string;
}): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/auth/register-tenant", {
    method: "POST",
    body: payload,
    skipAuthRedirect: true,
  });
}

export async function fetchMe(): Promise<MeResponse> {
  return apiRequest<MeResponse>("/auth/me", { skipAuthRedirect: true });
}

// ------------------------- 2.2 Tenant Settings -------------------------
export async function fetchTenantSettings(): Promise<TenantInfo> {
  return apiRequest<TenantInfo>("/tenants/me");
}

export async function updateTenantSettings(payload: {
  address?: string | null;
  contact_phone?: string | null;
  logo_data?: string;
  name?: string;
  logo_url?: string | null;
  theme_color?: string | null;
  open_time?: string;
  close_time?: string;
  buffer_minutes?: number;
}): Promise<TenantInfo> {
  return apiRequest<TenantInfo>("/tenants/me", {
    method: "PATCH",
    body: payload,
  });
}

// ------------------------- 2.3 Services -------------------------
export async function fetchServices(params?: {
  is_active?: boolean;
  is_package?: boolean;
}): Promise<ServiceItem[]> {
  const qs = new URLSearchParams();
  if (params?.is_active !== undefined) {
    qs.set("is_active", String(params.is_active));
  }
  if (params?.is_package !== undefined) {
    qs.set("is_package", String(params.is_package));
  }
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiRequest<ServiceItem[]>(`/services${suffix}`);
}

export async function createService(payload: {
  name: string;
  description?: string | null;
  duration_minutes: number;
  price: number;
  is_package: boolean;
  total_sessions: number;
  is_active: boolean;
}): Promise<ServiceItem> {
  return apiRequest<ServiceItem>("/services", {
    method: "POST",
    body: payload,
  });
}

export async function updateService(
  id: string,
  payload: Partial<{
    name: string;
    description: string | null;
    duration_minutes: number;
    price: number;
    is_package: boolean;
    total_sessions: number;
    is_active: boolean;
  }>
): Promise<ServiceItem> {
  return apiRequest<ServiceItem>(`/services/${id}`, {
    method: "PATCH",
    body: payload,
  });
}

export async function deleteService(id: string): Promise<{
  id: string;
  deleted: boolean;
  mode: "hard" | "soft";
}> {
  return apiRequest<{ id: string; deleted: boolean; mode: "hard" | "soft" }>(
    `/services/${id}`,
    { method: "DELETE" }
  );
}

// ------------------------- 2.4 Staff & Schedules -------------------------
export async function fetchStaffList(): Promise<UserDetail[]> {
  return apiRequest<UserDetail[]>("/staff");
}

export async function createStaff(payload: {
  full_name: string;
  phone_number: string;
  password: string;
  notes?: string | null;
}): Promise<UserDetail> {
  return apiRequest<UserDetail>("/staff", {
    method: "POST",
    body: payload,
  });
}

export async function updateStaff(
  id: string,
  payload: Partial<{
    full_name: string;
    phone_number: string;
    password: string;
    notes: string | null;
    is_active: boolean;
  }>
): Promise<UserDetail> {
  return apiRequest<UserDetail>(`/staff/${id}`, {
    method: "PATCH",
    body: payload,
  });
}

export async function fetchStaffSchedules(
  staffId: string
): Promise<StaffScheduleItem[]> {
  return apiRequest<StaffScheduleItem[]>(`/staff/${staffId}/schedules`);
}

export async function saveStaffSchedules(
  staffId: string,
  schedules: StaffScheduleItem[]
): Promise<StaffScheduleItem[]> {
  return apiRequest<StaffScheduleItem[]>(`/staff/${staffId}/schedules`, {
    method: "PUT",
    body: { schedules },
  });
}

// ------------------------- 2.5 Customers & Packages -------------------------
export async function fetchCustomers(params?: {
  q?: string;
  limit?: number;
  offset?: number;
}, onResponse?: (response: Response) => void): Promise<UserDetail[]> {
  const qs = new URLSearchParams();
  if (params?.q && params.q.trim()) qs.set("q", params.q.trim());
  if (params?.limit !== undefined) qs.set("limit", String(params.limit));
  if (params?.offset !== undefined) qs.set("offset", String(params.offset));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiRequest<UserDetail[]>(`/customers${suffix}`, { onResponse });
}

export async function fetchCustomerPage(params: { q?: string; limit?: number; offset?: number } = {}): Promise<ListPage<UserDetail>> {
  let response: Response | undefined;
  const limit = params.limit ?? 50, offset = params.offset ?? 0;
  const items = await fetchCustomers({ ...params, limit, offset }, (value) => { response = value; });
  return listPage(items, response, limit, offset);
}

export async function createCustomer(payload: {
  full_name: string;
  phone_number: string;
  notes?: string | null;
  password?: string;
}): Promise<UserDetail> {
  return apiRequest<UserDetail>("/customers", {
    method: "POST",
    body: payload,
  });
}

export async function updateCustomer(
  id: string,
  payload: { full_name?: string; notes?: string | null }
): Promise<UserDetail> {
  return apiRequest<UserDetail>(`/customers/${id}`, {
    method: "PATCH",
    body: payload,
  });
}

export async function fetchCustomerPackages(
  customerId: string
): Promise<CustomerPackageItem[]> {
  return apiRequest<CustomerPackageItem[]>(
    `/customers/${customerId}/packages`
  );
}

export async function fetchAllCustomerPackages(params?: {
  customer_id?: string;
  status?: PackageStatus;
  limit?: number;
  offset?: number;
}): Promise<CustomerPackageItem[]> {
  const qs = new URLSearchParams();
  if (params?.customer_id) qs.set("customer_id", params.customer_id);
  if (params?.status) qs.set("status", params.status);
  if (params?.limit !== undefined) qs.set("limit", String(params.limit));
  if (params?.offset !== undefined) qs.set("offset", String(params.offset));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiRequest<CustomerPackageItem[]>(`/customer-packages${suffix}`);
}

export async function issueCustomerPackage(payload: {
  customer_id: string;
  service_id: string;
  package_name?: string;
  total_sessions?: number;
  expiry_date?: string | null;
}): Promise<CustomerPackageItem> {
  return apiRequest<CustomerPackageItem>("/customer-packages", {
    method: "POST",
    body: payload,
  });
}

// ------------------------- 2.6 Bookings -------------------------
export async function fetchAvailableSlots(params: {
  booking_id?: string;
  date: string;
  service_ids: string[];
  staff_id?: string | null;
}): Promise<AvailableSlotsResponse> {
  const qs = new URLSearchParams();
  qs.set("date", params.date);
  for (const sid of params.service_ids) {
    qs.append("service_ids", sid);
  }
  if (params.staff_id) {
    qs.set("staff_id", params.staff_id);
  }
  return apiRequest<AvailableSlotsResponse>(
    `${params.booking_id ? `/bookings/${params.booking_id}/available-slots` : "/bookings/available-slots"}?${qs.toString()}`
  );
}

export async function fetchBookings(params?: {
  date_from?: string;
  date_to?: string;
  staff_id?: string;
  status?: BookingStatus;
  customer_id?: string;
  scope?: "upcoming" | "history";
  limit?: number;
  offset?: number;
}, onResponse?: (response: Response) => void): Promise<BookingRecord[]> {
  const qs = new URLSearchParams();
  if (params?.date_from) qs.set("date_from", params.date_from);
  if (params?.date_to) qs.set("date_to", params.date_to);
  if (params?.staff_id) qs.set("staff_id", params.staff_id);
  if (params?.status) qs.set("status", params.status);
  if (params?.customer_id) qs.set("customer_id", params.customer_id);
  if (params?.scope) qs.set("scope", params.scope);
  if (params?.limit !== undefined) qs.set("limit", String(params.limit));
  if (params?.offset !== undefined) qs.set("offset", String(params.offset));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiRequest<BookingRecord[]>(`/bookings${suffix}`, { onResponse });
}

export async function fetchBookingPage(params: NonNullable<Parameters<typeof fetchBookings>[0]>): Promise<ListPage<BookingRecord>> {
  let response: Response | undefined;
  const limit = params.limit ?? 50, offset = params.offset ?? 0;
  const items = await fetchBookings({ ...params, limit, offset }, (value) => { response = value; });
  return listPage(items, response, limit, offset);
}

export async function createBooking(
  payload: BookingCreateInput
): Promise<BookingRecord> {
  return apiRequest<BookingRecord>("/bookings", {
    method: "POST",
    body: payload,
  });
}

export interface ManualBatchInput {
  request_id: string;
  customer_id?: string;
  new_customer?: { full_name: string; phone_number: string; notes?: string | null };
  staff_id: string | null;
  items: { service_id: string; customer_package_id: string | null }[];
  start_times: string[];
  note: string | null;
}
export interface ManualBatchResult {
  request_id: string; customer_id: string; package_ids: string[]; booking_ids: string[];
}
export function createManualBatch(body: ManualBatchInput): Promise<ManualBatchResult> {
  return apiRequest<ManualBatchResult>("/bookings/manual-batches", { method: "POST", body });
}
export function fetchManualBatch(id: string): Promise<ManualBatchResult> {
  return apiRequest<ManualBatchResult>(`/bookings/manual-batches/${id}`);
}

export async function updateBookingStatus(
  bookingId: string,
  status: BookingStatus
): Promise<BookingRecord> {
  return apiRequest<BookingRecord>(`/bookings/${bookingId}/status`, {
    method: "PATCH",
    body: { status },
  });
}

export async function cancelBooking(bookingId: string): Promise<BookingRecord> {
  return apiRequest<BookingRecord>(`/bookings/${bookingId}/cancel`, {
    method: "POST",
  });
}

// ------------------------- 2.7 Reports -------------------------
export async function fetchStaffPerformanceReport(params: {
  start_date: string;
  end_date: string;
  staff_id?: string;
}): Promise<StaffPerformanceReport> {
  const qs = new URLSearchParams();
  qs.set("start_date", params.start_date);
  qs.set("end_date", params.end_date);
  if (params.staff_id) qs.set("staff_id", params.staff_id);
  return apiRequest<StaffPerformanceReport>(
    `/reports/staff-performance?${qs.toString()}`
  );
}

// ------------------------- 2.8 Notifications & Web Push -------------------------
export async function fetchVapidPublicKey(): Promise<VapidPublicKeyResponse> {
  return apiRequest<VapidPublicKeyResponse>("/notifications/vapid-public-key", {
    skipAuthRedirect: true,
  });
}

export async function subscribeWebPush(payload: {
  endpoint: string;
  keys: { p256dh: string; auth: string };
}): Promise<{ id: string; endpoint: string }> {
  return apiRequest<{ id: string; endpoint: string }>(
    "/notifications/subscribe",
    {
      method: "POST",
      body: payload,
    }
  );
}

export async function unsubscribeWebPush(
  endpoint: string,
  token?: string
): Promise<{ deleted: number }> {
  return apiRequest<{ deleted: number }>("/notifications/unsubscribe", {
    method: "DELETE",
    body: { endpoint },
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    skipAuthRedirect: true,
  });
}

export async function fetchNotifications(params?: {
  unread_only?: boolean;
  limit?: number;
  offset?: number;
}): Promise<NotificationsListResponse> {
  const qs = new URLSearchParams();
  if (params?.unread_only !== undefined) {
    qs.set("unread_only", String(params.unread_only));
  }
  if (params?.limit !== undefined) qs.set("limit", String(params.limit));
  if (params?.offset !== undefined) qs.set("offset", String(params.offset));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiRequest<NotificationsListResponse>(`/notifications${suffix}`);
}

export async function markAllNotificationsRead(): Promise<{
  updated: number;
}> {
  return apiRequest<{ updated: number }>("/notifications/read-all", {
    method: "PATCH",
  });
}

export async function markNotificationRead(
  notificationId: string
): Promise<NotificationItem> {
  return apiRequest<NotificationItem>(
    `/notifications/${notificationId}/read`,
    {
      method: "PATCH",
    }
  );
}

export function rescheduleBooking(id: string, payload: { start_time: string; staff_id: string | null; note: string | null; transfer_customer?: boolean }): Promise<BookingRecord> {
  return apiRequest<BookingRecord>(`/bookings/${id}`, { method: "PATCH", body: payload });
}

export function assignCustomer(id: string, assigned_staff_id: string | null): Promise<UserDetail> {
  return apiRequest<UserDetail>(`/customers/${id}/assignment`, { method: "PATCH", body: { assigned_staff_id } });
}

export const fetchBranches = (): Promise<import("./types").BranchAccess[]> => apiRequest("/branches");
export const switchBranch = (id: string): Promise<TokenResponse> => apiRequest(`/branches/${id}/switch`, { method: "POST" });
export const createBranch = (name: string): Promise<import("./types").BranchAccess> => apiRequest("/branches", { method: "POST", body: { name } });
export const grantBranchStaff = (branchId: string, sourceStaffId: string): Promise<import("./types").AuthUser> =>
  apiRequest(`/branches/${branchId}/staff-access`, { method: "POST", body: { source_staff_id: sourceStaffId } });
export const fetchBranchDashboard = (day: string, all = false): Promise<import("./types").BranchDashboard> =>
  apiRequest(`/dashboard?day=${day}&all_branches=${all}`);

export function fetchBookingDetail(id: string): Promise<BookingRecord> {
  return apiRequest<BookingRecord>(`/bookings/${encodeURIComponent(id)}`);
}
