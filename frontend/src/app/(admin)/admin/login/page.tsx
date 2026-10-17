"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Sparkles, Lock, Phone } from "lucide-react";
import { loginAdmin, saveAuthSession } from "@/lib/api";
import { useAdminAuth } from "@/components/admin/auth-context";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function AdminLoginPage(): React.ReactElement {
  const router = useRouter();
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
    setError(null);
    setSubmitting(true);
    try {
      const res = await loginAdmin(phoneNumber, password);
      if (res.user.role !== "ADMIN" && res.user.role !== "STAFF") {
        setError("Tài khoản này không có quyền truy cập trang Quản trị Spa.");
        return;
      }
      saveAuthSession(res.access_token, "");
      await refreshMe();
      router.push(res.user.role === "ADMIN" ? "/admin/dashboard" : "/admin/bookings");
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
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="space-y-2 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow">
            <Sparkles className="h-6 w-6" />
          </div>
          <CardTitle className="text-xl font-bold">
            Đăng nhập Quản trị SpaOS
          </CardTitle>
          <CardDescription>
            Dành cho Chủ Spa (ADMIN) & Kỹ thuật viên / Lễ tân (STAFF)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
            {error && (
              <div className="rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">
                {error}
              </div>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="phone">Số điện thoại</Label>
              <div className="relative">
                <Phone className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
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
                <Lock className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
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
              {submitting ? "Đang xác thực..." : "Đăng nhập vào Dashboard"}
            </Button>

            <p className="text-center text-xs text-muted-foreground">Chưa có tài khoản? Liên hệ chủ spa để được cấp quyền.</p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
