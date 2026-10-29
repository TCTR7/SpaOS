"use client";

import * as React from "react";
import { Modal } from "@/components/ui/modal";
import { ScreenHelp } from "@/components/screen-help";
import { ProductGuide } from "@/components/product-guide";
import { SpaLogo } from "@/components/spa-logo";
import { ContactLinks } from "@/components/contact-links";
import { NetworkStatus } from "@/components/network-status";
import { useBrandColor } from "@/components/brand-provider";
import { brandStyle } from "@/lib/brand-theme";
import Link from "@/components/spa-link";
import { usePathname } from "@/lib/spa-navigation";
import {
  MoreHorizontal,
  CircleHelp,
  AlertTriangle,
  CalendarCheck2,
  Clock,
  Sparkles,
  Ticket,
  User as UserIcon,
} from "lucide-react";
import { useCustomerTenant } from "./customer-context";
import { CustomerNotificationBell } from "./customer-notification-bell";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export function CustomerShell({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  const pathname = usePathname();
  const [moreOpen, setMoreOpen] = React.useState(false);
  const moreButton = React.useRef<HTMLButtonElement>(null);
  const focused = /\/(book|login|register)\/?$/.test(pathname || "");
  const widthClass = focused ? "max-w-md md:max-w-2xl" : "max-w-md md:max-w-4xl lg:max-w-5xl";
  const { slug, tenant, tenantLoading, tenantNotFound, tenantError, refreshTenant, user, authLoading, authError, refreshCustomer, logoutCustomer } =
    useCustomerTenant();

  const brandColor = useBrandColor(tenant?.theme_color);
  if (tenantLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <div className="flex flex-col items-center gap-2 text-center text-sm text-muted-foreground">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <span>Đang tải thông tin Spa...</span>
        </div>
      </div>
    );
  }

  if (tenantError) return <div className="flex min-h-screen items-center justify-center p-4">
    <div role="alert" className="max-w-sm space-y-3 text-center">
      <p>{tenantError}</p><Button onClick={() => void refreshTenant()}>Thử lại</Button>
    </div>
  </div>;

  if (tenantNotFound || !tenant) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <div className="w-full max-w-sm rounded-2xl border border-border neu-surface bg-card p-6 text-center shadow-md space-y-3">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-rose-100 text-rose-600">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <h1 className="text-lg font-bold text-foreground">
            Không tìm thấy spa
          </h1>
          <p className="text-xs text-muted-foreground">
            Đường dẫn Spa không tồn tại hoặc đã ngưng hoạt động. Vui lòng kiểm
            tra lại mã QR hoặc đường dẫn từ lễ tân.
          </p>
          <Link
            href="/"
            className="inline-flex min-h-11 items-center justify-center rounded-md bg-primary px-4 text-xs font-semibold text-primary-foreground shadow"
          >
            Chọn chi nhánh
          </Link>
        </div>
      </div>
    );
  }

  const themeColor = "var(--brand-color)";
  const baseHref = `/${tenant.slug}`;

  const navItems = [
    {
      href: baseHref,
      label: "Dịch vụ",
      icon: Sparkles,
      exact: true,
    },
    {
      href: `${baseHref}/book`,
      label: "Đặt lịch",
      icon: CalendarCheck2,
      exact: false,
    },
    {
      href: `${baseHref}/appointments`,
      label: "Lịch hẹn",
      icon: Clock,
      exact: false,
    },
    {
      href: `${baseHref}/profile`,
      label: "Thẻ & Hồ sơ",
      icon: Ticket,
      exact: false,
    },
  ];

  return (
    <div
      className="min-h-screen bg-background flex justify-center"
      style={brandStyle(brandColor)}
    >
      {/* Mobile-first container */}
      <div className={cn("relative flex min-h-screen w-full min-w-0 flex-col bg-background shadow-xl border-x border-border/60", widthClass)}>
        {/* Sticky Brand Header */}
        <header className="sticky top-0 z-30 flex items-center justify-between gap-2 border-b border-border neu-surface bg-card/95 px-4 py-3 backdrop-blur">
          <Link
            href={baseHref}
            className="flex min-w-0 items-center gap-2.5"
          >
            <SpaLogo key={tenant.id} name={tenant.name} src={tenant.logo_url} />
            <div className="min-w-0">
              <p className="text-base font-bold leading-snug text-foreground [overflow-wrap:anywhere]">
                {tenant.name}
              </p>
              <p className="text-xs text-muted-foreground">
                Mở cửa: {tenant.open_time.slice(0, 5)} –{" "}
                {tenant.close_time.slice(0, 5)}
              </p>
            </div>
          </Link>

          <div className="flex items-center gap-2">
            {user ? (
              <>
                <CustomerNotificationBell
                  slug={tenant.slug}
                  themeColor={themeColor}
                />
                <Link
                  href={`${baseHref}/profile`}
                  className="inline-flex min-h-11 items-center gap-1.5 rounded-full border border-border bg-muted/60 px-2.5 py-1 text-xs font-medium text-foreground"
                >
                  <UserIcon className="h-3.5 w-3.5" style={{ color: "var(--brand-text)" }} />
                  <span className="max-w-[60px] truncate sm:max-w-[90px]">
                    {user.full_name}
                  </span>
                </Link>
              </>
            ) : (
              <Link
                href={`${baseHref}/login`}
                className="inline-flex min-h-11 items-center justify-center rounded-full px-3.5 text-xs font-semibold text-white shadow-sm transition hover:opacity-90"
                style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
              >
                Đăng nhập khách hàng
              </Link>
            )}
          </div>
        </header>
        <NetworkStatus />
        <div className="px-4"><Link href="/admin/login" className="action-link text-xs">Dành cho chủ spa / nhân viên → Trang quản lý</Link><ContactLinks address={tenant.address} phone={tenant.contact_phone} /></div>

        {/* Main Scrollable Content */}
        <main className="flex-1 px-4 py-4 pb-[calc(6rem+env(safe-area-inset-bottom))]">
          {(authLoading || authError) && <div className="space-y-3 py-8 text-center" role="status">
            {authError ? <><p role="alert">{authError}</p>
              <Button onClick={() => void refreshCustomer()}>Thử lại</Button>
              <Button variant="outline" onClick={() => void logoutCustomer()}>Đăng xuất</Button></>
              : <p>Đang kiểm tra đăng nhập...</p>}
          </div>}
          <ScreenHelp role="CUSTOMER" identity={user?.id || tenant.id} slug={slug}/>
          {/* Keep an inline-login draft mounted, but inaccessible until verified. */}
          <div hidden={authLoading || Boolean(authError)}><ProductGuide key={user?.id || "guest"} role="CUSTOMER" slug={slug} identity={user?.id} autoOpen={!authLoading && !authError && pathname === baseHref} />{children}</div>
        </main>

        <Modal open={moreOpen} onClose={() => setMoreOpen(false)} title="Thêm" returnFocusRef={moreButton}>
          <nav aria-label="Điều hướng bổ sung" className="neu-nav space-y-2">
            <Link className="flex min-h-12 items-center gap-3 rounded-lg px-3 text-sm hover:bg-accent" href={baseHref + "/help"} onClick={() => setMoreOpen(false)}><CircleHelp className="h-5 w-5 shrink-0" />Trợ giúp &amp; Cài ứng dụng</Link>
            <Link className="flex min-h-12 items-center rounded-lg px-3 text-sm hover:bg-accent" href="/admin/login" onClick={() => setMoreOpen(false)}>Đăng nhập quản lý</Link>
          </nav>
        </Modal>
        {/* Bottom Navigation Bar */}
        <nav aria-label="Điều hướng khách hàng" className={cn("neu-nav fixed bottom-0 z-30 flex w-full items-center justify-around border-t border-border neu-surface bg-card/95 pt-1.5 pb-[max(0.375rem,env(safe-area-inset-bottom))] backdrop-blur", widthClass)}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = item.exact
              ? pathname === item.href
              : pathname === item.href ||
                pathname?.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex min-h-12 min-w-0 flex-1 flex-col items-center justify-center gap-0.5 rounded-lg px-1 py-1 text-xs font-medium transition",
                  active ? "font-bold" : "text-muted-foreground"
                )}
                style={active ? { color: "var(--brand-text)" } : undefined}
              >
                <Icon className="h-5 w-5" />
                <span>{item.label}</span>
              </Link>
            );
          })}
          <button type="button" ref={moreButton} onClick={() => setMoreOpen(true)} aria-haspopup="dialog" aria-expanded={moreOpen} className="flex min-h-12 min-w-0 flex-1 flex-col items-center justify-center gap-0.5 px-1 text-xs text-muted-foreground"><MoreHorizontal className="h-5 w-5" /><span>Thêm</span></button>
        </nav>
      </div>
    </div>
  );
}
