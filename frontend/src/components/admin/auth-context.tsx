"use client";

import * as React from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  clearAuthSession,
  fetchMe,
  fetchBranches,
  switchBranch,
  saveAuthSession,
  getStoredToken,
  unsubscribeWebPush,
} from "@/lib/api";
import type { AuthUser, TenantInfo, BranchAccess } from "@/lib/types";

interface AdminAuthContextValue {
  user: AuthUser | null;
  tenant: TenantInfo | null;
  loading: boolean;
  branches: BranchAccess[];
  changeBranch: (id: string) => Promise<void>;
  refreshMe: () => Promise<void>;
  logout: () => Promise<void>;
}

const AdminAuthContext = React.createContext<AdminAuthContextValue>({
  user: null,
  tenant: null,
  loading: true,
  branches: [],
  changeBranch: async () => {},
  refreshMe: async () => {},
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

  const isPublicAuthRoute =
    pathname?.startsWith("/admin/login") ||
    pathname?.startsWith("/admin/register-tenant");

  const refreshMe = React.useCallback(async (): Promise<void> => {
    const token = getStoredToken();
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
      if (me.user.role !== "ADMIN" && me.user.role !== "STAFF") {
        clearAuthSession();
        setUser(null);
        setTenant(null);
        if (!isPublicAuthRoute) {
          router.replace("/admin/login");
        }
        return;
      }
      setUser(me.user);
      setTenant(me.tenant);
      saveAuthSession(token, me.tenant.slug);
      setBranches(await fetchBranches().catch(() => []));
    } catch {
      clearAuthSession();
      setUser(null);
      setTenant(null);
      if (!isPublicAuthRoute) {
        router.replace("/admin/login");
      }
    } finally {
      setLoading(false);
    }
  }, [isPublicAuthRoute, router]);

  React.useEffect(() => {
    void refreshMe();
  }, [refreshMe]);

  const logout = React.useCallback(async (): Promise<void> => {
    try {
      if (typeof window !== "undefined" && "serviceWorker" in navigator) {
        const reg = await navigator.serviceWorker.getRegistration();
        const sub = await reg?.pushManager.getSubscription();
        if (sub) {
          await unsubscribeWebPush(sub.endpoint).catch(() => {});
          await sub.unsubscribe().catch(() => {});
        }
      }
    } catch {
      // ignore push cleanup errors
    } finally {
      clearAuthSession();
      setUser(null);
      setTenant(null);
      router.replace("/admin/login");
    }
  }, [router]);

  const changeBranch = async (id: string): Promise<void> => {
    const result = await switchBranch(id);
    if ("serviceWorker" in navigator) {
      const sub = await (await navigator.serviceWorker.getRegistration())?.pushManager.getSubscription();
      if (sub) { await unsubscribeWebPush(sub.endpoint); await sub.unsubscribe(); }
    }
    const target = branches.find((branch) => branch.tenant.id === id);
    saveAuthSession(result.access_token, target?.tenant.slug || "");
    window.location.assign(result.user.role === "ADMIN" ? "/admin/dashboard" : "/admin/bookings");
  };
  React.useEffect(() => {
    const changed = (event: StorageEvent): void => {
      if (event.key === "spaos_admin_token") window.location.replace("/admin");
    };
    window.addEventListener("storage", changed);
    return () => window.removeEventListener("storage", changed);
  }, []);

  return (
    <AdminAuthContext.Provider
      value={{ user, tenant, loading, branches, changeBranch, refreshMe, logout }}
    >
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth(): AdminAuthContextValue {
  return React.useContext(AdminAuthContext);
}
