"use client";
import * as React from "react";
import { useAvailableSlots } from "@/lib/use-available-slots";
import { useNearestAvailableDay } from "@/lib/use-nearest-available-day";
import { formatDateISOInVN, formatTimeVN } from "@/lib/utils";
import type { ServiceItem, UserDetail } from "@/lib/types";
import { Input, Label } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export function AvailabilityFinder({ services, staff, onChoose }: {
  services: ServiceItem[]; staff: UserDetail[];
  onChoose: (serviceId: string, day: string, staffId: string, start: string) => void;
}): React.ReactElement {
  const [serviceId, setServiceId] = React.useState("");
  const [day, setDay] = React.useState(formatDateISOInVN);
  const [staffId, setStaffId] = React.useState("");
  const service = services.find((item) => item.id === serviceId && item.is_active);
  const validStaff = staffId && staff.some((item) => item.id === staffId && item.is_active) ? staffId : "";
  const ids = service ? [service.id] : [];
  const availability = useAvailableSlots({ date: day, serviceIds: ids, staffId: validStaff,
    enabled: Boolean(service) && day >= formatDateISOInVN(), autoSelect: false });
  const nearest = useNearestAvailableDay({ date: day, serviceIds: ids, staffId: validStaff,
    enabled: Boolean(service) && !availability.loading, onFound: setDay });
  return <section aria-label="Tìm giờ trống" className="space-y-4 rounded-xl border neu-surface bg-card p-4">
    <h2 className="font-bold">Tìm giờ trống cho khách</h2>
    <div className="grid gap-3 sm:grid-cols-3 [&>div]:min-w-0">
      <div><Label htmlFor="availableService">Dịch vụ</Label><select id="availableService" className="h-11 w-full min-w-0 rounded-md border bg-background px-2 text-base" value={serviceId} onChange={(event) => setServiceId(event.target.value)}>
        <option value="">Chọn dịch vụ để xem giờ trống</option>
        {services.filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.name} · {item.duration_minutes} phút</option>)}
      </select></div>
      <div><Label htmlFor="availableDay">Ngày muốn đến</Label><Input id="availableDay" type="date" min={formatDateISOInVN()} value={day} onChange={(event) => { if (event.target.value >= formatDateISOInVN()) setDay(event.target.value); }} /></div>
      <div><Label htmlFor="availableStaff">Nhân viên thực hiện</Label><select id="availableStaff" className="h-11 w-full min-w-0 rounded-md border bg-background px-2 text-base" value={validStaff} onChange={(event) => setStaffId(event.target.value)}>
        <option value="">Bất kỳ nhân viên phù hợp</option>{staff.filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.full_name}</option>)}
      </select></div>
    </div>
    {!service ? <p className="text-sm text-muted-foreground">Giờ trống được kiểm tra theo thời lượng dịch vụ, ca làm và lịch đã đặt.</p> : <>
      {availability.loading ? <p role="status">Đang kiểm tra giờ trống...</p> : availability.error ? <div role="alert"><p>{availability.error}</p><Button variant="outline" onClick={availability.retry}>Thử tải lại giờ trống</Button></div> : availability.slots.length === 0 ? <p>Ngày này chưa có giờ phù hợp. Hãy tìm ngày khác hoặc đổi nhân viên.</p> : <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-6">
        {availability.slots.map((slot) => <Button key={slot.start_time} variant="outline" className="h-auto min-h-11 min-w-0 flex-col whitespace-normal break-words py-2" onClick={() => onChoose(service.id, day, validStaff, slot.start_time)}>
          <span>{formatTimeVN(slot.start_time)} – {formatTimeVN(slot.end_time)}</span>
          <span className="text-xs font-normal">{slot.available_staff_ids.map((id) => staff.find((item) => item.id === id)?.full_name).filter(Boolean).join(", ") || "Có nhân viên phù hợp"}</span>
        </Button>)}
      </div>}
      <Button variant="outline" className="h-auto min-h-11 max-w-full whitespace-normal text-left" disabled={nearest.searching || availability.loading} onClick={() => void nearest.search()}>{nearest.searching ? "Đang tìm..." : "Tìm ngày còn chỗ trong 7 ngày tiếp theo"}</Button>
      {nearest.message && <p role="status" className="text-sm">{nearest.message}</p>}
      <p className="text-xs text-muted-foreground">Chọn giờ để tạo lịch cho khách. Giờ được kiểm tra lại trước khi lưu.</p>
    </>}
  </section>;
}
