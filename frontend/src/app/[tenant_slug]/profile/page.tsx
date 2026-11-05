"use client";

import * as React from "react";
import { ProfileEditor } from "@/components/customer/profile-editor";
import { customerAuthHref } from "@/lib/customer-return-to";
import Link from "@/components/spa-link";
import { LogOut, Phone, User as UserIcon } from "lucide-react";
import { useCustomerTenant } from "@/components/customer/customer-context";
import { Button } from "@/components/ui/button";
import { Badge, Card, CardContent } from "@/components/ui/card";

export default function CustomerProfilePage(): React.ReactElement | null {
  const { slug, tenant, user, authLoading, logoutCustomer } = useCustomerTenant();

  if (!tenant) return null;
  const themeColor = "var(--brand-color)";

  if (!user && !authLoading) {
    return (
      <Card>
        <CardContent className="space-y-3 p-6 text-center">
          <UserIcon className="mx-auto h-10 w-10" style={{ color: "var(--brand-text)" }} />
          <h2 className="text-base font-bold text-foreground">Tài khoản khách hàng</h2>
          <p className="text-xs text-muted-foreground">
            Bạn không cần đăng nhập để đặt lịch. Đăng nhập chỉ giúp xem lại lịch hẹn của mình.
          </p>
          <div className="flex justify-center gap-2">
            <Link
              href={customerAuthHref(slug, "login", `/${slug}/profile`)}
              className="inline-flex min-h-11 items-center justify-center rounded-xl px-5 text-xs font-bold text-white shadow"
              style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
            >
              Đăng nhập
            </Link>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!user) return null;

  return (
    <div className="min-w-0 space-y-4 [overflow-wrap:anywhere]">
      <Card>
        <CardContent className="flex min-w-0 flex-wrap items-center justify-between gap-3 p-4">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <div
              className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-base font-bold text-white shadow-sm"
              style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
            >
              {user.full_name.slice(0, 1).toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="flex items-center gap-1.5 text-sm font-bold text-foreground">
                <UserIcon className="h-3.5 w-3.5 text-muted-foreground" />
                {user.full_name}
              </p>
              <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Phone className="h-3.5 w-3.5" />
                {user.phone_number}
              </p>
              <Badge variant="secondary" className="mt-1 max-w-full whitespace-normal">
                Thành viên {tenant.name}
              </Badge>
            </div>
          </div>
          <Button variant="outline" size="sm" className="text-rose-600" onClick={() => void logoutCustomer()}>
            <LogOut className="h-4 w-4" />
            Thoát
          </Button>
        </CardContent>
      </Card>
      <ProfileEditor key={user.id} />
    </div>
  );
}
