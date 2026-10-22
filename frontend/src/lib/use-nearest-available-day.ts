"use client";
import * as React from "react";
import { fetchAvailableSlots } from "./api";
import { fetchCustomerAvailableSlots } from "./customer-api";
import { addDaysISO } from "./utils";

/** Bounded, user-initiated search. Changing scope cancels stale results. Never selects a time. */
export function useNearestAvailableDay({ date, serviceIds, staffId, slug, enabled, onFound }: {
  date: string; serviceIds: string[]; staffId?: string | null; slug?: string; enabled: boolean;
  onFound: (day: string) => void;
}) {
  const scope = JSON.stringify([date, serviceIds, staffId || null, slug || null, enabled]);
  const live = React.useRef(scope); live.current = scope;
  const request = React.useRef(0);
  const callback = React.useRef(onFound); callback.current = onFound;
  const busy = React.useRef(false);
  const [result, setResult] = React.useState({ scope: "", searching: false, message: "" });
  React.useEffect(() => { request.current += 1; busy.current = false; return () => { request.current += 1; }; }, [scope]);
  const search = async (): Promise<void> => {
    if (!enabled || !serviceIds.length || busy.current) return;
    busy.current = true;
    const attempt = ++request.current;
    const current = () => request.current === attempt && live.current === scope;
    setResult({ scope, searching: true, message: "" });
    try {
      for (let offset = 1; offset <= 7; offset++) {
        if (!current()) return;
        const day = addDaysISO(date, offset);
        const params = { date: day, service_ids: serviceIds, staff_id: staffId };
        const response = await (slug ? fetchCustomerAvailableSlots(slug, params) : fetchAvailableSlots(params));
        if (!current()) return;
        if (response.slots.length) { callback.current(day); return; }
      }
      if (current()) setResult({ scope, searching: false, message: "Chưa tìm thấy giờ phù hợp trong 7 ngày tiếp theo. Bạn có thể chọn ngày xa hơn hoặc đổi nhân viên." });
    } catch {
      if (current()) setResult({ scope, searching: false, message: "Chưa kiểm tra được lịch. Kiểm tra kết nối và thử lại." });
    } finally {
      if (current()) { busy.current = false; setResult((value) => ({ ...value, searching: false })); }
    }
  };
  return { search, searching: result.scope === scope && result.searching, message: result.scope === scope ? result.message : "" };
}
