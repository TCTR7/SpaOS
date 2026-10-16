import { API_BASE_URL, ApiError } from "./api";
import type {
  AvailableSlotsResponse,
  BookingCreateInput,
  BookingRecord,
  CustomerPackageItem,
  MeResponse,
  NotificationItem,
  NotificationsListResponse,
  PublicTenantResponse,
  TokenResponse,
  VapidPublicKeyResponse,
} from "./types";

function tokenKeyForSlug(slug: string): string {
  return `spaos_customer_token_${slug.toLowerCase()}`;
}

export function getCustomerToken(slug: string): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(tokenKeyForSlug(slug));
}

export function saveCustomerToken(slug: string, token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(tokenKeyForSlug(slug), token);
}

export function clearCustomerToken(slug: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(tokenKeyForSlug(slug));
}

interface CustomerRequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  slug: string;
  requireAuth?: boolean;
}

export async function customerApiRequest<T>(
  path: string,
  options: CustomerRequestOptions
): Promise<T> {
  const slug = options.slug.trim().toLowerCase();
  const token = getCustomerToken(slug);
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

  if (response.status === 401 && options.requireAuth) {
    clearCustomerToken(slug);
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
      // ignore json parse error
    }
    throw new ApiError(response.status, detail);
  }

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
    requireAuth: true,
  });
}

// ------------------------- Available Slots & Bookings -------------------------
export async function fetchCustomerAvailableSlots(
  slug: string,
  params: {
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
    `/bookings/available-slots?${qs.toString()}`,
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
  scope: "upcoming" | "history"
): Promise<BookingRecord[]> {
  return customerApiRequest<BookingRecord[]>(
    `/bookings?scope=${scope}&limit=100`,
    { slug, requireAuth: true }
  );
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

export async function fetchMyCustomerPackages(
  slug: string,
  customerId: string
): Promise<CustomerPackageItem[]> {
  try {
    return await customerApiRequest<CustomerPackageItem[]>(
      `/customers/${customerId}/packages`,
      { slug, requireAuth: true }
    );
  } catch {
    return [];
  }
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
    user_agent?: string;
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
  endpoint: string
): Promise<{ unsubscribed: boolean }> {
  return customerApiRequest<{ unsubscribed: boolean }>(
    "/notifications/unsubscribe",
    {
      method: "DELETE",
      slug,
      body: { endpoint },
      requireAuth: true,
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
): Promise<{ marked_read: number }> {
  return customerApiRequest<{ marked_read: number }>(
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
