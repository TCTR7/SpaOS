import type { Metadata, Viewport } from "next";
import { CustomerTenantProvider } from "@/components/customer/customer-context";
import { CustomerShell } from "@/components/customer/customer-shell";
import type { PublicTenantResponse } from "@/lib/types";

const BACKEND_INTERNAL_URL =
  process.env.BACKEND_INTERNAL_URL || "http://localhost:8001";

async function getTenantBranding(
  slug: string
): Promise<PublicTenantResponse | null> {
  try {
    const res = await fetch(
      `${BACKEND_INTERNAL_URL}/api/v1/public/tenants/${encodeURIComponent(
        slug.trim().toLowerCase()
      )}`,
      { cache: "no-store" }
    );
    if (!res.ok) return null;
    return (await res.json()) as PublicTenantResponse;
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: { tenant_slug: string };
}): Promise<Metadata> {
  const tenant = await getTenantBranding(params.tenant_slug);
  const title = tenant
    ? `${tenant.name} — Đặt lịch Online | SpaOS`
    : "SpaOS - Đặt lịch & Quản lý Spa";
  const shortTitle = tenant ? tenant.name : "SpaOS";

  return {
    title,
    manifest: "/manifest.json",
    appleWebApp: {
      capable: true,
      statusBarStyle: "default",
      title: shortTitle,
    },
  };
}

export async function generateViewport({
  params,
}: {
  params: { tenant_slug: string };
}): Promise<Viewport> {
  const tenant = await getTenantBranding(params.tenant_slug);
  return {
    themeColor: tenant?.theme_color || "#e11d48",
  };
}

export default function TenantSlugLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { tenant_slug: string };
}): React.ReactElement {
  return (
    <CustomerTenantProvider slug={params.tenant_slug}>
      <CustomerShell>{children}</CustomerShell>
    </CustomerTenantProvider>
  );
}
