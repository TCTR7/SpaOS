"use client";
import * as React from "react";
import { ownWorkHours, type DateOverride } from "@/lib/experience-api";
import type { StaffScheduleItem } from "@/lib/types";
import { displayDate } from "@/lib/display-date";
import { Badge } from "@/components/ui/card";
import { DAY_OF_WEEK_LABELS } from "@/lib/utils";
import { useAdminAuth } from "@/components/admin/auth-context";
import { Button } from "@/components/ui/button";
export default function WorkHoursPage(): React.ReactElement {
  const { user } = useAdminAuth();
  const [data, setData] = React.useState<{week: StaffScheduleItem[]; overrides: DateOverride[]} | null>(null);
  const [error, setError] = React.useState(false), [attempt, setAttempt] = React.useState(0);
  React.useEffect(() => { if (user?.role !== "STAFF") return; let cancelled = false; setData(null); setError(false);
    void ownWorkHours().then((value) => { if (!cancelled) setData(value); }).catch(() => { if (!cancelled) setError(true); });
    return () => { cancelled = true; };
  }, [user?.id, user?.tenant_id, user?.role, attempt]);
  if (user?.role !== "STAFF") return <p>Chủ spa xem và sắp xếp ca tại Nhân sự & Ca làm việc.</p>;
  return <div className="mx-auto max-w-3xl space-y-4"><h1 className="text-xl font-bold">Ca làm của tôi</h1><p className="text-sm">Liên hệ chủ spa nếu bạn cần đổi ca hoặc nghỉ một ngày.</p>
    {error ? <div role="alert"><p>Chưa tải được ca làm.</p><Button onClick={() => setAttempt((value) => value + 1)}>Thử lại ca làm</Button></div> : !data ? <p role="status">Đang tải ca...</p> : <>
      {data.week.length === 0 && <p>Chủ spa chưa sắp xếp ca tuần cho bạn.</p>}
      <div className="grid gap-3 sm:grid-cols-2">{data.week.map((row) => <div key={row.day_of_week} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-card p-4"><span className="font-semibold">{DAY_OF_WEEK_LABELS[row.day_of_week]}</span>{row.is_day_off ? <Badge variant="secondary">Nghỉ</Badge> : <span className="text-sm tabular-nums">{row.start_time.slice(0,5)} – {row.end_time.slice(0,5)}</span>}</div>)}</div>
      {data.overrides.length > 0 && <section className="space-y-2"><h2 className="font-semibold">Thay đổi theo ngày</h2>{data.overrides.map((row) => <p key={row.day} className="rounded-xl border bg-card p-4 text-sm">{displayDate(row.day)} · {row.is_day_off ? "Nghỉ" : row.start_time.slice(0,5) + " – " + row.end_time.slice(0,5)}</p>)}</section>}
    </>}
  </div>;
}
