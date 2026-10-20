"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Lock, Phone, User as UserIcon } from "lucide-react";
import { registerCustomer, saveCustomerToken } from "@/lib/customer-api";
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

export default function CustomerRegisterPage(): React.ReactElement | null {
  const router = useRouter();
  const { slug, tenant, refreshCustomer } = useCustomerTenant();

  const [fullName, setFullName] = React.useState<string>("");
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
    if (submitting) return;
    setError(null);
    setSubmitting(true);
    try {
      const res = await registerCustomer(slug, {
        full_name: fullName.trim(),
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
          : "Đăng ký thất bại, vui lòng kiểm tra lại SĐT."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="py-4">
      <Card className="min-w-0 shadow-md [overflow-wrap:anywhere]">
        <CardHeader className="text-center space-y-1">
          <CardTitle className="text-lg font-bold">
            Đăng ký Thành viên
          </CardTitle>
          <CardDescription>
            Tạo tài khoản khách hàng tại{" "}
            <strong className="text-foreground">{tenant.name}</strong>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
            {error && (
              <div role="alert" className="min-w-0 [overflow-wrap:anywhere] rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">
                {error}
              </div>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="regName">Họ và tên của bạn</Label>
              <div className="relative">
                <UserIcon className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="regName"
                  placeholder="Nguyễn Minh Anh"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="pl-9"
                  required
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="regPhone">Số điện thoại</Label>
              <div className="relative">
                <Phone className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="regPhone"
                  type="tel"
                  inputMode="tel"
                  placeholder="0912345678"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  className="pl-9"
                  required
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="regPassword">Mật khẩu (tối thiểu 6 ký tự)</Label>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="regPassword"
                  type="password"
                  minLength={6}
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
              {submitting ? "Đang tạo tài khoản..." : "Hoàn tất đăng ký"}
            </Button>

            <div className="text-center text-xs text-muted-foreground">
              Đã có tài khoản?{" "}
              <Link
                href={`/${slug}/login`}
                className="font-semibold hover:underline"
                style={{ color: "var(--brand-text)" }}
              >
                Đăng nhập ngay
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
