"use client";
import * as React from "react";
import { apiRequest, saveAuthSession, getAdminSessionIdentity } from "@/lib/api";
import { customerApiRequest, saveCustomerToken, getCustomerSessionIdentity } from "@/lib/customer-api";
import { useBranchGuard } from "@/lib/branch-guard";
import type { TokenResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
export function CredentialForm({ slug, staffId, phone, onSaved, onBusyChange, onDirtyChange }: {slug?: string; staffId?: string; phone?: string; onSaved?: () => void; onBusyChange?: (busy: boolean) => void; onDirtyChange?: (dirty: boolean) => void}): React.ReactElement {
  const [current, setCurrent] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [number, setNumber] = React.useState(phone || "");
  const [busy, setBusy] = React.useState(false);
  const flight = React.useRef(false), alive = React.useRef(false);
  React.useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  const [message, setMessage] = React.useState("");
  const [error, setError] = React.useState("");
  React.useEffect(() => { onBusyChange?.(busy); return () => onBusyChange?.(false); }, [busy, onBusyChange]);
  React.useEffect(() => { onDirtyChange?.(Boolean(current || password || number !== (phone || ""))); return () => onDirtyChange?.(false); }, [current, password, number, phone, onDirtyChange]);
  useBranchGuard(!slug && Boolean(current || password || number !== (phone || "")), !slug && busy);
  return <form className="space-y-4 rounded-2xl border neu-surface bg-card p-5" onSubmit={async (event) => {
    event.preventDefault(); if (flight.current) return; flight.current = true; setBusy(true); setError(""); setMessage("");
    const identity = slug ? getCustomerSessionIdentity(slug) : getAdminSessionIdentity();
    const currentSession = () => alive.current && identity === (slug ? getCustomerSessionIdentity(slug) : getAdminSessionIdentity());
    try {
      const body = { current_password: current, password, ...(!slug && number ? { phone_number: number } : {}) };
      if (slug) {
        const result = await customerApiRequest<TokenResponse>("/account/credentials", { slug, method: "PATCH", body, requireAuth: true });
        if (!currentSession()) return;
        saveCustomerToken(slug, result.access_token);
      } else if (staffId) await apiRequest("/staff/" + staffId + "/account", { method: "PATCH", body });
      else {
        const result = await apiRequest<TokenResponse>("/account/credentials", { method: "PATCH", body });
        if (!currentSession()) return;
        const { getStoredSlug } = await import("@/lib/api");
        if (!currentSession()) return;
        saveAuthSession(result.access_token, getStoredSlug() || "");
      }
      if (staffId && !currentSession()) return;
      setCurrent(""); setPassword(""); setMessage("Đã cập nhật tài khoản. Các phiên đăng nhập cũ đã hết hiệu lực."); onSaved?.();
    } catch (e) { setError(e instanceof Error ? e.message : "Chưa cập nhật được tài khoản"); }
    finally { flight.current = false; setBusy(false); }
  }}>
    <h2 className="font-bold">{staffId ? "Tài khoản đăng nhập của nhân viên" : "Đổi mật khẩu"}</h2>
    <p className="text-xs text-muted-foreground">{staffId ? "Thay đổi áp dụng ở mọi chi nhánh của tài khoản. Nhập mật khẩu của bạn để xác nhận; bạn cần quyền chủ spa ở tất cả các chi nhánh đó." : "Nhập mật khẩu hiện tại để xác nhận. Mật khẩu mới áp dụng cho tài khoản của bạn."}</p>
    <fieldset disabled={busy} className="space-y-3">
      {!slug && <div><Label htmlFor="credentialPhone">Số điện thoại đăng nhập</Label><Input id="credentialPhone" type="tel" value={number} onChange={(event) => setNumber(event.target.value)} /></div>}
      <div><Label htmlFor="credentialCurrent">Mật khẩu {staffId ? "của bạn" : "hiện tại"}</Label><PasswordInput id="credentialCurrent" autoComplete="current-password" required value={current} onChange={(event) => setCurrent(event.target.value)} /></div>
      <div><Label htmlFor="credentialNew">Mật khẩu mới (ít nhất 8 ký tự)</Label><PasswordInput id="credentialNew" autoComplete="new-password" required minLength={8} maxLength={72} value={password} onChange={(event) => setPassword(event.target.value)} /></div>
      <Button type="submit" disabled={busy}>{busy ? "Đang cập nhật..." : "Cập nhật tài khoản"}</Button>
    </fieldset>
    {error && <p role="alert" className="feedback-error">{error}</p>}{message && <p role="status" className="feedback-success">{message}</p>}
  </form>;
}
