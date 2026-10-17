"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Wallet,
  CalendarDays,
  LogOut,
  Menu,
  Settings,
  Sparkles,
  UserCheck,
  Users,
  X,
} from "lucide-react";
import { useAdminAuth } from "./auth-context";
import { NotificationBell } from "./notification-bell";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { UserRole } from "@/lib/types";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  roles: UserRole[];
}

const NAV_ITEMS: NavItem[] = [
  { href: "/admin/dashboard", label: "Tổng quan", icon: BarChart3, roles: ["ADMIN"] },
  { href: "/admin/branches", label: "Chi nhánh", icon: Users, roles: ["ADMIN"] },
  { href: "/admin/payments", label: "Thu tiền", icon: Wallet, roles: ["ADMIN"] },
  {
    href: "/admin/bookings",
    label: "Lịch hẹn (Calendar)",
    icon: CalendarDays,
    roles: ["ADMIN", "STAFF"],
  },
  {
    href: "/admin/customers",
    label: "Khách hàng & Liệu trình",
    icon: Users,
    roles: ["ADMIN", "STAFF"],
  },
  {
    href: "/admin/services",
    label: "Danh mục Dịch vụ",
    icon: Sparkles,
    roles: ["ADMIN", "STAFF"],
  },
  {
    href: "/admin/staff",
    label: "Nhân sự & Ca làm việc",
    icon: UserCheck,
    roles: ["ADMIN"],
  },
  {
    href: "/admin/reports",
    label: "Báo cáo Hoa hồng",
    icon: BarChart3,
    roles: ["ADMIN"],
  },
  {
    href: "/admin/settings",
    label: "Cấu hình Spa",
    icon: Settings,
    roles: ["ADMIN"],
  },
];

export function AdminShell({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  const pathname = usePathname();
  const { user, tenant, loading, logout, branches, changeBranch } = useAdminAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState<boolean>(false);

  const [branchBusy, setBranchBusy] = React.useState(false);
  const [branchError, setBranchError] = React.useState<string | null>(null);
  const [allScope, setAllScope] = React.useState(false);
  React.useEffect(() => { setAllScope(pathname === "/admin/dashboard" && new URLSearchParams(window.location.search).get("scope") === "all"); }, [pathname]);

  const isPublicAuthRoute =
    pathname?.startsWith("/admin/login") ||
    pathname?.startsWith("/admin/register-tenant");

  if (isPublicAuthRoute) {
    return <>{children}</>;
  }

  if (loading || !user || !tenant) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-2 text-sm text-muted-foreground">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <span>Đang tải không gian quản trị SpaOS...</span>
        </div>
      </div>
    );
  }

  const allowedNavItems = NAV_ITEMS.filter((item) =>
    item.roles.includes(user.role) && (item.href !== "/admin/branches" || branches.some((b) => b.tenant.id === tenant.id && b.is_owner))
  );

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      {/* Sidebar Desktop */}
      <aside className="hidden w-64 shrink-0 flex-col border-r border-border bg-card md:flex">
        <div className="flex h-16 items-center gap-3 border-b border-border px-5">
          <div
            className="flex h-9 w-9 items-center justify-center rounded-lg text-sm font-bold text-white shadow-sm"
            style={{
              backgroundColor: tenant.theme_color || "#be185d",
            }}
          >
            {tenant.name.slice(0, 1).toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-bold text-foreground">
              {tenant.name}
            </p>
            <p className="truncate text-xs text-muted-foreground">
              Chi nhánh đang làm việc
            </p>
          </div>
        </div>

        <nav className="flex-1 space-y-1 p-3">
          {allowedNavItems.map((item) => {
            const Icon = item.icon;
            const active =
              pathname === item.href || pathname?.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  active
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-slate-700 hover:bg-accent hover:text-accent-foreground"
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-border p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="min-w-0">
              <p className="truncate text-xs font-semibold text-foreground">
                {user.full_name}
              </p>
              <p className="truncate text-[11px] text-muted-foreground">
                {user.phone_number}
              </p>
            </div>
            <Badge variant={user.role === "ADMIN" ? "default" : "secondary"}>
              {user.role}
            </Badge>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="w-full justify-start text-rose-600 hover:text-rose-700"
            onClick={() => void logout()}
          >
            <LogOut className="h-4 w-4" />
            Đăng xuất
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top Header */}
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-card/90 px-4 backdrop-blur md:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="rounded-md p-2 text-slate-700 hover:bg-muted md:hidden"
              aria-label="Mở menu"
            >
              {mobileMenuOpen ? (
                <X className="h-5 w-5" />
              ) : (
                <Menu className="h-5 w-5" />
              )}
            </button>
<div className="min-w-0">
              <label className="sr-only" htmlFor="activeBranch">Chi nhánh đang làm việc</label>
              <select id="activeBranch" className="h-9 max-w-[210px] rounded-md border bg-background px-2 text-sm" disabled={branchBusy}
                value={allScope ? "all" : tenant.id} onChange={async (e) => {
                  const id = e.target.value;
                  if (id === "all") { window.location.assign("/admin/dashboard?scope=all"); return; }
                  if (id === tenant.id && allScope) { window.location.assign("/admin/dashboard"); return; }
                  setBranchBusy(true); setBranchError(null);
                  try { await changeBranch(id); } catch (e) { setBranchError(e instanceof Error ? e.message : "Không chuyển được chi nhánh"); setBranchBusy(false); }
                }}>
                {branches.length === 0 && <option value={tenant.id}>{tenant.name}</option>}
                {branches.map((b) => <option key={b.tenant.id} value={b.tenant.id}>{b.tenant.name}</option>)}
                {user.role === "ADMIN" && branches.some((b) => b.tenant.id === tenant.id && b.is_owner) && <option value="all">Tất cả chi nhánh</option>}
              </select>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <NotificationBell />
            <div className="hidden items-center gap-2 border-l border-border pl-3 sm:flex">
              <div className="text-right">
                <p className="text-xs font-semibold text-foreground">
                  {user.full_name}
                </p>
                <p className="text-[11px] text-muted-foreground">
                  {user.role === "ADMIN" ? "Chủ Spa / Quản lý" : "Kỹ thuật viên"}
                </p>
              </div>
            </div>
          </div>
        </header>

        {/* Mobile Nav Drawer */}
        {mobileMenuOpen && (
          <div className="border-b border-border bg-card p-3 md:hidden">
            <nav className="space-y-1">
              {allowedNavItems.map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium",
                      active
                        ? "bg-primary text-primary-foreground"
                        : "text-slate-700 hover:bg-accent"
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>
            <div className="mt-3 border-t border-border pt-3">
              <Button
                variant="outline"
                size="sm"
                className="w-full justify-start text-rose-600"
                onClick={() => void logout()}
              >
                <LogOut className="h-4 w-4" />
                Đăng xuất ({user.full_name})
              </Button>
            </div>
          </div>
        )}

        <main className="flex-1 p-4 md:p-6">{branchError && <p role="alert" className="mb-3 text-rose-700">{branchError}</p>}<div key={tenant.id}>{children}</div></main>
      </div>
    </div>
  );
}
