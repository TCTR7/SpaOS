"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Sparkles } from "lucide-react";
import { registerTenant, saveAuthSession } from "@/lib/api";
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

export default function RegisterTenantPage(): React.ReactElement {
  const router = useRouter();
  const { refreshMe } = useAdminAuth();

  const [tenantName, setTenantName] = React.useState<string>("");
  const [tenantSlug, setTenantSlug] = React.useState<string>("");
  const [adminFullName, setAdminFullName] = React.useState<string>("");
  const [phoneNumber, setPhoneNumber] = React.useState<string>("");
  const [password, setPassword] = React.useState<string>("");
  const [submitting, setSubmitting] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string | null>(null);

  const handleNameChange = (name: string): void => {
    setTenantName(name);
    if (!tenantSlug) {
      const autoSlug = name
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/đ/g, "d")
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
      setTenantSlug(autoSlug);
    }
  };

  const handleSubmit = async (
    e: React.FormEvent<HTMLFormElement>
  ): Promise<void> => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const slug = tenantSlug.trim().toLowerCase();
      const res = await registerTenant({
        tenant_name: tenantName.trim(),
        tenant_slug: slug,
        admin_full_name: adminFullName.trim(),
        phone_number: phoneNumber.trim(),
        password,
      });
      saveAuthSession(res.access_token, slug);
      await refreshMe();
      router.push("/admin/bookings");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Đăng ký Spa mới thất bại"
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
            Khởi tạo Spa mới trên SpaOS
          </CardTitle>
          <CardDescription>
            Tạo không gian quản lý Multi-tenant riêng biệt cho Spa của bạn
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
              <Label htmlFor="tenantName">Tên Spa / Thẩm mỹ viện</Label>
              <Input
                id="tenantName"
                placeholder="VD: Hoa Hồng Beauty & Spa"
                value={tenantName}
                onChange={(e) => handleNameChange(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="tenantSlug">
                Đường dẫn định danh (Slug: chữ thường, số, gạch ngang)
              </Label>
              <Input
                id="tenantSlug"
                placeholder="vd: spa-hoa-hong"
                value={tenantSlug}
                onChange={(e) => setTenantSlug(e.target.value.toLowerCase())}
                pattern="^[a-z0-9-]+$"
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="adminFullName">Họ và tên Chủ Spa (ADMIN)</Label>
              <Input
                id="adminFullName"
                placeholder="Nguyễn Thị Hoa"
                value={adminFullName}
                onChange={(e) => setAdminFullName(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="phoneNumber">Số điện thoại đăng nhập</Label>
              <Input
                id="phoneNumber"
                type="tel"
                placeholder="0912345678"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">Mật khẩu (tối thiểu 6 ký tự)</Label>
              <Input
                id="password"
                type="password"
                minLength={6}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "Đang khởi tạo Spa..." : "Tạo Spa & Đăng nhập ngay"}
            </Button>

            <div className="text-center text-xs text-muted-foreground">
              Đã có tài khoản Spa?{" "}
              <Link
                href="/admin/login"
                className="font-semibold text-primary hover:underline"
              >
                Quay lại Đăng nhập
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
