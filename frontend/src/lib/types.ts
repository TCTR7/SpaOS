export type UserRole = "ADMIN" | "STAFF" | "CUSTOMER";

export interface AuthUser {
  id: string;
  tenant_id: string;
  role: UserRole;
  full_name: string;
  phone_number: string;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export interface TenantInfo {
  id: string;
  slug: string;
  name: string;
  logo_url: string | null;
  theme_color: string | null;
  open_time?: string;
  close_time?: string;
  buffer_minutes: number;
  status: string;
}

export interface MeResponse {
  user: AuthUser;
  tenant: TenantInfo;
}

export interface ServiceItem {
  id: string;
  name: string;
  description: string | null;
  duration_minutes: number;
  price: string;
  is_package: boolean;
  total_sessions: number;
  is_active: boolean;
}

export interface PublicTenantResponse {
  id: string;
  slug: string;
  name: string;
  logo_url: string | null;
  theme_color: string | null;
  open_time: string;
  close_time: string;
  buffer_minutes: number;
  services: ServiceItem[];
}

export interface UserDetail {
  assigned_staff_id?: string | null;
  id: string;
  tenant_id: string;
  role: UserRole;
  full_name: string;
  phone_number: string;
  notes: string | null;
  is_active: boolean;
  created_at: string;
}

export interface StaffScheduleItem {
  id?: string;
  staff_id?: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  is_day_off: boolean;
}

export type PackageStatus = "ACTIVE" | "COMPLETED" | "EXPIRED";

export interface CustomerPackageItem {
  purchase_price?: string | null;
  id: string;
  tenant_id: string;
  customer_id: string;
  service_id: string;
  package_name: string;
  total_sessions: number;
  used_sessions: number;
  remaining_sessions: number;
  expiry_date: string | null;
  status: PackageStatus;
  created_at: string;
}

export interface MyCustomerPackageItem extends CustomerPackageItem {
  reserved_sessions: number;
  available_sessions: number;
}

export type BookingStatus =
  | "PENDING"
  | "CONFIRMED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "CANCELLED"
  | "NO_SHOW";

export interface BookingItemDetail {
  id: string;
  service_id: string;
  customer_package_id: string | null;
  duration_minutes: number;
  price: string;
}

export interface BookingRecord {
  id: string;
  tenant_id: string;
  customer_id: string;
  staff_id: string | null;
  start_time: string;
  end_time: string;
  total_duration_minutes: number;
  total_price: string;
  status: BookingStatus;
  note: string | null;
  created_at: string;
  items: BookingItemDetail[];
}

export interface SlotItem {
  start_time: string;
  end_time: string;
  available_staff_ids: string[];
}

export interface AvailableSlotsResponse {
  date: string;
  total_duration_minutes: number;
  buffer_minutes: number;
  slot_step_minutes: number;
  slots: SlotItem[];
}

export interface BookingCreateInput {
  start_time: string;
  staff_id?: string | null;
  customer_id?: string;
  note?: string | null;
  items: {
    service_id: string;
    customer_package_id?: string | null;
  }[];
}

export interface StaffPerformanceItem {
  staff_id: string;
  full_name: string;
  is_active: boolean;
  completed_bookings_count: number;
  completed_services_count: number;
  single_services_count: number;
  package_sessions_count: number;
  total_revenue: string;
}

export interface StaffPerformanceReport {
  start_date: string;
  end_date: string;
  timezone: string;
  staff: StaffPerformanceItem[];
  totals: {
    completed_bookings_count: number;
    completed_services_count: number;
    single_services_count: number;
    package_sessions_count: number;
    total_revenue: string;
  };
}

export type NotificationType =
  | "BOOKING_CREATED"
  | "BOOKING_CONFIRMED"
  | "BOOKING_IN_PROGRESS"
  | "BOOKING_COMPLETED"
  | "BOOKING_CANCELLED"
  | "BOOKING_NO_SHOW"
  | string;

export interface NotificationItem {
  id: string;
  title: string;
  body: string;
  type: NotificationType;
  booking_id: string | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationsListResponse {
  unread_count: number;
  items: NotificationItem[];
}

export interface VapidPublicKeyResponse {
  public_key: string;
  enabled: boolean;
}

export interface PaymentInvoice {
  id: string;
  customer_id: string;
  booking_id: string | null;
  customer_package_id: string | null;
  amount_due: string;
  amount_paid: string;
  balance_due: string;
  status: "UNPAID" | "PARTIAL" | "PAID";
  created_at: string;
}
export interface PaymentEntry {
  id: string;
  invoice_id: string;
  amount: string;
  method: "CASH" | "BANK_TRANSFER";
  recorded_by: string;
  created_at: string;
  reversal_of: string | null;
  note: string | null;
}
export interface AuditEvent {
  id: string;
  actor_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  details: Record<string, unknown>;
  created_at: string;
}
export interface PaymentSummary {
  date_from: string;
  date_to: string;
  timezone: string;
  cash: string;
  bank_transfer: string;
  net_received: string;
}

export interface PaymentCollection {
  source_id: string;
  source_type: "booking" | "package";
  customer_id: string;
  customer_name: string;
  phone_number: string;
  description: string;
  occurred_at: string;
  source_status: string;
  invoice_id: string | null;
  amount_due: string | null;
  amount_paid: string;
  balance_due: string | null;
  status: "UNPAID" | "PARTIAL" | "PAID" | "NEEDS_PRICE" | "COVERED" | "FREE";
}

export interface BranchAccess { tenant: TenantInfo; user: AuthUser; is_owner: boolean }
export interface DashboardMetrics {
  appointments: number; in_progress: number; completed: number;
  cash: string; bank_transfer: string; net_received: string; completed_value: string;
  outstanding: string; unknown_prices: number; active_packages: number;
}
export interface BranchDashboard {
  date: string; timezone: string;
  branches: { branch_id: string; name: string; metrics: DashboardMetrics }[];
  totals: DashboardMetrics;
}
