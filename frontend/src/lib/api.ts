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

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

const TOKEN_KEY = "spaos_admin_token";
const SLUG_KEY = "spaos_admin_slug";

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
  window.localStorage.setItem(TOKEN_KEY, token);
  window.localStorage.setItem(SLUG_KEY, slug);
}

export function clearAuthSession(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
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
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token && !headers.Authorization) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method || "GET",
    headers,
    body:
      options.body !== undefined ? JSON.stringify(options.body) : undefined,
    cache: "no-store",
  });

  if (response.status === 401 && !options.skipAuthRedirect) {
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
    let detail = `Lỗi hệ thống (${response.status})`;
    try {
      const data = (await response.json()) as {
        detail?: string | { msg?: string }[];
      };
      if (typeof data.detail === "string") {
        detail = data.detail;
      } else if (Array.isArray(data.detail) && data.detail.length > 0) {
        detail = data.detail.map((d) => d.msg || "").join(", ");
      }
    } catch {
      // ignore json parse failure
    }
    throw new ApiError(response.status, detail);
  }

  return (await response.json()) as T;
}

// ------------------------- 2.1 Auth -------------------------
export async function loginAdmin(
  tenantSlug: string,
  phoneNumber: string,
  password: string
): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/auth/login", {
    method: "POST",
    headers: { "X-Tenant-Slug": tenantSlug.trim().toLowerCase() },
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
  return apiRequest<MeResponse>("/auth/me");
}

// ------------------------- 2.2 Tenant Settings -------------------------
export async function fetchTenantSettings(): Promise<TenantInfo> {
  return apiRequest<TenantInfo>("/tenants/me");
}

export async function updateTenantSettings(payload: {
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
}): Promise<UserDetail[]> {
  const qs = new URLSearchParams();
  if (params?.q && params.q.trim()) qs.set("q", params.q.trim());
  if (params?.limit !== undefined) qs.set("limit", String(params.limit));
  if (params?.offset !== undefined) qs.set("offset", String(params.offset));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiRequest<UserDetail[]>(`/customers${suffix}`);
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
    `/bookings/available-slots?${qs.toString()}`
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
}): Promise<BookingRecord[]> {
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
  return apiRequest<BookingRecord[]>(`/bookings${suffix}`);
}

export async function createBooking(
  payload: BookingCreateInput
): Promise<BookingRecord> {
  return apiRequest<BookingRecord>("/bookings", {
    method: "POST",
    body: payload,
  });
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
  user_agent?: string;
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
  endpoint: string
): Promise<{ unsubscribed: boolean }> {
  return apiRequest<{ unsubscribed: boolean }>("/notifications/unsubscribe", {
    method: "DELETE",
    body: { endpoint },
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
  marked_read: number;
}> {
  return apiRequest<{ marked_read: number }>("/notifications/read-all", {
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
