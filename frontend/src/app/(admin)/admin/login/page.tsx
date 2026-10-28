"use client";

import * as React from "react";
import Link from "@/components/spa-link";
import { PasswordInput } from "@/components/ui/password-input";
import { useRouter } from "@/lib/spa-navigation";
import { Sparkles, Lock, Phone } from "lucide-react";
import { loginAdmin, saveAuthSession } from "@/lib/api";
import { takeAdminBookingTarget } from "@/lib/admin-booking-target";
import { spaSlug } from "@/lib/spa-path";
import { useBranding } from "@/components/brand-provider";
import { useAdminAuth } from "@/components/admin/auth-context";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function AdminLoginPage(): React.ReactElement {
  const router = useRouter();
  const {branding}=useBranding();
  const { refreshMe } = useAdminAuth();

  const [phoneNumber, setPhoneNumber] = React.useState<string>("");
  const [password, setPassword] = React.useState<string>("");
  const [hydrated, setHydrated] = React.useState(false);
  const [submitting, setSubmitting] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setHydrated(true);
  }, []);

  const handleSubmit = async (
    e: React.FormEvent<HTMLFormElement>
  ): Promise<void> => {
    e.preventDefault();
    if (submitting) return;
    setError(null);
    setSubmitting(true);
    try {
      const res = await loginAdmin(phoneNumber, password);
      if (res.user.role !== "ADMIN" && res.user.role !== "STAFF") {
        setError("Tài khoản này không có quyền truy cập trang Quản trị Spa.");
        return;
      }
      const currentSpa = spaSlug(window.location.pathname);
      if (currentSpa && currentSpa !== res.spa_slug) throw new Error("Tài khoản không thuộc spa này. Mở đúng ứng dụng được bàn giao.");
      const destination=(res.spa_slug?takeAdminBookingTarget(res.spa_slug):null)||(res.user.role === "ADMIN"?"/admin/dashboard":"/admin/bookings");
      if (!currentSpa && res.spa_slug) {
        window.localStorage.setItem("spaos_admin_token:"+res.spa_slug, res.access_token);
        window.localStorage.setItem("spaos_admin_session_version:"+res.spa_slug, crypto.randomUUID());
        window.location.assign(`/s/${res.spa_slug}${destination}`);
        return;
      }
      saveAuthSession(res.access_token, "");
      await refreshMe();
      router.push(destination);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Đăng nhập thất bại, vui lòng kiểm tra lại thông tin."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-rose-50 via-background to-amber-50/40 p-4">
      <Card className="w-full min-w-0 max-w-md shadow-lg [overflow-wrap:anywhere]">
        <CardHeader className="space-y-2 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow">
            {branding.logo_url?<img src={branding.logo_url} alt={branding.name||"Logo spa"} className="h-12 w-12 rounded-xl object-contain"/>:<Sparkles className="h-6 w-6" />}
          </div>
          <CardTitle className="text-xl font-bold">
            {branding.name||"Đăng nhập"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
            {error && (
              <div role="alert" className="min-w-0 [overflow-wrap:anywhere] rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">
                {error}
              </div>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="phone">Số điện thoại</Label>
              <div className="relative">
                <Phone className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  disabled={!hydrated || submitting}
                  id="phone"
                  autoComplete="username"
                  type="tel"
                  placeholder="0900000001"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  className="pl-9"
                  required
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">Mật khẩu</Label>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <PasswordInput
                  disabled={!hydrated || submitting}
                  id="password"
                  autoComplete="current-password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-9"
                  required
                />
              </div>
            </div>

            <Button type="submit" className="w-full" disabled={!hydrated || submitting}>
              {submitting ? "Đang đăng nhập..." : "Đăng nhập"}
            </Button>
            <p className="text-sm text-muted-foreground">Quên mật khẩu? Liên hệ đơn vị triển khai để nhận liên kết đặt lại.</p>
            <div className="flex flex-wrap justify-between gap-3 text-sm"><Link className="inline-flex min-h-11 items-center underline" href="/">Trang đặt lịch cho khách</Link><Link className="inline-flex min-h-11 items-center underline" href="/operator/login">Quản trị hệ thống</Link></div>

            <p className="text-center text-xs text-muted-foreground">Chưa có tài khoản? Liên hệ chủ spa để được hỗ trợ.</p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
