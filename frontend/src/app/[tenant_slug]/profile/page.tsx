"use client";

import * as React from "react";
import Link from "next/link";
import {
  CalendarPlus,
  LogOut,
  Phone,
  Ticket,
  User as UserIcon,
} from "lucide-react";
import { fetchMyCustomerPackages } from "@/lib/customer-api";
import type { MyCustomerPackageItem } from "@/lib/types";
import { formatDateTimeVN } from "@/lib/utils";
import { useCustomerTenant } from "@/components/customer/customer-context";
import { Button } from "@/components/ui/button";
import { Badge, Card, CardContent } from "@/components/ui/card";

export default function CustomerProfilePage(): React.ReactElement | null {
  const { slug, tenant, user, authLoading, logoutCustomer } =
    useCustomerTenant();
  const [packages, setPackages] = React.useState<MyCustomerPackageItem[]>([]);
  const [loadingPkgs, setLoadingPkgs] = React.useState<boolean>(false);

  const [packageError, setPackageError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setPackageError(null);
    if (!user) {
      setPackages([]);
      return;
    }
    let cancelled = false;
    setLoadingPkgs(true);
    setPackages([]);
    void (async () => {
      try {
        const list = await fetchMyCustomerPackages(slug);
        if (!cancelled) setPackages(list);
      } catch (err) {
        if (!cancelled) setPackageError(err instanceof Error ? err.message : "Không thể tải thẻ liệu trình. Vui lòng tải lại trang.");
      } finally {
        if (!cancelled) setLoadingPkgs(false);
      }
    })();
    return () => { cancelled = true; };
  }, [slug, user]);

  if (!tenant) return null;
  const themeColor = "var(--brand-color)";

  if (!user && !authLoading) {
    return (
      <Card>
        <CardContent className="p-6 text-center space-y-3">
          <Ticket
            className="mx-auto h-10 w-10"
            style={{ color: "var(--brand-text)" }}
          />
          <h2 className="text-base font-bold text-foreground">
            Quản lý Thẻ liệu trình & Hồ sơ cá nhân
          </h2>
          <p className="text-xs text-muted-foreground">
            Đăng nhập để xem số buổi còn lại trong thẻ liệu trình và đặt lịch
            trừ buổi trực tuyến.
          </p>
          <div className="flex justify-center gap-2">
            <Link
              href={`/${slug}/login`}
              className="inline-flex h-9 items-center justify-center rounded-xl px-5 text-xs font-bold text-white shadow"
              style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
            >
              Đăng nhập
            </Link>
            <Link
              href={`/${slug}/register`}
              className="inline-flex h-9 items-center justify-center rounded-xl border border-border bg-card px-5 text-xs font-semibold text-foreground"
            >
              Đăng ký
            </Link>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!user) return null;

  return (
    <div className="space-y-4">
      {/* Personal Profile Card */}
      <Card>
        <CardContent className="p-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div
              className="flex h-12 w-12 items-center justify-center rounded-full text-white font-bold text-base shadow-xs"
              style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
            >
              {user.full_name.slice(0, 1).toUpperCase()}
            </div>
            <div>
              <p className="text-sm font-bold text-foreground flex items-center gap-1.5">
                <UserIcon className="h-3.5 w-3.5 text-muted-foreground" />
                {user.full_name}
              </p>
              <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                <Phone className="h-3.5 w-3.5" />
                {user.phone_number}
              </p>
              <Badge variant="secondary" className="mt-1">
                Thành viên {tenant.name}
              </Badge>
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            className="text-rose-600"
            onClick={() => void logoutCustomer()}
          >
            <LogOut className="h-4 w-4" />
            Thoát
          </Button>
        </CardContent>
      </Card>

      {/* Treatment Packages Section */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-1.5 text-sm font-bold text-foreground">
            <Ticket className="h-4 w-4" style={{ color: "var(--brand-text)" }} />
            Thẻ liệu trình đang sở hữu ({packages.length})
          </h2>
        </div>

        {loadingPkgs ? (
          <Card>
            <CardContent className="p-8 text-center text-xs text-muted-foreground">
              Đang tải thông tin thẻ liệu trình...
            </CardContent>
          </Card>
        ) : packageError ? (
          <p role="alert" className="text-sm text-rose-700">{packageError}</p>
        ) : packages.length === 0 ? (
          <Card>
            <CardContent className="p-6 text-center space-y-2">
              <p className="text-xs text-muted-foreground">
                Bạn hiện chưa có thẻ liệu trình nào hoặc có thể chọn gói liệu
                trình trực tiếp tại mục Đặt lịch.
              </p>
              <Link
                href={`/${slug}/book`}
                className="inline-flex min-h-11 items-center justify-center rounded-lg px-4 text-xs font-semibold text-white"
                style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
              >
                Khám phá Gói liệu trình
              </Link>
            </CardContent>
          </Card>
        ) : (
          packages.map((pkg) => {
            const pct = Math.min(
              100,
              Math.round(
                (pkg.used_sessions / Math.max(pkg.total_sessions, 1)) * 100
              )
            );
            const canBookWithPkg =
              pkg.status === "ACTIVE" && pkg.available_sessions > 0;
            return (
              <Card key={pkg.id} data-layout-card="customer-package">
                <CardContent className="p-4 space-y-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-bold text-foreground">
                        {pkg.package_name}
                      </p>
                      <p className="text-[11px] text-muted-foreground">
                        Ngày mở thẻ: {formatDateTimeVN(pkg.created_at)}
                        {pkg.expiry_date &&
                          ` • Hạn dùng: ${formatDateTimeVN(pkg.expiry_date)}`}
                      </p>
                    </div>
                    <Badge
                      variant={
                        pkg.status === "ACTIVE"
                          ? "success"
                          : pkg.status === "COMPLETED"
                            ? "secondary"
                            : "danger"
                      }
                    >
                      {{ ACTIVE: "Đang sử dụng", COMPLETED: "Đã dùng hết", EXPIRED: "Đã hết hạn" }[pkg.status]}
                    </Badge>
                  </div>

                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                      <span>
                        Đã dùng:{" "}
                        <strong>
                          {pkg.used_sessions}/{pkg.total_sessions} buổi
                        </strong>
                      </span>
                      <span
                        className="font-bold"
                        style={{ color: "var(--brand-text)" }}
                      >
                        Có thể đặt thêm: {pkg.available_sessions} buổi
                      </span>
                    </div>
                    <div className="h-2.5 w-full overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full transition-all"
                        style={{
                          width: `${pct}%`,
                          backgroundColor: themeColor, color: "var(--brand-foreground)",
                        }}
                      />
                    </div>
                  </div>

                  <p className="text-xs text-muted-foreground">
                    Chưa dùng: {pkg.remaining_sessions} buổi • Đã đặt lịch: {pkg.reserved_sessions} buổi
                  </p>
                  {pkg.status === "ACTIVE" && pkg.available_sessions === 0 && pkg.reserved_sessions > 0 && (
                    <p className="text-xs text-muted-foreground">Các buổi còn lại đã được đặt lịch. Xem mục Lịch hẹn để kiểm tra hoặc thay đổi.</p>
                  )}
                  {canBookWithPkg && (
                    <div className="flex justify-end pt-1">
                      <Link
                        href={`/${slug}/book?service_id=${pkg.service_id}&package_id=${pkg.id}`}
                        className="inline-flex min-h-11 items-center gap-1.5 rounded-lg px-3.5 text-xs font-bold text-white shadow-xs"
                        style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
                      >
                        <CalendarPlus className="h-3.5 w-3.5" />
                        Dùng 1 buổi trong thẻ
                      </Link>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}
