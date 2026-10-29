"use client";
import * as React from "react";
import { useRouter } from "@/lib/spa-navigation";
import { useCustomerTenant } from "@/components/customer/customer-context";
import { customerApiRequest, clearCustomerToken, getCustomerSessionIdentity } from "@/lib/customer-api";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
export default function ActivatePage(): React.ReactElement {
  const { slug } = useCustomerTenant();
  const router = useRouter();
  const [token, setToken] = React.useState(""), [password, setPassword] = React.useState("");
  const [busy, setBusy] = React.useState(false), [error, setError] = React.useState("");
  const flight = React.useRef(false), alive = React.useRef(false);
  React.useEffect(() => { alive.current = true; if (window.location.hash) { setToken(window.location.hash.slice(1)); window.history.replaceState(window.history.state, "", window.location.pathname); } return () => { alive.current = false; }; }, []);
  return <div className="space-y-4 rounded-xl border p-4"><h1 className="text-xl font-bold">Đặt mật khẩu của bạn</h1>
    <form className="space-y-3" onSubmit={async (event) => {
      event.preventDefault(); if (flight.current) return; flight.current = true; setBusy(true); setError("");
      const identity = getCustomerSessionIdentity(slug);
      try {
        await customerApiRequest("/auth/recovery", { slug, method: "POST", body: { token, password } });
        if (!alive.current || identity !== getCustomerSessionIdentity(slug)) return;
        setPassword(""); setToken("");
        clearCustomerToken(slug);
        router.replace("/" + slug + "/login?password_set=1");
      } catch (e) { if (alive.current) setError(e instanceof Error ? e.message : "Liên kết chưa sử dụng được. Hãy liên hệ spa."); }
      finally { flight.current = false; if (alive.current) setBusy(false); }
    }}><Label htmlFor="activatePassword">Mật khẩu mới (ít nhất 8 ký tự)</Label><PasswordInput id="activatePassword" minLength={8} maxLength={72} required value={password} disabled={busy} onChange={(event) => setPassword(event.target.value)} autoComplete="new-password" />
    <Button type="submit" disabled={busy || !token}>{busy ? "Đang lưu..." : "Đặt mật khẩu"}</Button>
    {!token && <p>Liên kết không đầy đủ. Hãy nhờ spa cấp liên kết mới.</p>}{error && <p role="alert">{error}</p>}</form>
  </div>;
}
