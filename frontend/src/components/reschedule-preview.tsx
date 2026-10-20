import type { BookingRecord } from "@/lib/types";
import { formatCurrency, formatDateTimeVN } from "@/lib/utils";

export function ReschedulePreview({ booking, start, staffName, transfer = false }: {
  booking: BookingRecord; start: string; staffName: string; transfer?: boolean;
}): React.ReactElement {
  return <section aria-label="Thay đổi lịch hẹn" className="space-y-2 rounded-lg border bg-muted/40 p-3 text-sm [overflow-wrap:anywhere]">
    <p><strong>Hiện tại:</strong> {formatDateTimeVN(booking.start_time)} • {booking.staff_name || "Chưa có tên KTV"}</p>
    <p><strong>Sau khi lưu:</strong> {start ? `${formatDateTimeVN(start)} • ${staffName}` : "Chưa chọn giờ hợp lệ; lịch hiện tại chưa thay đổi"}</p>
    <p>Giữ thời lượng {booking.total_duration_minutes} phút và giá {formatCurrency(booking.total_price)}; không dùng thêm buổi thẻ.</p>
    <p>{transfer ? "Sẽ chuyển người phụ trách hồ sơ theo KTV mới." : "Giữ nguyên người phụ trách hồ sơ khách."}</p>
  </section>;
}
