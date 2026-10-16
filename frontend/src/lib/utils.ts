import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { BookingStatus } from "./types";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: string | number): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (Number.isNaN(num)) return "0 ₫";
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(num);
}

export function formatDateTimeVN(iso: string): string {
  const dt = new Date(iso);
  return new Intl.DateTimeFormat("vi-VN", {
    timeZone: "Asia/Ho_Chi_Minh",
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(dt);
}

export function formatTimeVN(iso: string): string {
  const dt = new Date(iso);
  return new Intl.DateTimeFormat("vi-VN", {
    timeZone: "Asia/Ho_Chi_Minh",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(dt);
}

export function formatDateISOInVN(date: Date = new Date()): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Ho_Chi_Minh",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const year = parts.find((p) => p.type === "year")?.value ?? "2026";
  const month = parts.find((p) => p.type === "month")?.value ?? "01";
  const day = parts.find((p) => p.type === "day")?.value ?? "01";
  return `${year}-${month}-${day}`;
}

export function addDaysISO(dateISO: string, days: number): string {
  const [y, m, d] = dateISO.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d + days, 12, 0, 0));
  return dt.toISOString().slice(0, 10);
}

export function getWeekDaysISO(anchorDateISO: string): string[] {
  const [y, m, d] = anchorDateISO.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d, 12, 0, 0));
  const dayOfWeek = dt.getUTCDay(); // 0 = Sunday .. 6 = Saturday
  const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
  const result: string[] = [];
  for (let i = 0; i < 7; i++) {
    const cur = new Date(Date.UTC(y, m - 1, d + mondayOffset + i, 12, 0, 0));
    result.push(cur.toISOString().slice(0, 10));
  }
  return result;
}

export const DAY_OF_WEEK_LABELS: Record<number, string> = {
  1: "Thứ 2",
  2: "Thứ 3",
  3: "Thứ 4",
  4: "Thứ 5",
  5: "Thứ 6",
  6: "Thứ 7",
  0: "Chủ Nhật",
};

export const BOOKING_STATUS_META: Record<
  BookingStatus,
  { label: string; badgeClass: string; cardClass: string; next: BookingStatus[] }
> = {
  PENDING: {
    label: "Chờ xác nhận",
    badgeClass: "bg-amber-100 text-amber-800 border-amber-300",
    cardClass: "border-l-4 border-l-amber-500 bg-amber-50/70",
    next: ["CONFIRMED", "CANCELLED"],
  },
  CONFIRMED: {
    label: "Đã xác nhận",
    badgeClass: "bg-blue-100 text-blue-800 border-blue-300",
    cardClass: "border-l-4 border-l-blue-500 bg-blue-50/70",
    next: ["IN_PROGRESS", "COMPLETED", "CANCELLED", "NO_SHOW"],
  },
  IN_PROGRESS: {
    label: "Đang thực hiện",
    badgeClass: "bg-purple-100 text-purple-800 border-purple-300",
    cardClass: "border-l-4 border-l-purple-500 bg-purple-50/70",
    next: ["COMPLETED", "CANCELLED"],
  },
  COMPLETED: {
    label: "Hoàn thành",
    badgeClass: "bg-emerald-100 text-emerald-800 border-emerald-300",
    cardClass: "border-l-4 border-l-emerald-500 bg-emerald-50/70",
    next: [],
  },
  CANCELLED: {
    label: "Đã hủy",
    badgeClass: "bg-slate-200 text-slate-700 border-slate-300",
    cardClass: "border-l-4 border-l-slate-400 bg-slate-100/70 opacity-75",
    next: [],
  },
  NO_SHOW: {
    label: "Vắng mặt",
    badgeClass: "bg-rose-100 text-rose-800 border-rose-300",
    cardClass: "border-l-4 border-l-rose-500 bg-rose-50/70",
    next: [],
  },
};

export function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}
