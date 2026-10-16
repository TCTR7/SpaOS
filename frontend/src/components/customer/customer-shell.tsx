"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
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

export function CustomerShell({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  const pathname = usePathname();
  const { slug, tenant, tenantLoading, tenantNotFound, user } =
    useCustomerTenant();

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

  if (tenantNotFound || !tenant) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-6 text-center shadow-md space-y-3">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-rose-100 text-rose-600">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <h1 className="text-lg font-bold text-foreground">
            Không tìm thấy Spa ({slug})
          </h1>
          <p className="text-xs text-muted-foreground">
            Đường dẫn Spa không tồn tại hoặc đã ngưng hoạt động. Vui lòng kiểm
            tra lại mã QR hoặc đường dẫn từ lễ tân.
          </p>
          <Link
            href="/spa-demo"
            className="inline-flex h-9 items-center justify-center rounded-md bg-primary px-4 text-xs font-semibold text-primary-foreground shadow"
          >
            Thử truy cập Spa mẫu (/spa-demo)
          </Link>
        </div>
      </div>
    );
  }

  const themeColor = tenant.theme_color || "#be185d";
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
      className="min-h-screen bg-slate-100/80 flex justify-center"
      style={{ "--spa-brand": themeColor } as React.CSSProperties}
    >
      {/* Mobile-first container */}
      <div className="relative flex min-h-screen w-full max-w-md flex-col bg-background shadow-xl border-x border-border/60">
        {/* Sticky Brand Header */}
        <header className="sticky top-0 z-30 flex items-center justify-between gap-2 border-b border-border bg-card/95 px-4 py-3 backdrop-blur">
          <Link
            href={baseHref}
            className="flex min-w-0 items-center gap-2.5"
          >
            {tenant.logo_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={tenant.logo_url}
                alt={tenant.name}
                className="h-9 w-9 rounded-xl object-cover border border-border"
              />
            ) : (
              <div
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-sm font-bold text-white shadow-xs"
                style={{ backgroundColor: themeColor }}
              >
                {tenant.name.slice(0, 1).toUpperCase()}
              </div>
            )}
            <div className="min-w-0">
              <p className="truncate text-sm font-bold text-foreground">
                {tenant.name}
              </p>
              <p className="text-[11px] text-muted-foreground">
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
                  className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/60 px-2.5 py-1 text-xs font-medium text-foreground"
                >
                  <UserIcon className="h-3.5 w-3.5" style={{ color: themeColor }} />
                  <span className="max-w-[90px] truncate">
                    {user.full_name}
                  </span>
                </Link>
              </>
            ) : (
              <Link
                href={`${baseHref}/login`}
                className="inline-flex h-8 items-center justify-center rounded-full px-3.5 text-xs font-semibold text-white shadow-xs transition hover:opacity-90"
                style={{ backgroundColor: themeColor }}
              >
                Đăng nhập
              </Link>
            )}
          </div>
        </header>

        {/* Main Scrollable Content */}
        <main className="flex-1 px-4 py-4 pb-24">{children}</main>

        {/* Bottom Navigation Bar */}
        <nav className="fixed bottom-0 z-30 flex w-full max-w-md items-center justify-around border-t border-border bg-card/95 py-1.5 backdrop-blur">
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
                className={cn(
                  "flex flex-col items-center gap-0.5 rounded-lg px-3 py-1 text-[11px] font-medium transition",
                  active ? "font-bold" : "text-muted-foreground"
                )}
                style={active ? { color: themeColor } : undefined}
              >
                <Icon className="h-5 w-5" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
