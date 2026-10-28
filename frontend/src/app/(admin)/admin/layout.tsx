import { AdminAuthProvider } from "@/components/admin/auth-context";
import { AdminShell } from "@/components/admin/admin-shell";
import { headers } from "next/headers";
export function generateMetadata():{manifest:string} {
  const slug=headers().get("x-spa-slug");
  return {manifest:slug?`/s/${slug}/manifest.webmanifest`:"/admin/app.webmanifest"};
}

export default function AdminGroupLayout({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  return (
    <AdminAuthProvider>
      <AdminShell>{children}</AdminShell>
    </AdminAuthProvider>
  );
}
