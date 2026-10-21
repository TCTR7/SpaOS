"use client";
import * as React from "react";
import { useCustomerTenant } from "./customer-context";
import { customerApiRequest } from "@/lib/customer-api";
import { CredentialForm } from "@/components/credential-form";
import { Input, Label } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
export function ProfileEditor(): React.ReactElement | null {
  const { user, slug, refreshCustomer, reloadCustomerProfile } = useCustomerTenant();
  const [name, setName] = React.useState(user?.full_name || "");
  const [busy, setBusy] = React.useState(false), [error, setError] = React.useState(""), [message, setMessage] = React.useState("");
  const flight = React.useRef(false);
  if (!user) return null;
  return <details className="disclosure"><summary className="min-h-11 cursor-pointer py-2 font-semibold">Sửa hồ sơ và mật khẩu</summary>
    <form className="space-y-3 py-3" onSubmit={async (event) => {
      event.preventDefault(); if (flight.current) return; flight.current = true; setBusy(true); setError(""); setMessage("");
      try { await customerApiRequest("/account/profile", { slug, method: "PATCH", requireAuth: true, body: { full_name: name } }); await reloadCustomerProfile(); setMessage("Đã cập nhật họ tên."); }
      catch (e) { setError(e instanceof Error ? e.message : "Chưa lưu được hồ sơ"); }
      finally { flight.current = false; setBusy(false); }
    }}><Label htmlFor="profileName">Họ và tên</Label><Input id="profileName" required maxLength={255} disabled={busy} value={name} onChange={(event) => setName(event.target.value)} /><Button disabled={busy} type="submit">Lưu họ tên</Button>
      <p className="text-xs text-muted-foreground">Số điện thoại là thông tin đăng nhập. Liên hệ spa nếu bạn cần thay đổi hoặc đối chiếu hồ sơ.</p>
      {error && <p role="alert" className="feedback-error">{error}</p>}{message && <p role="status" className="feedback-success">{message}</p>}
    </form>
    <CredentialForm slug={slug} onSaved={() => void refreshCustomer()} />
  </details>;
}
