"use client";

import * as React from "react";
import { SpaLogo } from "@/components/spa-logo";
import { ProductGuide } from "@/components/product-guide";
import { StaffWorkplace } from "./staff-workplace";
import { StaffAvatar } from "./staff-avatar";
import { NetworkStatus } from "@/components/network-status";
import { useBrandColor, useBranding } from "@/components/brand-provider";
import { brandStyle } from "@/lib/brand-theme";
import { spaPath } from "@/lib/spa-path";
import Link from "@/components/spa-link";
import { usePathname, useRouter, useSearchParams } from "@/lib/spa-navigation";
import {
  Building2,
  BarChart3,
  Wallet,
  CalendarDays,
  LogOut,
  MoreHorizontal,
  Settings,
  CircleHelp,
  Sparkles,
  UserCheck,
  Users,
} from "lucide-react";
import { useAdminAuth } from "./auth-context";
import { NotificationBell } from "./notification-bell";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { BranchDirtyError, withBranchChange } from "@/lib/branch-guard";
import { ScreenHelp } from "@/components/screen-help";
import { UnfinishedWork } from "./unfinished-work";
import type { UserRole } from "@/lib/types";

interface NavItem {
  href: string;
  match?: string[];
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  roles: UserRole[];
}

const NAV_ITEMS: NavItem[] = [
  { href: "/admin/dashboard", match: ["/admin/reports"], label: "Tổng quan & Báo cáo", icon: BarChart3, roles: ["ADMIN"] },
  { href: "/admin/bookings", label: "Lịch hẹn", icon: CalendarDays, roles: ["ADMIN", "STAFF"] },
  { href: "/admin/customers", label: "Khách hàng", icon: Users, roles: ["ADMIN", "STAFF"] },
  { href: "/admin/payments", label: "Thu tiền", icon: Wallet, roles: ["ADMIN"] },
  { href: "/admin/services", label: "Dịch vụ", icon: Sparkles, roles: ["ADMIN"] },
  { href: "/admin/staff", label: "Nhân sự & Ca làm", icon: UserCheck, roles: ["ADMIN"] },
  { href: "/admin/settings", match: ["/admin/brand", "/admin/branches"], label: "Cài đặt & Chi nhánh", icon: Settings, roles: ["ADMIN"] },
  { href: "/admin/work-hours", match: ["/admin/services"], label: "Ca làm & Dịch vụ", icon: CalendarDays, roles: ["STAFF"] },
];

export function AdminShell({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  return <React.Suspense fallback={<p role="status" className="p-4">Đang tải...</p>}>
    <AdminShellContent>{children}</AdminShellContent>
  </React.Suspense>;
}

function AdminShellContent({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  const { branding } = useBranding();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const moreButton = React.useRef<HTMLButtonElement>(null);
  const { user, tenant, loading, authError, refreshMe, logout, branches, changeBranch } = useAdminAuth();
  const brandColor = useBrandColor(tenant?.theme_color);
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState<boolean>(false);
  const [sessionNotice, setSessionNotice] = React.useState<string | null>(null);
  React.useEffect(() => {
    const notice = sessionStorage.getItem("spaos_session_notice");
    if (notice) setSessionNotice(notice);
    sessionStorage.removeItem("spaos_session_notice");
  }, []);

  React.useEffect(() => {
    const media = window.matchMedia("(min-width: 768px)");
    const closeOnDesktop = (): void => { if (media.matches) setMobileMenuOpen(false); };
    media.addEventListener("change", closeOnDesktop);
    return () => media.removeEventListener("change", closeOnDesktop);
  }, []);

  const [requestedBranch, setRequestedBranch] = React.useState<string | null>(null);
  const [branchBusy, setBranchBusy] = React.useState(false);
  const [branchError, setBranchError] = React.useState<string | null>(null);
  const allScope = pathname === "/admin/dashboard" && searchParams.get("scope") === "all";

  const isPublicAuthRoute =
    pathname?.startsWith("/admin/login") ||
    pathname === "/admin/recover" ||
    pathname?.startsWith("/admin/register-tenant");

  if (isPublicAuthRoute) {
    return <>{children}</>;
  }

  if (loading || !user || !tenant) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-2 text-sm text-muted-foreground">
          {authError ? <div role="alert" className="max-w-sm space-y-3 p-4 text-center">
            <p>{authError}</p>
            <Button onClick={() => void refreshMe()}>Thử lại</Button>
            <Button variant="outline" onClick={() => void logout()}>Đăng xuất</Button>
          </div> : <><div className="h-7 w-7 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <span>Đang tải...</span></>}
        </div>
      </div>
    );
  }

  const targetBranch = pathname === "/admin/bookings" ? searchParams.get("target_branch") : null;
  const linkedBranch = branches.find((branch) => branch.tenant.id === targetBranch);
  const allowedNavItems = NAV_ITEMS.filter((item) => item.roles.includes(user.role));

  const primaryPaths = user.role === "ADMIN"
    ? ["/admin/dashboard", "/admin/bookings", "/admin/customers", "/admin/payments"]
    : ["/admin/bookings", "/admin/customers", "/admin/work-hours"];
  const primaryItems = primaryPaths.flatMap((href) => allowedNavItems.filter((item) => item.href === href));
  const moreItems = [
    ...allowedNavItems.filter((item) => !primaryPaths.includes(item.href)),
    { href: "/admin/account", label: "Tài khoản của tôi", icon: UserCheck, roles: ["ADMIN", "STAFF"] as UserRole[] },
    { href: "/admin/help", label: "Trợ giúp & Cài ứng dụng", icon: CircleHelp, roles: ["ADMIN", "STAFF"] as UserRole[] },
  ];
  const isActive = (href: string, match: string[] = []): boolean =>
    [href, ...match].some((prefix) => pathname === prefix || pathname?.startsWith(prefix + "/") === true);
  const moreActive = moreItems.some((item) => isActive(item.href));
  const chooseBranch = async (id: string, discard = false): Promise<void> => {
    if (branchBusy || (id === tenant.id && !allScope)) return;
    setBranchBusy(true); setBranchError(null);
    try {
      if (id === "all" || (id === tenant.id && allScope)) {
        await withBranchChange(async () => {
          window.location.assign(spaPath(id === "all" ? "/admin/dashboard?scope=all" : "/admin/dashboard"));
        }, discard);
      } else await changeBranch(id, discard);
      setRequestedBranch(null);
    } catch (error) {
      if (error instanceof BranchDirtyError) setRequestedBranch(id);
      else { setRequestedBranch(null); setBranchError(error instanceof Error ? error.message : "Không chuyển được chi nhánh"); }
    } finally { setBranchBusy(false); }
  };
  const navigateFromMore = (event: React.MouseEvent<HTMLAnchorElement>, href: string): void => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
    event.preventDefault();
    if (window.history.state?.spaosDialog) {
      window.addEventListener("popstate", () => queueMicrotask(() => router.push(href)), { once: true });
      window.history.back();
    } else { setMobileMenuOpen(false); router.push(href); }
  };

  return (
    <div className="flex min-h-screen bg-background text-foreground" style={brandStyle(brandColor)}>
      {/* Sidebar Desktop */}
      <aside className="hidden w-64 shrink-0 flex-col border-r border-border neu-surface bg-card md:flex">
        <div className="flex min-h-24 items-center gap-3 border-b border-border px-4 py-4">
          <Building2 className="h-7 w-7 shrink-0 text-primary" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <p className="text-base font-bold leading-snug [overflow-wrap:anywhere]">{branding.name || tenant.name}</p>
            <p className="mt-1 text-xs text-muted-foreground">{user.role === "ADMIN" ? "Quản lý spa" : "Nhân viên spa"}</p>
          </div>
        </div>

        <nav className="neu-nav flex-1 space-y-2 p-3">
          {allowedNavItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.href, item.match);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  active
                    ? "bg-background text-primary shadow-inner"
                    : "text-slate-700 hover:bg-accent hover:text-accent-foreground"
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="space-y-2 border-t border-border p-3">
          <Link
            href="/admin/account"
            aria-current={isActive("/admin/account") ? "page" : undefined}
            className={cn(
              "flex items-center gap-2.5 rounded-lg p-2 transition hover:bg-accent",
              isActive("/admin/account") && "bg-background text-primary shadow-inner"
            )}
          >
            <StaffAvatar name={user.full_name} src={user.photo_url} className="h-9 w-9 text-sm" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-semibold text-foreground">{user.full_name}</p>
              <p className="truncate text-xs text-muted-foreground">Tài khoản của tôi · {user.phone_number}</p>
            </div>
          </Link>
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
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border neu-surface bg-card/90 px-4 backdrop-blur md:px-6">
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <SpaLogo key={allScope ? "all" : tenant.id} name={tenant.name} src={tenant.logo_url} className="h-10 w-10 rounded-xl" />
            <div className="min-w-0">
              <label className="sr-only" htmlFor="activeBranch">Chi nhánh đang làm việc</label>
              <select id="activeBranch" className={cn("h-11 w-full max-w-[210px] min-w-0 rounded-md border bg-background px-2 text-sm", branches.length <= 1 && "hidden")} disabled={branchBusy}
                value={allScope ? "all" : tenant.id} onChange={(event) => void chooseBranch(event.target.value)}>
                {branches.length === 0 && <option value={tenant.id}>{tenant.name}</option>}
                {branches.map((b) => <option key={b.tenant.id} value={b.tenant.id}>{b.tenant.name}</option>)}
                {user.role === "ADMIN" && branches.some((b) => b.tenant.id === tenant.id && b.is_owner) && <option value="all">Tất cả chi nhánh</option>}
              </select>
              {branches.length <= 1 && <span title={tenant.name} className="block max-w-[210px] truncate text-sm font-semibold">{tenant.name}</span>}
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <Link
              href="/admin/help"
              title="Trợ giúp & Cài ứng dụng"
              aria-label="Trợ giúp & Cài ứng dụng"
              className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-border text-muted-foreground hover:bg-accent hover:text-foreground"
            >
              <CircleHelp className="h-5 w-5" />
            </Link>
            <NotificationBell />
            <Link href="/admin/account" className="hidden items-center gap-2 border-l border-border pl-3 sm:flex">
              <StaffAvatar name={user.full_name} src={user.photo_url} className="h-8 w-8 text-xs" />
              <span className="max-w-[140px] truncate text-xs font-semibold text-foreground">{user.full_name}</span>
            </Link>
          </div>
        </header>
        <NetworkStatus />

        <Modal open={requestedBranch !== null} title="Bỏ thay đổi chưa lưu?"
          onClose={() => { if (!branchBusy) setRequestedBranch(null); }}>
          <p className="mb-4 text-sm">Bạn có thay đổi chưa lưu tại chi nhánh này. Bỏ thay đổi để chuyển?</p>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" disabled={branchBusy} onClick={() => setRequestedBranch(null)}>Tiếp tục chỉnh sửa</Button>
            <Button variant="destructive" disabled={branchBusy} onClick={() => { if (requestedBranch) void chooseBranch(requestedBranch, true); }}>Bỏ thay đổi và chuyển</Button>
          </div>
        </Modal>
        <Modal open={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)}
          title="Thêm" historyGuard returnFocusRef={moreButton}>
          <nav aria-label="Điều hướng bổ sung" className="neu-nav space-y-1">
            {moreItems.map((item) => {
              const Icon = item.icon;
              return <Link key={item.href} href={item.href}
                onClick={(event) => navigateFromMore(event, item.href)}
                aria-current={isActive(item.href) ? "page" : undefined}
                className={cn("flex min-h-12 items-center gap-3 rounded-lg px-3 py-2 text-sm [overflow-wrap:anywhere]",
                  isActive(item.href) ? "bg-background text-primary shadow-inner" : "hover:bg-accent")}>
                <Icon className="h-5 w-5 shrink-0" /><span>{item.label}</span>
              </Link>;
            })}
          </nav>
          <div className="mt-4 space-y-3 border-t pt-4 [overflow-wrap:anywhere]">
            <p className="text-sm">{user.full_name}</p>
            <Button variant="outline" className="min-h-11 w-full text-rose-600"
              onClick={() => void logout()}><LogOut className="h-4 w-4" />Đăng xuất</Button>
          </div>
        </Modal>

        <main className="min-w-0 flex-1 p-4 pb-[calc(6rem+env(safe-area-inset-bottom))] md:p-6">
          <UnfinishedWork />
          {sessionNotice && <p role="status" className="mb-3 rounded-lg border p-3 text-sm">{sessionNotice}</p>}
          {branchError && <p role="alert" className="mb-3 text-rose-700">{branchError}</p>}
          <div key={tenant.id} ref={(element) => { element?.toggleAttribute("inert", branchBusy); }}>
            <ProductGuide key={user.id} role={user.role === "ADMIN" ? "ADMIN" : "STAFF"} identity={user.id} identities={branches.map((branch) => branch.user.id)} autoOpen={pathname !== "/admin/help"} />
            <ScreenHelp role={user.role === "ADMIN" ? "ADMIN" : "STAFF"} identity={user.id} />
            {targetBranch && targetBranch !== tenant.id ? (
              <section className="space-y-3 rounded-xl border p-4" aria-label="Chi nhánh của lịch hẹn">
                <p role="status">{linkedBranch ? "Lịch hẹn thuộc chi nhánh " + linkedBranch.tenant.name + ". Mở chi nhánh này để xem lịch." : "Bạn không còn được cấp chi nhánh của lịch hẹn này. Liên hệ chủ spa để kiểm tra."}</p>
                {linkedBranch && <Button disabled={branchBusy} onClick={() => void chooseBranch(linkedBranch.tenant.id)}>Mở lịch tại {linkedBranch.tenant.name}</Button>}
              </section>
            ) : (
              <>{user.role === "STAFF" && <StaffWorkplace staffId={user.id} branchId={tenant.id} />}{children}</>
            )}
          </div>
        </main>
      </div>
      <nav aria-label="Điều hướng chính" className="neu-nav fixed inset-x-0 bottom-0 z-30 flex border-t border-border neu-surface bg-card/95 pt-1 pb-[max(0.375rem,env(safe-area-inset-bottom))] backdrop-blur md:hidden">
        {primaryItems.map((item) => {
          const Icon = item.icon;
          const label = item.href === "/admin/customers" ? "Khách" : item.href === "/admin/dashboard" ? "Tổng quan" : item.label;
          return <Link key={item.href} href={item.href} aria-current={isActive(item.href, item.match) ? "page" : undefined}
            className={cn("flex min-h-12 min-w-0 flex-1 flex-col items-center justify-center gap-1 px-1 text-xs",
              isActive(item.href, item.match) ? "font-semibold text-primary" : "text-muted-foreground")}>
            <Icon className="h-5 w-5 shrink-0" /><span>{label}</span>
          </Link>;
        })}
        <button type="button" ref={moreButton} aria-current={moreActive ? "page" : undefined} aria-haspopup="dialog" aria-expanded={mobileMenuOpen}
          onClick={() => setMobileMenuOpen(true)}
          className={cn("flex min-h-12 min-w-0 flex-1 flex-col items-center justify-center gap-1 px-1 text-xs",
            moreActive ? "font-semibold text-primary" : "text-muted-foreground")}>
          <MoreHorizontal className="h-5 w-5" /><span>Thêm</span>
        </button>
      </nav>
    </div>
  );
}
