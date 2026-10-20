"use client";

import * as React from "react";
import Link from "next/link";
import { CalendarPlus, Clock, Sparkles, Ticket } from "lucide-react";
import { useCustomerTenant } from "@/components/customer/customer-context";
import { formatCurrency } from "@/lib/utils";
import { Badge, Card, CardContent } from "@/components/ui/card";

export default function TenantPublicHomePage(): React.ReactElement | null {
  const { tenant } = useCustomerTenant();
  const [filterType, setFilterType] = React.useState<
    "all" | "single" | "package"
  >("all");

  if (!tenant) return null;

  const themeColor = "var(--brand-color)";
  const singleServices = tenant.services.filter((s) => !s.is_package);
  const packageServices = tenant.services.filter((s) => s.is_package);

  const visibleServices =
    filterType === "single"
      ? singleServices
      : filterType === "package"
        ? packageServices
        : tenant.services;

  return (
    <div className="min-w-0 space-y-5 [overflow-wrap:anywhere]">
      {/* Hero Banner */}
      <div
        className="rounded-2xl p-5 text-white shadow-md space-y-3"
        style={{
          background: `linear-gradient(135deg, var(--brand-text), #1e293b)`,
        }}
      >
        <div className="inline-flex items-center gap-1.5 rounded-full bg-white/20 px-3 py-1 text-[11px] font-semibold backdrop-blur-xs">
          <Sparkles className="h-3.5 w-3.5" />
          Đặt lịch Online 24/7 • Không cần chờ đợi
        </div>
        <h1 className="text-xl font-bold leading-snug">{tenant.name}</h1>
        <p className="text-xs text-white/85">
          Giờ hoạt động: {tenant.open_time.slice(0, 5)} –{" "}
          {tenant.close_time.slice(0, 5)} • Nghỉ chuẩn bị phòng:{" "}
          {tenant.buffer_minutes} phút
        </p>
        <div className="pt-1">
          <Link
            href={`/${tenant.slug}/book`}
            className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-xs font-bold shadow transition hover:opacity-95"
            style={{ color: "var(--brand-text)" }}
          >
            <CalendarPlus className="h-4 w-4" />
            Đặt lịch hẹn ngay
          </Link>
        </div>
      </div>

      {/* Category Filter Tabs */}
      <div className="flex items-center justify-between gap-2">
        <div className="inline-flex rounded-xl border border-border bg-muted p-1 text-xs font-semibold">
          <button
            type="button"
            onClick={() => setFilterType("all")}
            className={`rounded-lg px-3 py-1.5 transition ${
              filterType === "all"
                ? "bg-card text-foreground shadow-xs"
                : "text-muted-foreground"
            }`}
          >
            Tất cả ({tenant.services.length})
          </button>
          <button
            type="button"
            onClick={() => setFilterType("single")}
            className={`rounded-lg px-3 py-1.5 transition ${
              filterType === "single"
                ? "bg-card text-foreground shadow-xs"
                : "text-muted-foreground"
            }`}
          >
            Dịch vụ lẻ ({singleServices.length})
          </button>
          <button
            type="button"
            onClick={() => setFilterType("package")}
            className={`rounded-lg px-3 py-1.5 transition ${
              filterType === "package"
                ? "bg-card text-foreground shadow-xs"
                : "text-muted-foreground"
            }`}
          >
            Liệu trình ({packageServices.length})
          </button>
        </div>
      </div>

      {/* Services List */}
      <div className="grid min-w-0 gap-3 md:grid-cols-2">
        {visibleServices.length === 0 ? (
          <Card>
            <CardContent className="p-8 text-center text-xs text-muted-foreground">
              Hiện chưa có dịch vụ nào trong danh mục này.
            </CardContent>
          </Card>
        ) : (
          visibleServices.map((svc) => (
            <Card
              key={svc.id}
              className="overflow-hidden transition hover:shadow-md"
            >
              <CardContent className="p-4 space-y-2.5">
                  <div className="flex min-w-0 flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      {svc.is_package ? (
                        <Badge variant="default" className="gap-1">
                          <Ticket className="h-3 w-3" />
                          Liệu trình {svc.total_sessions} buổi
                        </Badge>
                      ) : (
                        <Badge variant="secondary">Dịch vụ lẻ</Badge>
                      )}
                      <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        {svc.duration_minutes} phút
                      </span>
                    </div>
                    <h3 className="mt-1.5 text-sm font-bold text-foreground">
                      {svc.name}
                    </h3>
                  </div>
                  <p
                    className="text-sm font-extrabold shrink-0"
                    style={{ color: "var(--brand-text)" }}
                  >
                    {formatCurrency(svc.price)}
                  </p>
                </div>

                {svc.description && (
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {svc.description}
                  </p>
                )}

                <div className="flex justify-end pt-1">
                  <Link
                    href={`/${tenant.slug}/book?service_id=${svc.id}`}
                    className="inline-flex h-8 items-center justify-center rounded-lg px-3.5 text-xs font-semibold text-white shadow-xs transition hover:opacity-90"
                    style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
                  >
                    Chọn đặt lịch
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
