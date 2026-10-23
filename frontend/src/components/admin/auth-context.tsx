"use client";

import * as React from "react";
import { usePathname, useRouter } from "next/navigation";
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
  unsubscribeWebPush,
} from "@/lib/api";
import { withBranchChange, useBranchGuard } from "@/lib/branch-guard";
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
  const [recoveryPending, setRecoveryPending] = React.useState(false);
  React.useEffect(() => {
    const check = (): void => {
      const key = tenant && user ? "spaos_manual_batch_" + tenant.id + "_" + user.id : "";
      setRecoveryPending(!!key && !!sessionStorage.getItem(key));
    };
    check();
    window.addEventListener("spaos:manual-batch-changed", check);
    return () => window.removeEventListener("spaos:manual-batch-changed", check);
  }, [tenant?.id, user?.id]);
  useBranchGuard(false, recoveryPending);

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
      setUser(me.user); setTenant(me.tenant); setBranches(verifiedBranches);
    } catch (error) {
      if (!current()) return;
      if (error instanceof ApiError && error.status === 401) {
        clearAuthSession();
        if (!isPublicAuthRoute) router.replace("/admin/login");
      } else {
        setAuthError("Chưa tải được tài khoản và chi nhánh. Vui lòng thử lại.");
      }
    } finally {
      if (current()) setLoading(false);
    }
  }, [isPublicAuthRoute, router]);

  // Refresh saved branding without unmounting the settings form or losing feedback.
  const reloadTenant = React.useCallback(async (): Promise<void> => {
    const request = ++operation.current;
    const session = getAdminSessionIdentity();
    const [me, verifiedBranches] = await Promise.all([fetchMe(), fetchBranches()]);
    if (operation.current !== request || session !== getAdminSessionIdentity()) return;
    if (me.user.id !== user?.id || me.tenant.id !== tenant?.id) return;
    setUser(me.user); setTenant(me.tenant); setBranches(verifiedBranches);
  }, [user?.id, tenant?.id]);

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
    window.location.assign(result.user.role === "ADMIN" ? "/admin/dashboard" : "/admin/bookings");
  }, discard);
  React.useEffect(() => {
    const changed = (event: StorageEvent): void => {
      if (event.key === "spaos_admin_token" || event.key === ADMIN_SESSION_VERSION_KEY || event.key === null) {
        invalidateAdminSessionRequests();
        operation.current += 1;
        setUser(null); setTenant(null); setBranches([]); setLoading(true);
        window.location.replace("/admin");
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
