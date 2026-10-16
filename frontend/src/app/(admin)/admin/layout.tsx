import { AdminAuthProvider } from "@/components/admin/auth-context";
import { AdminShell } from "@/components/admin/admin-shell";

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
