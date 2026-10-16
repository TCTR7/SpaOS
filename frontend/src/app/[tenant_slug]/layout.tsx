import { CustomerTenantProvider } from "@/components/customer/customer-context";
import { CustomerShell } from "@/components/customer/customer-shell";

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
