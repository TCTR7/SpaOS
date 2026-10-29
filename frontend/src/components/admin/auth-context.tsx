"use client";

import * as React from "react";
import { usePathname, useRouter } from "@/lib/spa-navigation";
import {
  clearAuthSession,
  fetchMe,
  fetchBranches,
  switchBranch,
  saveAuthSession,
  saveVerifiedAdminSlug,
  getAdminSessionIdentity,
  invalidateAdminSessionRequests,
  ADMIN_SESSION_CHANGED,
  ADMIN_SESSION_VERSION_KEY,
  ApiError,
  getStoredToken,
  resolveAdminSession,
  unsubscribeWebPush,
} from "@/lib/api";
import { currentAdminBookingTarget, rememberAdminBookingTarget } from "@/lib/admin-booking-target";
import { withBranchChange } from "@/lib/branch-guard";
import { spaPath, spaSlug, adminStorageKey } from "@/lib/spa-path";
import type { AuthUser, TenantInfo, BranchAccess, TokenResponse } from "@/lib/types";

interface AdminAuthContextValue {
  user: AuthUser | null;
  tenant: TenantInfo | null;
  loading: boolean;
  authError: string | null;
  branches: BranchAccess[];
  changeBranch: (id: string, discard?: boolean) => Promise<void>;
  refreshMe: () => Promise<void>;
  reloadTenant: () => Promise<void>;
  logout: () => Promise<void>;
}

const AdminAuthContext = React.createContext<AdminAuthContextValue>({
  user: null,
  tenant: null,
  loading: true,
  authError: null,
  branches: [],
  changeBranch: async () => {},
  refreshMe: async () => {},
  reloadTenant: async () => {},
  logout: async () => {},
});

export function AdminAuthProvider({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = React.useState<AuthUser | null>(null);
  const [tenant, setTenant] = React.useState<TenantInfo | null>(null);
  const [branches, setBranches] = React.useState<BranchAccess[]>([]);
  const [loading, setLoading] = React.useState<boolean>(true);
  const [authError, setAuthError] = React.useState<string | null>(null);
  const operation = React.useRef(0);
  const detailsRevision = React.useRef(0);
  const isPublicAuthRoute =
    pathname?.startsWith("/admin/login") ||
    pathname === "/admin/recover" ||
    pathname?.startsWith("/admin/register-tenant");

  const refreshMe = React.useCallback(async (): Promise<void> => {
    const request = ++operation.current;
    const session = getAdminSessionIdentity();
    const current = (): boolean => operation.current === request && session === getAdminSessionIdentity();
    const token = getStoredToken();
    setUser(null); setTenant(null); setBranches([]); setAuthError(null); setLoading(true);
    if (!token) {
      rememberAdminBookingTarget();
      setUser(null);
      setTenant(null);
      setLoading(false);
      if (!isPublicAuthRoute) {
        router.replace("/admin/login");
      }
      return;
    }

    try {
      const me = await fetchMe();
      if (!current()) return;
      const expectedSpa = spaSlug(window.location.pathname);
      if (expectedSpa && me.spa?.slug !== expectedSpa) throw new ApiError(401, "Tài khoản không thuộc spa này");
      if (me.user.role !== "ADMIN" && me.user.role !== "STAFF") {
        clearAuthSession();
        setUser(null);
        setTenant(null);
        if (!isPublicAuthRoute) {
          router.replace("/admin/login");
        }
        return;
      }
      const verifiedBranches = await fetchBranches();
      if (!current()) return;
      saveVerifiedAdminSlug(me.tenant.slug);
      setUser(me.user); setTenant({...me.tenant, theme_color:me.spa?.theme_color || me.tenant.theme_color, logo_url:me.spa?.logo_url || me.tenant.logo_url}); setBranches(verifiedBranches);
    } catch (error) {
      if (!current()) return;
      if (error instanceof ApiError && error.status === 401) {
        try {
          if (await resolveAdminSession()) return;
          if (!current()) return;
          clearAuthSession();
          if (!isPublicAuthRoute) router.replace("/admin/login");
        } catch {
          if (current()) setAuthError("Chưa xác minh được quyền chi nhánh. Vui lòng thử lại khi có mạng.");
        }
      } else {
        setAuthError("Chưa tải được tài khoản và chi nhánh. Vui lòng thử lại.");
      }
    } finally {
      if (current()) setLoading(false);
    }
  }, [isPublicAuthRoute, router]);

  // Refresh saved branding without unmounting the settings form or losing feedback.
  const reloadTenant = React.useCallback(async (): Promise<void> => {
    const request = operation.current;
    const details = ++detailsRevision.current;
    const session = getAdminSessionIdentity();
    const [me, verifiedBranches] = await Promise.all([fetchMe(), fetchBranches()]);
    if (operation.current !== request || details !== detailsRevision.current || session !== getAdminSessionIdentity()) return;
    if (me.user.id !== user?.id || me.tenant.id !== tenant?.id) return;
    // A routine focus check must not reload booking reference data or disturb drafts.
    const nextTenant={...me.tenant,theme_color:me.spa?.theme_color||me.tenant.theme_color,logo_url:me.spa?.logo_url||me.tenant.logo_url};
    setUser(previous=>JSON.stringify(previous)===JSON.stringify(me.user)?previous:me.user);
    setTenant(previous=>JSON.stringify(previous)===JSON.stringify(nextTenant)?previous:nextTenant);
    setBranches(previous=>JSON.stringify(previous)===JSON.stringify(verifiedBranches)?previous:verifiedBranches);
  }, [user?.id, tenant?.id]);

  React.useEffect(() => {
    if (!user || isPublicAuthRoute) return;
    let pending = false;
    const check = async (): Promise<void> => {
      if (pending || document.visibilityState !== "visible") return;
      pending = true;
      try { await reloadTenant(); }
      catch (error) { if (error instanceof ApiError && error.status === 401) void refreshMe(); }
      finally { pending = false; }
    };
    const timer = window.setInterval(() => { void check(); }, 30000);
    const visible = (): void => { void check(); };
    window.addEventListener("focus", visible);
    document.addEventListener("visibilitychange", visible);
    return () => { window.clearInterval(timer); window.removeEventListener("focus", visible); document.removeEventListener("visibilitychange", visible); };
  }, [user?.id, isPublicAuthRoute, reloadTenant, refreshMe]);

  React.useEffect(() => {
    void refreshMe();
    return () => { operation.current += 1; };
  }, [refreshMe]);

  const logout = React.useCallback(async (): Promise<void> => {
    const token = getStoredToken();
    operation.current += 1;
    clearAuthSession();
    const loggedOutSession = getAdminSessionIdentity();
    setUser(null); setTenant(null); setBranches([]); setAuthError(null); setLoading(false);
    router.replace("/admin/login");
    try {
      if (typeof window !== "undefined" && "serviceWorker" in navigator) {
        const reg = await navigator.serviceWorker.getRegistration();
        const sub = await reg?.pushManager.getSubscription();
        if (sub && token && loggedOutSession === getAdminSessionIdentity()) {
          await unsubscribeWebPush(sub.endpoint, token).catch(() => {});
          if (loggedOutSession === getAdminSessionIdentity()) await sub.unsubscribe().catch(() => {});
        }
      }
    } catch {
      // ignore push cleanup errors
    }
  }, [router]);

  const changeBranch = async (id: string, discard = false): Promise<void> => withBranchChange(async () => {
    const session = getAdminSessionIdentity();
    const token = getStoredToken();
    const request = ++operation.current;
    const current = (): boolean => operation.current === request && session === getAdminSessionIdentity();
    const target = branches.find((branch) => branch.tenant.id === id);
    if (!token || !user || !target) throw new Error("Chưa thể chuyển chi nhánh. Vui lòng thử lại.");
    let result: TokenResponse;
    try {
      result = await switchBranch(id);
    } catch (error) {
      if (current()) throw error;
      return;
    }
    if (!current()) return;
    if ("serviceWorker" in navigator) {
      try {
        const sub = await (await navigator.serviceWorker.getRegistration())?.pushManager.getSubscription();
        if (!current()) return;
        if (sub) {
          await unsubscribeWebPush(sub.endpoint, token).catch(() => {});
          if (!current()) return;
          await sub.unsubscribe().catch(() => {});
        }
      } catch { /* Push cleanup must not prevent a verified branch switch. */ }
    }
    if (!current()) return;
    setUser(null); setTenant(null); setBranches([]); setLoading(true);
    saveAuthSession(result.access_token, target.tenant.slug);
    const bookingTarget=currentAdminBookingTarget();
    const destination=bookingTarget&&new URLSearchParams(window.location.search).get("target_branch")===id?bookingTarget:(result.user.role === "ADMIN" ? "/admin/dashboard" : "/admin/bookings");
    window.location.assign(spaPath(destination));
  }, discard);
  React.useEffect(() => {
    const changed = (event: StorageEvent): void => {
      if (event.key === adminStorageKey("spaos_admin_token") || event.key === adminStorageKey(ADMIN_SESSION_VERSION_KEY) || event.key === null) {
        invalidateAdminSessionRequests();
        operation.current += 1;
        setUser(null); setTenant(null); setBranches([]); setLoading(true);
        window.location.replace(spaPath("/admin"));
      }
    };
    const invalidated = (): void => { void refreshMe(); };
    window.addEventListener("storage", changed);
    window.addEventListener(ADMIN_SESSION_CHANGED, invalidated);
    return () => {
      window.removeEventListener("storage", changed);
      window.removeEventListener(ADMIN_SESSION_CHANGED, invalidated);
    };
  }, [refreshMe]);

  return (
    <AdminAuthContext.Provider
      value={{ user, tenant, loading, authError, branches, changeBranch, refreshMe, reloadTenant, logout }}
    >
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth(): AdminAuthContextValue {
  return React.useContext(AdminAuthContext);
}
