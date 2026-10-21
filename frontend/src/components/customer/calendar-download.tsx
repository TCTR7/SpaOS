"use client";
import * as React from "react";
import { Button } from "@/components/ui/button";
import type { BookingRecord } from "@/lib/types";
function escapeCalendar(value: string): string { return value.replace(/\\/g, "\\\\").replace(/\r?\n/g, "\\n").replace(/,/g, "\\,").replace(/;/g, "\\;"); }
function instant(value: string): string { return new Date(value).toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, ""); }
export function CalendarDownload({ booking, location }: {booking: BookingRecord; location?: string | null}): React.ReactElement | null {
  if (["CANCELLED", "NO_SHOW", "COMPLETED"].includes(booking.status)) return null;
  const download = () => {
    const title = "Lịch hẹn spa" + (booking.status === "PENDING" ? " (chờ xác nhận)" : "");
    const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//SpaOS//Appointments//VI", "BEGIN:VEVENT", "UID:" + booking.id + "@spaos", "DTSTAMP:" + instant(new Date().toISOString()), "DTSTART:" + instant(booking.start_time), "DTEND:" + instant(booking.end_time), "SUMMARY:" + escapeCalendar(title), "DESCRIPTION:" + escapeCalendar("Kiểm tra trạng thái mới nhất trong ứng dụng spa. Thay đổi trong ứng dụng không tự cập nhật tệp lịch này."), "STATUS:" + (booking.status === "PENDING" ? "TENTATIVE" : "CONFIRMED"), ...(location ? ["LOCATION:" + escapeCalendar(location)] : []), "END:VEVENT", "END:VCALENDAR"];
    const url = URL.createObjectURL(new Blob([lines.map((line) => { let folded = "", bytes = 0; for (const character of line) { const size = new TextEncoder().encode(character).length; if (bytes + size > 75) { folded += "\r\n "; bytes = 1; } folded += character; bytes += size; } return folded; }).join("\r\n") + "\r\n"], {type: "text/calendar;charset=utf-8"}));
    const link = document.createElement("a"); link.href = url; link.download = "lich-hen.ics"; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return <div className="space-y-1"><Button variant="outline" type="button" onClick={download}>Thêm vào lịch cá nhân</Button><p className="text-xs text-muted-foreground">Tệp lịch không tự cập nhật khi bạn đổi hoặc hủy lịch hẹn.</p></div>;
}
