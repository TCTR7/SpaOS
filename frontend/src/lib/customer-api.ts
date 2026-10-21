import { apiErrorMessage } from "./api-error-message";
import { API_BASE_URL, ApiError } from "./api";
import { listPage, type ListPage } from "./list-page";
import type {
  AvailableSlotsResponse,
  BookingCreateInput,
  BookingRecord,
  MyCustomerPackageItem,
  MeResponse,
  NotificationItem,
  NotificationsListResponse,
  PublicTenantResponse,
  TokenResponse,
  VapidPublicKeyResponse,
} from "./types";

function tokenKeyForSlug(slug: string): string {
  return `spaos_customer_token_${slug.trim().toLowerCase()}`;
}

export function customerSessionVersionKey(slug: string): string {
  return `spaos_customer_session_version_${slug.trim().toLowerCase()}`;
}

const revisions = new Map<string, number>();
export const CUSTOMER_SESSION_CHANGED = "spaos:customer-session-changed";
export function invalidateCustomerSessionRequests(slug: string): void {
  revisions.set(tokenKeyForSlug(slug), (revisions.get(tokenKeyForSlug(slug)) || 0) + 1);
}
export function getCustomerSessionIdentity(slug: string): string {
  return JSON.stringify([getCustomerToken(slug), revisions.get(tokenKeyForSlug(slug)) || 0,
    typeof window === "undefined" ? null : window.localStorage.getItem(customerSessionVersionKey(slug))]);
}

export function getCustomerToken(slug: string): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(tokenKeyForSlug(slug));
}

export function saveCustomerToken(slug: string, token: string): void {
  if (typeof window === "undefined") return;
  revisions.set(tokenKeyForSlug(slug), (revisions.get(tokenKeyForSlug(slug)) || 0) + 1);
  window.localStorage.setItem(tokenKeyForSlug(slug), token);
  window.localStorage.setItem(customerSessionVersionKey(slug), window.crypto.randomUUID());
}

export function clearCustomerToken(slug: string): void {
  if (typeof window === "undefined") return;
  revisions.set(tokenKeyForSlug(slug), (revisions.get(tokenKeyForSlug(slug)) || 0) + 1);
  window.localStorage.removeItem(tokenKeyForSlug(slug));
  window.localStorage.setItem(customerSessionVersionKey(slug), window.crypto.randomUUID());
  window.dispatchEvent(new CustomEvent(CUSTOMER_SESSION_CHANGED, { detail: slug.trim().toLowerCase() }));
}

interface CustomerRequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  slug: string;
  requireAuth?: boolean;
  token?: string;
  onResponse?: (response: Response) => void;
}

export async function customerApiRequest<T>(
  path: string,
  options: CustomerRequestOptions
): Promise<T> {
  const slug = options.slug.trim().toLowerCase();
  const token = options.token ?? getCustomerToken(slug);
  const session = getCustomerSessionIdentity(slug);
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Tenant-Slug": slug,
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method || "GET",
    headers,
    body:
      options.body !== undefined ? JSON.stringify(options.body) : undefined,
    cache: "no-store",
  });

  if (response.status === 401 && options.requireAuth && token &&
      token === getCustomerToken(slug) && session === getCustomerSessionIdentity(slug)) {
    clearCustomerToken(slug);
  }

  if (!response.ok) {
    const data = await response.json().catch(() => null) as { detail?: unknown } | null;
    throw new ApiError(response.status, apiErrorMessage(response.status, data?.detail));
  }

  options.onResponse?.(response);
  return (await response.json()) as T;
}

// ------------------------- Public Tenant & Services -------------------------
export async function fetchPublicTenant(
  slug: string
): Promise<PublicTenantResponse> {
  return customerApiRequest<PublicTenantResponse>(
    `/public/tenants/${encodeURIComponent(slug.trim().toLowerCase())}`,
    { slug }
  );
}

// ------------------------- Customer Auth -------------------------
export async function registerCustomer(
  slug: string,
  payload: { full_name: string; phone_number: string; password: string }
): Promise<TokenResponse> {
  return customerApiRequest<TokenResponse>("/auth/register", {
    method: "POST",
    slug,
    body: payload,
  });
}

export async function loginCustomer(
  slug: string,
  payload: { phone_number: string; password: string }
): Promise<TokenResponse> {
  return customerApiRequest<TokenResponse>("/auth/login", {
    method: "POST",
    slug,
    body: payload,
  });
}

export async function fetchCustomerMe(slug: string): Promise<MeResponse> {
  return customerApiRequest<MeResponse>("/auth/me", {
    slug,
    // The provider owns validation, including its request/session guard.
  });
}

// ------------------------- Available Slots & Bookings -------------------------
export async function fetchCustomerAvailableSlots(
  slug: string,
  params: {
    booking_id?: string;
    date: string;
    service_ids: string[];
    staff_id?: string | null;
  }
): Promise<AvailableSlotsResponse> {
  const qs = new URLSearchParams();
  qs.set("date", params.date);
  for (const sid of params.service_ids) {
    qs.append("service_ids", sid);
  }
  if (params.staff_id) {
    qs.set("staff_id", params.staff_id);
  }
  return customerApiRequest<AvailableSlotsResponse>(
    `${params.booking_id ? `/bookings/${params.booking_id}/available-slots` : "/bookings/available-slots"}?${qs.toString()}`,
    { slug }
  );
}

export async function createCustomerBooking(
  slug: string,
  payload: BookingCreateInput
): Promise<BookingRecord> {
  return customerApiRequest<BookingRecord>("/bookings", {
    method: "POST",
    slug,
    body: payload,
    requireAuth: true,
  });
}

export async function fetchCustomerBookings(
  slug: string,
  scope: "upcoming" | "history",
  options: { limit?: number; offset?: number; onResponse?: (response: Response) => void } = {}
): Promise<BookingRecord[]> {
  return customerApiRequest<BookingRecord[]>(
    `/bookings?scope=${scope}&limit=${options.limit ?? 100}&offset=${options.offset ?? 0}`,
    { slug, requireAuth: true, onResponse: options.onResponse }
  );
}

export async function fetchCustomerBookingPage(slug: string, scope: "upcoming" | "history", offset = 0): Promise<ListPage<BookingRecord>> {
  let response: Response | undefined;
  const items = await fetchCustomerBookings(slug, scope, { limit: 50, offset, onResponse: (value) => { response = value; } });
  return listPage(items, response, 50, offset);
}

export async function cancelCustomerBooking(
  slug: string,
  bookingId: string
): Promise<BookingRecord> {
  return customerApiRequest<BookingRecord>(`/bookings/${bookingId}/cancel`, {
    method: "POST",
    slug,
    requireAuth: true,
  });
}

export async function fetchMyCustomerPackages(slug: string): Promise<MyCustomerPackageItem[]> {
  return customerApiRequest<MyCustomerPackageItem[]>("/customer-packages/me", {
    slug, requireAuth: true,
  });
}

// ------------------------- Notifications & Web Push -------------------------
export async function fetchCustomerVapidKey(
  slug: string
): Promise<VapidPublicKeyResponse> {
  return customerApiRequest<VapidPublicKeyResponse>(
    "/notifications/vapid-public-key",
    { slug }
  );
}

export async function subscribeCustomerWebPush(
  slug: string,
  payload: {
    endpoint: string;
    keys: { p256dh: string; auth: string };
  }
): Promise<{ id: string; endpoint: string }> {
  return customerApiRequest<{ id: string; endpoint: string }>(
    "/notifications/subscribe",
    {
      method: "POST",
      slug,
      body: payload,
      requireAuth: true,
    }
  );
}

export async function unsubscribeCustomerWebPush(
  slug: string,
  endpoint: string,
  token?: string
): Promise<{ deleted: number }> {
  return customerApiRequest<{ deleted: number }>(
    "/notifications/unsubscribe",
    {
      method: "DELETE",
      slug,
      body: { endpoint },
      token,
    }
  );
}

export async function fetchCustomerNotifications(
  slug: string
): Promise<NotificationsListResponse> {
  return customerApiRequest<NotificationsListResponse>(
    "/notifications?limit=30&offset=0",
    { slug, requireAuth: true }
  );
}

export async function markAllCustomerNotificationsRead(
  slug: string
): Promise<{ updated: number }> {
  return customerApiRequest<{ updated: number }>(
    "/notifications/read-all",
    {
      method: "PATCH",
      slug,
      requireAuth: true,
    }
  );
}

export async function markCustomerNotificationRead(
  slug: string,
  notificationId: string
): Promise<NotificationItem> {
  return customerApiRequest<NotificationItem>(
    `/notifications/${notificationId}/read`,
    {
      method: "PATCH",
      slug,
      requireAuth: true,
    }
  );
}

export function rescheduleCustomerBooking(slug: string, id: string, payload: { start_time: string; staff_id: string | null; note: string | null }): Promise<BookingRecord> {
  return customerApiRequest<BookingRecord>(`/bookings/${id}`, { method: "PATCH", slug, body: payload, requireAuth: true });
}
