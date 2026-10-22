import { AdminAuthProvider } from "@/components/admin/auth-context";
import { AdminShell } from "@/components/admin/admin-shell";
export const metadata={manifest:"/admin/app.webmanifest",appleWebApp:{capable:true,title:"Quản lý Spa"}};

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
