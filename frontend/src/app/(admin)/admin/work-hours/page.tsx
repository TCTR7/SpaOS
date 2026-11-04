"use client";
import * as React from "react";
import { WorkforceEditor } from "@/components/admin/workforce-editor";
import AdminServicesPage from "@/app/(admin)/admin/services/page";
import { useAdminAuth } from "@/components/admin/auth-context";

export default function WorkHoursPage(): React.ReactElement {
  const { user } = useAdminAuth();
  const [tab, setTab] = React.useState<"hours" | "services">("hours");
  if (user?.role !== "STAFF") return <p>Chủ spa xem và sắp xếp ca tại Nhân sự &amp; Ca làm việc.</p>;
  return (
    <div className="min-w-0 space-y-4">
      <div className="flex flex-wrap gap-1 rounded-xl border border-border bg-muted p-1 text-sm font-semibold">
        <button type="button" onClick={() => setTab("hours")} className={`min-h-10 flex-1 rounded-lg px-3 py-1.5 transition ${tab === "hours" ? "neu-surface bg-card text-foreground shadow-sm" : "text-muted-foreground"}`}>
          Ca làm của tôi
        </button>
        <button type="button" onClick={() => setTab("services")} className={`min-h-10 flex-1 rounded-lg px-3 py-1.5 transition ${tab === "services" ? "neu-surface bg-card text-foreground shadow-sm" : "text-muted-foreground"}`}>
          Bảng giá Dịch vụ
        </button>
      </div>
      {tab === "services" ? <AdminServicesPage /> : <WorkforceEditor key={user.id} staffId={user.id} readOnly />}
    </div>
  );
}
