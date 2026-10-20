import { apiRequest } from "./api";
import type { PaymentInvoice, PaymentEntry, AuditEvent, PaymentSummary } from "./types";

export const listPaymentInvoices = (offset = 0): Promise<PaymentInvoice[]> =>
  apiRequest(`/payments/invoices?limit=50&offset=${offset}`);
export const openPaymentInvoice = (body: { booking_id?: string; customer_package_id?: string; legacy_amount_due?: string }): Promise<PaymentInvoice> =>
  apiRequest("/payments/invoices", { method: "POST", body });
export const listPaymentEntries = (id: string, offset = 0): Promise<PaymentEntry[]> =>
  apiRequest(`/payments/invoices/${id}/entries?limit=100&offset=${offset}`);
export const recordReceipt = (id: string, body: { amount: string; method: "CASH" | "BANK_TRANSFER"; note: string | null; idempotency_key: string }): Promise<PaymentEntry> =>
  apiRequest(`/payments/invoices/${id}/receipts`, { method: "POST", body });
export const voidReceipt = (id: string, body: { reason: string; idempotency_key: string }): Promise<PaymentEntry> =>
  apiRequest(`/payments/entries/${id}/void`, { method: "POST", body });
export const getPaymentSummary = (from: string, to: string): Promise<PaymentSummary> =>
  apiRequest(`/payments/summary?date_from=${encodeURIComponent(from)}&date_to=${encodeURIComponent(to)}`);
export const listAuditEvents = (entityId?: string, offset = 0): Promise<AuditEvent[]> =>
  apiRequest(`/audit-logs?limit=50&offset=${offset}${entityId ? "&entity_id=" + encodeURIComponent(entityId) : ""}`);

export function formatPaymentCurrency(value: string | number): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "Không rõ";
  return new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND", minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(amount);
}

export const listCollections = (q: string, scope: "outstanding" | "all", offset = 0): Promise<import("./types").PaymentCollection[]> =>
  apiRequest(`/payments/collections?q=${encodeURIComponent(q)}&scope=${scope}&limit=50&offset=${offset}`);
