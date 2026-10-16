"use client";

import * as React from "react";
import {
  clearCustomerToken,
  fetchCustomerMe,
  fetchPublicTenant,
  getCustomerToken,
  unsubscribeCustomerWebPush,
} from "@/lib/customer-api";
import type { AuthUser, PublicTenantResponse } from "@/lib/types";

interface CustomerTenantContextValue {
  slug: string;
  tenant: PublicTenantResponse | null;
  tenantLoading: boolean;
  tenantNotFound: boolean;
  user: AuthUser | null;
  authLoading: boolean;
  refreshCustomer: () => Promise<void>;
  logoutCustomer: () => Promise<void>;
}

const CustomerTenantContext = React.createContext<CustomerTenantContextValue>({
  slug: "",
  tenant: null,
  tenantLoading: true,
  tenantNotFound: false,
  user: null,
  authLoading: true,
  refreshCustomer: async () => {},
  logoutCustomer: async () => {},
});

export function CustomerTenantProvider({
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

  React.useEffect(() => {
    let cancelled = false;
    setTenantLoading(true);
    setTenantNotFound(false);
    void (async () => {
      try {
        const data = await fetchPublicTenant(normalizedSlug);
        if (!cancelled) {
          setTenant(data);
        }
      } catch {
        if (!cancelled) {
          setTenant(null);
          setTenantNotFound(true);
        }
      } finally {
        if (!cancelled) {
          setTenantLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [normalizedSlug]);

  const refreshCustomer = React.useCallback(async (): Promise<void> => {
    const token = getCustomerToken(normalizedSlug);
    if (!token) {
      setUser(null);
      setAuthLoading(false);
      return;
    }
    try {
      const me = await fetchCustomerMe(normalizedSlug);
      setUser(me.user);
    } catch {
      clearCustomerToken(normalizedSlug);
      setUser(null);
    } finally {
      setAuthLoading(false);
    }
  }, [normalizedSlug]);

  React.useEffect(() => {
    void refreshCustomer();
  }, [refreshCustomer]);

  const logoutCustomer = React.useCallback(async (): Promise<void> => {
    try {
      if (typeof window !== "undefined" && "serviceWorker" in navigator) {
        const reg = await navigator.serviceWorker.getRegistration();
        const sub = await reg?.pushManager.getSubscription();
        if (sub) {
          await unsubscribeCustomerWebPush(normalizedSlug, sub.endpoint).catch(
            () => {}
          );
          await sub.unsubscribe().catch(() => {});
        }
      }
    } catch {
      // ignore push cleanup errors
    } finally {
      clearCustomerToken(normalizedSlug);
      setUser(null);
    }
  }, [normalizedSlug]);

  return (
    <CustomerTenantContext.Provider
      value={{
        slug: normalizedSlug,
        tenant,
        tenantLoading,
        tenantNotFound,
        user,
        authLoading,
        refreshCustomer,
        logoutCustomer,
      }}
    >
      {children}
    </CustomerTenantContext.Provider>
  );
}

export function useCustomerTenant(): CustomerTenantContextValue {
  return React.useContext(CustomerTenantContext);
}
