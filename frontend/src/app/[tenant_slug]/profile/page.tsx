"use client";

import * as React from "react";
import { ProfileEditor } from "@/components/customer/profile-editor";
import { PackageHistory } from "@/components/package-history";
import { customerAuthHref } from "@/lib/customer-return-to";
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
  const [attempt, setAttempt] = React.useState(0);

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
  }, [slug, user, attempt]);

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
              href={customerAuthHref(slug, "login", `/${slug}/profile`)}
              className="inline-flex min-h-11 items-center justify-center rounded-xl px-5 text-xs font-bold text-white shadow"
              style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
            >
              Đăng nhập
            </Link>
            <Link
              href={customerAuthHref(slug, "register", `/${slug}/profile`)}
              className="inline-flex min-h-11 items-center justify-center rounded-xl border border-border bg-card px-5 text-xs font-semibold text-foreground"
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
    <div className="min-w-0 space-y-4 [overflow-wrap:anywhere]">
      {/* Personal Profile Card */}
      <Card>
        <CardContent className="p-4 flex min-w-0 flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <div
              className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-white font-bold text-base shadow-sm"
              style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
            >
              {user.full_name.slice(0, 1).toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-bold text-foreground flex items-center gap-1.5">
                <UserIcon className="h-3.5 w-3.5 text-muted-foreground" />
                {user.full_name}
              </p>
              <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                <Phone className="h-3.5 w-3.5" />
                {user.phone_number}
              </p>
              <Badge variant="secondary" className="mt-1 max-w-full whitespace-normal">
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

      <ProfileEditor key={user.id} />
      {/* Treatment Packages Section */}
      <div className="grid min-w-0 gap-3 md:grid-cols-2">
        <div className="space-y-2 md:col-span-2">
          <h2 className="flex items-center gap-1.5 text-sm font-bold text-foreground">
            <Ticket className="h-4 w-4" style={{ color: "var(--brand-text)" }} />
            Thẻ liệu trình đang sở hữu ({packages.length})
          </h2>
          <p className="text-xs text-muted-foreground">Số buổi trong thẻ không xác nhận tình trạng thanh toán. Liên hệ spa để đối chiếu tiền đã thu.</p>
        </div>

        {loadingPkgs ? (
          <Card>
            <CardContent className="p-8 text-center text-xs text-muted-foreground">
              Đang tải thông tin thẻ liệu trình...
            </CardContent>
          </Card>
        ) : packageError ? (
          <div role="alert" className="space-y-2 text-sm text-rose-700"><p>{packageError}</p><Button variant="outline" onClick={() => setAttempt((value) => value + 1)}>Thử tải lại thẻ</Button></div>
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
            const exhausted = pkg.status === "COMPLETED" || pkg.used_sessions >= pkg.total_sessions;
            const expired = pkg.status === "EXPIRED" || Boolean(pkg.expiry_date && new Date(pkg.expiry_date).getTime() <= Date.now());
            const held = !exhausted && !expired && pkg.status === "ACTIVE" && pkg.available_sessions === 0 && pkg.reserved_sessions > 0;
            const canBookWithPkg = pkg.status === "ACTIVE" && !exhausted && !expired && pkg.available_sessions > 0;
            const stateLabel = exhausted ? "Đã dùng hết" : expired ? "Đã hết hạn" : held ? "Đã giữ chỗ hết buổi" : "Đang sử dụng";
            return (
              <Card key={pkg.id} data-layout-card="customer-package" className="min-w-0">
                <CardContent className="p-4 space-y-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-bold text-foreground">
                        {pkg.package_name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Ngày mở thẻ: {formatDateTimeVN(pkg.created_at)}
                        {pkg.expiry_date &&
                          ` • Hạn dùng: ${formatDateTimeVN(pkg.expiry_date)}`}
                      </p>
                    </div>
                    <Badge
                      variant={expired ? "danger" : exhausted || held ? "secondary" : "success"}
                    >
                      {stateLabel}
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
                  {held && (
                    <p className="text-xs text-muted-foreground">Các buổi còn lại đã được đặt lịch. Xem mục Lịch hẹn để kiểm tra hoặc thay đổi.</p>
                  )}
                  <PackageHistory key={pkg.id} id={pkg.id} slug={slug} />
                  {canBookWithPkg && (
                    <div className="flex justify-end pt-1">
                      <Link
                        href={`/${slug}/book?service_id=${pkg.service_id}&package_id=${pkg.id}`}
                        className="inline-flex min-h-11 items-center gap-1.5 rounded-lg px-3.5 text-xs font-bold text-white shadow-sm"
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
