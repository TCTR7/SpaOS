"use client";
import * as React from "react";
import { apiRequest } from "@/lib/api";
import { useBranchGuard } from "@/lib/branch-guard";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
export function RecoveryLink({ customerId, slug }: {customerId: string; slug: string}): React.ReactElement {
  const [verified, setVerified] = React.useState(false), [password, setPassword] = React.useState("");
  const [busy, setBusy] = React.useState(false), [link, setLink] = React.useState("");
  const [error, setError] = React.useState("");
  const flight = React.useRef(false);
  useBranchGuard(Boolean(password), busy);
  return <details className="disclosure">
    <summary className="min-h-11 cursor-pointer py-2 text-sm font-semibold">Giúp khách đăng nhập hoặc đặt lại mật khẩu</summary>
    <div className="space-y-3">
    <p className="py-2 text-sm">Chỉ cấp liên kết sau khi đã xác minh đúng khách qua thông tin spa đang lưu hoặc gặp trực tiếp. Liên kết dùng một lần trong 30 phút; cấp mới sẽ hủy liên kết cũ.</p>
    <label className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" checked={verified} disabled={busy} onChange={(event) => setVerified(event.target.checked)} />Tôi đã xác minh đúng khách hàng</label>
    <Label htmlFor="recoveryOwnerPassword">Mật khẩu của bạn để xác nhận</Label>
    <PasswordInput id="recoveryOwnerPassword" disabled={busy} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" />
    <Button type="button" disabled={!verified || !password || busy} onClick={async () => {
      if (flight.current) return; flight.current = true; setBusy(true); setError(""); setLink("");
      try {
        const result = await apiRequest<{token: string}>("/customers/" + customerId + "/recovery-link", { method: "POST", body: { identity_verified: verified, current_password: password } });
        setLink(window.location.origin + "/" + encodeURIComponent(slug) + "/activate#" + result.token); setPassword("");
      } catch (e) { setError(e instanceof Error ? e.message : "Chưa cấp được liên kết"); }
      finally { flight.current = false; setBusy(false); }
    }}>{busy ? "Đang cấp..." : "Cấp liên kết cho khách"}</Button>
    {link && <div className="space-y-2 py-2"><p className="break-all text-xs">{link}</p><Button variant="outline" onClick={async () => { try { if (!navigator.clipboard) throw new Error(); await navigator.clipboard.writeText(link); } catch { setError("Hãy chọn và sao chép liên kết bên trên."); } }}>Sao chép liên kết</Button><p className="text-xs">Chỉ gửi riêng cho đúng khách đã xác minh.</p></div>}
    {error && <p role="alert" className="feedback-error">{error}</p>}
    </div>
  </details>;
}
