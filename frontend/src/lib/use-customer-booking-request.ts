"use client";
import * as React from "react";
import { ApiError } from "./api";
import { customerApiRequest, getCustomerSessionIdentity } from "./customer-api";
import type { BookingCreateInput, BookingRecord } from "./types";
export function useCustomerBookingRequest(slug: string, userId?: string) {
  const key = userId ? "spaos_booking_request_" + slug + "_" + userId : "";
  const live = React.useRef(key); live.current = key;
  const alive = React.useRef(false), flight = React.useRef(false);
  const id = React.useRef("");
  const operation = React.useRef(0);
  const payload = React.useRef<BookingCreateInput | null>(null);
  const [state, setState] = React.useState({ key: "", uncertain: false, busy: false, message: "" });
  React.useEffect(() => {
    operation.current += 1; alive.current = true; flight.current = false; payload.current = null;
    const stored = key ? sessionStorage.getItem(key) : null;
    id.current = stored && /^[a-f0-9-]{36}$/.test(stored) ? stored : "";
    setState({ key, uncertain: Boolean(id.current), busy: false, message: "" });
    return () => { alive.current = false; };
  }, [key]);
  const matching = state.key === key;
  const saved = async (requestId: string): Promise<BookingRecord | null> => {
    try { return await customerApiRequest<BookingRecord>("/booking-requests/" + requestId, { slug, requireAuth: true }); }
    catch (e) { if (e instanceof ApiError && e.status === 404) return null; throw e; }
  };
  const finish = (booking: BookingRecord, current: () => boolean): BookingRecord | null => {
    if (!current()) return null;
    sessionStorage.removeItem(key); id.current = ""; payload.current = null;
    setState({ key, uncertain: false, busy: false, message: "" }); return booking;
  };
  const submit = async (body: BookingCreateInput): Promise<BookingRecord | null> => {
    if (!key || !matching || flight.current || (state.uncertain && !payload.current)) return null;
    flight.current = true;
    const request = ++operation.current;
    const identity = getCustomerSessionIdentity(slug);
    const current = () => alive.current && operation.current === request && live.current === key && identity === getCustomerSessionIdentity(slug);
    if (!id.current) id.current = crypto.randomUUID();
    const requestId = id.current;
    if (!payload.current) payload.current = body;
    sessionStorage.setItem(key, requestId);
    setState({ key, uncertain: false, busy: true, message: "" });
    try {
      const booking = await customerApiRequest<BookingRecord>("/booking-requests", { slug, method: "POST", requireAuth: true, body: { ...payload.current, request_id: requestId } });
      return finish(booking, current);
    } catch (e) {
      if (!current()) return null;
      if (e instanceof ApiError && e.status === 409) {
        try { const existing = await saved(requestId); if (existing) return finish(existing, current); } catch (lookupError) {
          if (current()) setState({ key, uncertain: true, busy: false, message: "Chưa kiểm tra được lịch đã lưu. Vui lòng kiểm tra lại trước khi đặt tiếp." });
          throw lookupError;
        }
      }
      if (e instanceof ApiError && e.status >= 400 && e.status < 500 && e.status !== 401) {
        payload.current = null; setState({ key, uncertain: false, busy: false, message: "" });
      } else setState({ key, uncertain: true, busy: false, message: "Chưa xác định lịch đã được lưu hay chưa. Hãy kiểm tra kết quả trước khi đặt tiếp." });
      throw e;
    } finally { if (operation.current === request) flight.current = false; if (current()) setState((old) => ({ ...old, busy: false })); }
  };
  const check = async (): Promise<BookingRecord | null> => {
    if (!key || !id.current || flight.current) return null; flight.current = true;
    const request = ++operation.current;
    const identity = getCustomerSessionIdentity(slug);
    const current = () => alive.current && operation.current === request && live.current === key && identity === getCustomerSessionIdentity(slug);
    setState((old) => ({ ...old, busy: true, message: "" }));
    try {
      const booking = await saved(id.current);
      if (booking) return finish(booking, current);
      if (current()) { payload.current = null; setState({ key, uncertain: false, busy: false, message: "Chưa có lịch được lưu cho yêu cầu này. Bạn có thể kiểm tra giờ và xác nhận lại." }); }
    } catch { if (current()) setState({ key, uncertain: true, busy: false, message: "Chưa kiểm tra được kết quả. Kết nối lại rồi thử kiểm tra." }); }
    finally { if (operation.current === request) flight.current = false; if (current()) setState((old) => ({ ...old, busy: false })); }
    return null;
  };
  return { submit, check, retry: () => payload.current ? submit(payload.current) : check(), ready: matching,
    uncertain: matching && state.uncertain, busy: matching && state.busy, canRetry: Boolean(payload.current), message: matching ? state.message : "" };
}
