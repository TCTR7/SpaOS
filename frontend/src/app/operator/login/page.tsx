"use client";
import * as React from "react";
import { operatorLogin } from "@/lib/operator-api";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";

export default function OperatorLoginPage(): React.ReactElement {
  const [phone, setPhone] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [ready, setReady] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  React.useEffect(() => { setReady(true); }, []);
  return <main className="mx-auto min-w-0 [overflow-wrap:anywhere] max-w-md space-y-5 px-4 py-12">
    <h1 className="text-2xl font-bold">Quản trị triển khai SpaOS</h1>
    <p className="text-sm text-muted-foreground">Dành cho đơn vị triển khai và cấp tài khoản chủ spa.</p>
    {error && <p role="alert" className="text-sm text-rose-700">{error}</p>}
    <form className="space-y-4 rounded-xl border neu-surface bg-card p-5" onSubmit={async (e) => {
      e.preventDefault(); if (busy) return; setBusy(true); setError(null);
      try { await operatorLogin(phone.trim(), password); setPassword(""); window.location.assign("/operator"); }
      catch (e) { setError(e instanceof Error ? e.message : "Đăng nhập không thành công"); setBusy(false); }
    }}>
      <Label htmlFor="operatorPhone">Số điện thoại quản trị</Label>
      <Input id="operatorPhone" type="tel" autoComplete="username" required value={phone} disabled={!ready || busy} onChange={(e) => setPhone(e.target.value)} />
      <Label htmlFor="operatorPassword">Mật khẩu</Label>
      <Input id="operatorPassword" type="password" autoComplete="current-password" required value={password} disabled={!ready || busy} onChange={(e) => setPassword(e.target.value)} />
      <Button type="submit" disabled={!ready || busy}>{busy ? "Đang đăng nhập..." : "Đăng nhập quản trị"}</Button>
    </form>
    <a className="text-sm underline" href="/admin/login">Chủ spa / Nhân viên đăng nhập tại đây</a>
  </main>;
}
