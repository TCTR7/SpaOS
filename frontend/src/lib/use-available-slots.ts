"use client";

import * as React from "react";
import { ApiError, fetchAvailableSlots } from "./api";
import { fetchCustomerAvailableSlots } from "./customer-api";
import type { SlotItem } from "./types";
import { formatTimeVN } from "./utils";

/** Only a successful response for the current scope permits selecting/submitting. */
export function useAvailableSlots({ date, serviceIds, staffId, enabled, slug, preferredStart, bookingId, autoSelect = true }: {
  date: string; serviceIds: string[]; staffId?: string | null; enabled: boolean;
  slug?: string; preferredStart?: string; bookingId?: string; autoSelect?: boolean;
}): {
  slots: SlotItem[]; loading: boolean; error: string | null; retry: () => void;
  selectedStart: string; select: (start: string) => void;
} {
  const scope = JSON.stringify([date, serviceIds, staffId || null, slug || null, preferredStart || null, bookingId || null]);
  const activeScope = enabled && date && serviceIds.length ? scope : null;
  const [attempt, setAttempt] = React.useState(0);
  const [choice, setChoice] = React.useState("");
  const [result, setResult] = React.useState<{ scope: string | null; slots: SlotItem[]; error: string | null; ready: boolean }>({
    scope: null, slots: [], error: null, ready: false,
  });

  React.useEffect(() => {
    if (!activeScope) {
      setResult({ scope: null, slots: [], error: null, ready: false });
      setChoice("");
      return;
    }
    let cancelled = false;
    const [day, services, staff, tenantSlug, preferred, booking] = JSON.parse(activeScope) as [string, string[], string | null, string | null, string | null, string | null];
    setResult({ scope: activeScope, slots: [], error: null, ready: false });
    const params = { date: day, service_ids: services, staff_id: staff, booking_id: booking || undefined };
    void (tenantSlug ? fetchCustomerAvailableSlots(tenantSlug, params) : fetchAvailableSlots(params))
      .then((response) => {
        if (cancelled) return;
        setChoice((previous) => response.slots.some((slot) => slot.start_time === previous) ? previous :
          (preferred && response.slots.find((slot) => booking
            ? new Date(slot.start_time).getTime() === new Date(preferred).getTime()
            : formatTimeVN(slot.start_time) === formatTimeVN(preferred))?.start_time) || (!booking && autoSelect ? response.slots[0]?.start_time : "") || "");
        setResult({ scope: activeScope, slots: response.slots, error: null, ready: true });
      }).catch((error: unknown) => {
        if (!cancelled) setResult({ scope: activeScope, slots: [], error: error instanceof ApiError && error.status < 500
          ? error.message : "Không tải được khung giờ. Kiểm tra kết nối và thử lại.", ready: false });
      });
    return () => { cancelled = true; };
  }, [activeScope, attempt, autoSelect]);

  const matching = Boolean(activeScope && result.scope === activeScope);
  const verified = matching && result.ready;
  return {
    slots: verified ? result.slots : [],
    loading: Boolean(activeScope && (!matching || (!result.ready && !result.error))),
    error: matching ? result.error : null,
    retry: () => {
      setResult((previous) => ({ ...previous, ready: false, error: null }));
      setAttempt((previous) => previous + 1);
    },
    selectedStart: verified && result.slots.some((slot) => slot.start_time === choice) ? choice : "",
    select: (start) => { if (verified && result.slots.some((slot) => slot.start_time === start)) setChoice(start); },
  };
}
