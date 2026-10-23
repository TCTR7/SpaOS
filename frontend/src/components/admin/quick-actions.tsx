import * as React from "react";
import Link from "next/link";
import { CalendarDays, Sparkles, UserCheck, Users, Wallet } from "lucide-react";

const ACTIONS: { href: string; label: string; hint: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { href: "/admin/bookings", label: "Lịch hẹn", hint: "Xem và tạo lịch", icon: CalendarDays },
  { href: "/admin/customers", label: "Khách hàng", hint: "Hồ sơ & liệu trình", icon: Users },
  { href: "/admin/payments", label: "Thu tiền", hint: "Khoản còn thiếu", icon: Wallet },
  { href: "/admin/services", label: "Danh mục dịch vụ", hint: "Dịch vụ & gói liệu trình", icon: Sparkles },
  { href: "/admin/staff", label: "Nhân sự & Ca làm việc", hint: "Hồ sơ, kỹ năng, ca làm", icon: UserCheck },
];

/** Lối tắt tới các mục chính; các mục này cũng quan trọng như lịch hẹn nên không nằm trong menu "Thêm". */
export function QuickActions(): React.ReactElement {
  return (
    <nav aria-label="Truy cập nhanh" data-testid="dashboard-quick-actions" className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {ACTIONS.map(({ href, label, hint, icon: Icon }) => (
        <Link key={href} href={href}
          className="flex min-h-24 min-w-0 flex-col items-start gap-1 rounded-xl border border-border bg-card p-3 transition-colors hover:border-primary/40 hover:bg-accent">
          <Icon className="h-5 w-5 text-primary" aria-hidden="true" />
          <span className="text-sm font-semibold leading-snug [overflow-wrap:anywhere]">{label}</span>
          <span className="text-xs text-muted-foreground [overflow-wrap:anywhere]">{hint}</span>
        </Link>
      ))}
    </nav>
  );
}
