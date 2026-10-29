"use client";

import * as React from "react";
import {
  clearCustomerToken,
  fetchCustomerMe,
  fetchPublicTenant,
  getCustomerToken,
  unsubscribeCustomerWebPush,
  getCustomerSessionIdentity,
  invalidateCustomerSessionRequests,
  customerSessionVersionKey,
  CUSTOMER_SESSION_CHANGED,
} from "@/lib/customer-api";
import { ApiError } from "@/lib/api";
import { spaSlug } from "@/lib/spa-path";
import type { AuthUser, PublicTenantResponse } from "@/lib/types";

interface CustomerTenantContextValue {
  slug: string;
  tenant: PublicTenantResponse | null;
  tenantLoading: boolean;
  tenantNotFound: boolean;
  tenantError: string | null;
  refreshTenant: () => Promise<void>;
  user: AuthUser | null;
  authLoading: boolean;
  authError: string | null;
  refreshCustomer: () => Promise<void>;
  reloadCustomerProfile: () => Promise<void>;
  logoutCustomer: () => Promise<void>;
}

const CustomerTenantContext = React.createContext<CustomerTenantContextValue>({
  slug: "",
  tenant: null,
  tenantLoading: true,
  tenantNotFound: false,
  tenantError: null,
  refreshTenant: async () => {},
  user: null,
  authLoading: true,
  authError: null,
  refreshCustomer: async () => {},
  reloadCustomerProfile: async () => {},
  logoutCustomer: async () => {},
});

function ScopedCustomerTenantProvider({
  slug,
  children,
}: {
  slug: string;
  children: React.ReactNode;
}): React.ReactElement {
  const normalizedSlug = slug.trim().toLowerCase();
  const [tenant, setTenant] = React.useState<PublicTenantResponse | null>(null);
  const [tenantLoading, setTenantLoading] = React.useState<boolean>(true);
  const [tenantNotFound, setTenantNotFound] = React.useState<boolean>(false);
  const [user, setUser] = React.useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = React.useState<boolean>(true);
  const [authError, setAuthError] = React.useState<string | null>(null);
  const [tenantError, setTenantError] = React.useState<string | null>(null);
  const authRequest = React.useRef(0);
  const tenantRequest = React.useRef(0);
  const verifiedIdentity = React.useRef<string | null>(null);
  const [authGeneration, setAuthGeneration] = React.useState(0);

  const refreshTenant = React.useCallback(async (): Promise<void> => {
    const request = ++tenantRequest.current;
    setTenantLoading(true);
    setTenantNotFound(false); setTenant(null); setTenantError(null);
    try {
      const data = await fetchPublicTenant(normalizedSlug);
      const brand = spaSlug(window.location.pathname);
      if(brand&&data.spa_slug!==brand)throw new ApiError(404,"La chi nhánh của spa khác");
      if (request === tenantRequest.current) setTenant(data);
    } catch (error) {
      if (request === tenantRequest.current) {
        if (error instanceof ApiError && error.status === 404) setTenantNotFound(true);
        else setTenantError("Không tải được thông tin Spa. Kiểm tra kết nối và thử lại.");
      }
    } finally {
      if (request === tenantRequest.current) setTenantLoading(false);
    }
  }, [normalizedSlug]);

  React.useEffect(() => {
    void refreshTenant();
    return () => { tenantRequest.current += 1; };
  }, [refreshTenant]);

  const refreshCustomer = React.useCallback(async (): Promise<void> => {
    // Remove private drafts and portaled dialogs from the previous verified
    // identity. Anonymous inline login retains its booking choices.
    if (verifiedIdentity.current) {
      verifiedIdentity.current = null;
      setAuthGeneration((previous) => previous + 1);
    }
    const request = ++authRequest.current;
    const session = getCustomerSessionIdentity(normalizedSlug);
    const current = (): boolean => request === authRequest.current && session === getCustomerSessionIdentity(normalizedSlug);
    setUser(null); setAuthError(null); setAuthLoading(true);
    const token = getCustomerToken(normalizedSlug);
    if (!token) {
      setUser(null);
      setAuthLoading(false);
      return;
    }
    try {
      const me = await fetchCustomerMe(normalizedSlug);
      if (!current()) return;
      if (me.user.role !== "CUSTOMER" || me.tenant.slug !== normalizedSlug || me.user.tenant_id !== me.tenant.id) {
        clearCustomerToken(normalizedSlug);
        return;
      }
      setUser(me.user);
      verifiedIdentity.current = session;
    } catch (error) {
      if (!current()) return;
      if (error instanceof ApiError && error.status === 401) clearCustomerToken(normalizedSlug);
      else setAuthError("Chưa tải được tài khoản. Kiểm tra kết nối và thử lại.");
    } finally {
      if (current()) setAuthLoading(false);
    }
  }, [normalizedSlug]);

  React.useEffect(() => {
    void refreshCustomer();
    const changed = (event: StorageEvent): void => {
      if (event.key === null || event.key === `spaos_customer_token_${normalizedSlug}` || event.key === customerSessionVersionKey(normalizedSlug)) {
        invalidateCustomerSessionRequests(normalizedSlug);
        void refreshCustomer();
      }
    };
    const invalidated = (event: Event): void => {
      if ((event as CustomEvent<string>).detail === normalizedSlug) void refreshCustomer();
    };
    window.addEventListener("storage", changed);
    window.addEventListener(CUSTOMER_SESSION_CHANGED, invalidated);
    return () => {
      authRequest.current += 1;
      window.removeEventListener("storage", changed);
      window.removeEventListener(CUSTOMER_SESSION_CHANGED, invalidated);
    };
  }, [normalizedSlug, refreshCustomer]);

  // A profile-only reload preserves form feedback. Session changes still use
  // refreshCustomer and discard all private drafts through authGeneration.
  const reloadCustomerProfile = React.useCallback(async (): Promise<void> => {
    const session = getCustomerSessionIdentity(normalizedSlug);
    const request = authRequest.current;
    if (!verifiedIdentity.current || verifiedIdentity.current !== session) return;
    const me = await fetchCustomerMe(normalizedSlug);
    if (request !== authRequest.current || session !== getCustomerSessionIdentity(normalizedSlug) || verifiedIdentity.current !== session) return;
    if (me.user.role !== "CUSTOMER" || me.tenant.slug !== normalizedSlug || me.user.tenant_id !== me.tenant.id || me.user.id !== user?.id) {
      clearCustomerToken(normalizedSlug);
      return;
    }
    setUser(me.user);
  }, [normalizedSlug, user?.id]);

  const logoutCustomer = React.useCallback(async (): Promise<void> => {
    const token = getCustomerToken(normalizedSlug);
    authRequest.current += 1;
    clearCustomerToken(normalizedSlug);
    const loggedOutSession = getCustomerSessionIdentity(normalizedSlug);
    setUser(null); setAuthLoading(false); setAuthError(null);
    try {
      if (typeof window !== "undefined" && "serviceWorker" in navigator) {
        const reg = await navigator.serviceWorker.getRegistration();
        const sub = await reg?.pushManager.getSubscription();
        if (sub && token && loggedOutSession === getCustomerSessionIdentity(normalizedSlug)) {
          await unsubscribeCustomerWebPush(normalizedSlug, sub.endpoint, token).catch(
            () => {}
          );
          if (loggedOutSession === getCustomerSessionIdentity(normalizedSlug)) await sub.unsubscribe().catch(() => {});
        }
      }
    } catch {
      // ignore push cleanup errors
    }
  }, [normalizedSlug]);

  return (
    <CustomerTenantContext.Provider
      value={{
        slug: normalizedSlug,
        tenant,
        tenantLoading,
        tenantNotFound,
        tenantError, refreshTenant,
        user,
        authLoading,
        authError,
        refreshCustomer,
        reloadCustomerProfile,
        logoutCustomer,
      }}
    >
      <React.Fragment key={authGeneration}>{children}</React.Fragment>
    </CustomerTenantContext.Provider>
  );
}

// A new branch gets fresh state before its first render; pending requests from
// the unmounted branch are invalidated by the effects above.
export function CustomerTenantProvider({ slug, children }: { slug: string; children: React.ReactNode }): React.ReactElement {
  const normalizedSlug = slug.trim().toLowerCase();
  return <ScopedCustomerTenantProvider key={normalizedSlug} slug={normalizedSlug}>{children}</ScopedCustomerTenantProvider>;
}

export function useCustomerTenant(): CustomerTenantContextValue {
  return React.useContext(CustomerTenantContext);
}
