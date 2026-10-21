import { apiRequest } from "./api";
import { customerApiRequest } from "./customer-api";
import type { BookingRecord, StaffScheduleItem, UserDetail } from "./types";
export interface DateOverride { day: string; start_time: string; end_time: string; is_day_off: boolean }
export interface PackageVisit { booking_id: string; start_time: string; status: BookingRecord["status"] }
export interface SetupSummary { services: number; staff: number; staff_with_hours: number; contact_ready: boolean; slug: string }
export const setupSummary = (): Promise<SetupSummary> => apiRequest("/tenants/me/setup");
export const customerDetail = (id: string): Promise<UserDetail> => apiRequest("/customers/" + encodeURIComponent(id));
export const getDateOverrides = (id: string): Promise<DateOverride[]> => apiRequest("/staff/" + encodeURIComponent(id) + "/date-overrides");
export const saveDateOverride = (id: string, body: DateOverride): Promise<{updated: boolean}> => apiRequest("/staff/" + encodeURIComponent(id) + "/date-overrides", { method: "PUT", body });
export const removeDateOverride = (id: string, day: string): Promise<{removed: boolean}> => apiRequest("/staff/" + encodeURIComponent(id) + "/date-overrides/" + day, { method: "DELETE" });
export const ownWorkHours = (): Promise<{week: StaffScheduleItem[]; overrides: DateOverride[]}> => apiRequest("/staff/me/work-hours");
export function packageVisits(id: string, offset: number, slug?: string): Promise<PackageVisit[]> {
  const path = "/customer-packages/" + encodeURIComponent(id) + "/history?limit=30&offset=" + offset;
  return slug ? customerApiRequest(path, { slug, requireAuth: true }) : apiRequest(path);
}
