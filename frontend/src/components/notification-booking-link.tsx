"use client";
import * as React from "react";
import { assertAdminNavigationSafe } from "@/lib/branch-guard";
import { Button } from "@/components/ui/button";

export function NotificationBookingLink({ bookingId, slug, disabled }: { bookingId: string; slug?: string; disabled?: boolean }): React.ReactElement {
  const [error, setError] = React.useState("");
  const open = async (): Promise<void> => {
    const href = (slug ? "/" + encodeURIComponent(slug) + "/appointments" : "/admin/bookings") + "?" + new URLSearchParams({ booking_id: bookingId });
    try {
      if (!slug) assertAdminNavigationSafe();
      window.location.assign(href);
    } catch { setError("Hãy lưu hoặc hoàn tất công việc đang làm trước khi mở lịch hẹn."); }
  };
  return <><Button type="button" size="sm" variant="outline" disabled={disabled} onClick={() => void open()}>Xem lịch hẹn</Button>{error && <p role="alert">{error}</p>}</>;
}
