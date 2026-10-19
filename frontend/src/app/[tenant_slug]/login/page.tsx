"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Lock, Phone } from "lucide-react";
import { loginCustomer, saveCustomerToken } from "@/lib/customer-api";
import { useCustomerTenant } from "@/components/customer/customer-context";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";

export default function CustomerLoginPage(): React.ReactElement | null {
  const router = useRouter();
  const { slug, tenant, refreshCustomer } = useCustomerTenant();

  const [phoneNumber, setPhoneNumber] = React.useState<string>("");
  const [password, setPassword] = React.useState<string>("");
  const [submitting, setSubmitting] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string | null>(null);

  if (!tenant) return null;
  const themeColor = "var(--brand-color)";

  const handleSubmit = async (
    e: React.FormEvent<HTMLFormElement>
  ): Promise<void> => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await loginCustomer(slug, {
        phone_number: phoneNumber.trim(),
        password,
      });
      saveCustomerToken(slug, res.access_token);
      await refreshCustomer();
      router.push(`/${slug}/book`);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Số điện thoại hoặc mật khẩu không đúng."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="py-4">
      <Card className="shadow-md">
        <CardHeader className="text-center space-y-1">
          <CardTitle className="text-lg font-bold">
            Đăng nhập Khách hàng
          </CardTitle>
          <CardDescription>
            Đặt lịch nhanh & quản lý thẻ liệu trình tại{" "}
            <strong className="text-foreground">{tenant.name}</strong>
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
              <Label htmlFor="custPhone">Số điện thoại</Label>
              <div className="relative">
                <Phone className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="custPhone"
                  type="tel"
                  inputMode="tel"
                  autoComplete="username"
                  placeholder="Nhập số điện thoại"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  className="pl-9"
                  required
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="custPassword">Mật khẩu</Label>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="custPassword"
                  type="password"
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-9"
                  required
                />
              </div>
            </div>

            <Button
              type="submit"
              className="w-full"
              style={{ backgroundColor: themeColor, color: "var(--brand-foreground)" }}
              disabled={submitting}
            >
              {submitting ? "Đang đăng nhập..." : "Đăng nhập"}
            </Button>

            <div className="text-center text-xs text-muted-foreground">
              Lần đầu đến {tenant.name}?{" "}
              <Link
                href={`/${slug}/register`}
                className="font-semibold hover:underline"
                style={{ color: "var(--brand-text)" }}
              >
                Đăng ký tài khoản mới
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
