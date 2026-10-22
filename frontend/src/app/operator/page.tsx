"use client";
import * as React from "react";
import { BrandColorPicker } from "@/components/brand-color-picker";
import { OperatorBranding } from "@/components/operator-branding";
import { useBranding, announceBranding } from "@/components/brand-provider";
import { clearOperatorToken, operatorRequest, OperatorError } from "@/lib/operator-api";
import type { OperatorIdentity, OwnerCreate, OwnerProvision } from "@/lib/operator-api";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { formatDateTimeVN } from "@/lib/utils";
import { OperatorSystem } from "@/components/operator-system";
import { OperatorOwner } from "@/components/operator-owner";

export default function OperatorPage(): React.ReactElement {
  const {branding,refresh} = useBranding();
  const [ownerColor,setOwnerColor] = React.useState<string | null>(null);
  const [operator, setOperator] = React.useState<OperatorIdentity | null>(null);
  const [selectedOwner, setSelectedOwner] = React.useState<string|null>(null);
  const [rows, setRows] = React.useState<OwnerProvision[]>([]);
  const [offset, setOffset] = React.useState(0);
  const [branch, setBranch] = React.useState("");
  const [name, setName] = React.useState("");
  const [phone, setPhone] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [confirm, setConfirm] = React.useState("");
  const [attempt, setAttempt] = React.useState<OwnerCreate | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState("");
  const [success, setSuccess] = React.useState<OwnerProvision | null>(null);
  const createFlight = React.useRef(false);
  const [loadAttempt, setLoadAttempt] = React.useState(0);
  const locked = busy || attempt !== null;
  const hasOwners = rows.length > 0 || offset > 0 || success !== null;
  const load = async (page = offset): Promise<void> => setRows(await operatorRequest<OwnerProvision[]>("/owners?limit=50&offset="+page));
  React.useEffect(() => {
    let cancelled = false;
    void Promise.all([operatorRequest<OperatorIdentity>("/me"), operatorRequest<OwnerProvision[]>("/owners?limit=50&offset="+offset)])
      .then(([identity, records]) => { if (!cancelled) { setOperator(identity); setRows(records); } })
      .catch((e: unknown) => { if (!cancelled) setError(e instanceof Error ? e.message : "Không tải được trang quản trị"); });
    return () => { cancelled = true; };
  }, [offset, loadAttempt]);
  const create = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault(); if (createFlight.current || busy) return;
    if (!attempt && password !== confirm) { setError("Mật khẩu nhập lại không khớp."); return; }
    const body = attempt || {request_id: crypto.randomUUID(), branch_name: branch.trim(), owner_full_name: name.trim(), phone_number: phone.trim(), password, theme_color: hasOwners ? branding.theme_color : ownerColor || branding.theme_color};
    createFlight.current = true;
    setAttempt(body); setBusy(true); setError(null); setSuccess(null); setMessage("");
    try {
      const record = await operatorRequest<OwnerProvision>("/owners", body);
      setAttempt(null); setPassword(""); setConfirm(""); setBranch(""); setName(""); setPhone(""); setOwnerColor(null);
      await refresh(); announceBranding();
      setSuccess(record); setMessage("Đã tạo tài khoản chủ spa và chi nhánh đầu tiên.");
      setSelectedOwner(record.id);
      try { await load(0); setOffset(0); } catch { setError("Tài khoản đã được tạo. Tải lại trang để xem danh sách mới."); }
    } catch (e) {
      if (e instanceof OperatorError && e.status < 500) setAttempt(null);
      setError(e instanceof Error ? e.message : "Chưa rõ kết quả. Thử lại cùng yêu cầu để tránh tạo trùng.");
    } finally { createFlight.current = false; setBusy(false); }
  };
  return <main className="mx-auto min-w-0 [overflow-wrap:anywhere] max-w-5xl space-y-5 px-4 py-8">
    <div className="flex flex-wrap items-center justify-between gap-3"><h1 className="text-xl font-bold">Cấp tài khoản chủ spa</h1>
      {operator && <Button variant="outline" disabled={locked} onClick={async () => {
        setBusy(true); setError(null);
        try { await operatorRequest("/logout", {}); clearOperatorToken(); window.location.assign("/operator/login"); }
        catch (e) { setError(e instanceof Error ? e.message : "Không đăng xuất được"); setBusy(false); }
      }}>Đăng xuất</Button>}
    </div>
    {operator && <p className="text-sm text-muted-foreground">Quản trị: {operator.full_name}</p>}
    {operator && <OperatorSystem />}
    {error && <div role="alert" className="space-y-2 text-sm text-rose-700"><p>{error}</p><Button variant="outline" disabled={locked} onClick={() => { setError(null); setLoadAttempt((v) => v+1); }}>Thử tải lại danh sách</Button></div>}
    {message && <p role="status" className="text-sm text-emerald-700">{message}</p>}
    {success && <div className="rounded-xl border bg-card p-4 text-sm" data-testid="owner-created">
      <p><strong>{success.owner_name}</strong> • {success.phone_number}</p><p>Chi nhánh: {success.branch_name}</p>
      <p>Bàn giao SĐT và mật khẩu đã đặt qua kênh riêng. Chủ spa đăng nhập tại <a className="underline" href="/admin/login">trang đăng nhập</a>.</p>
    </div>}
    {operator && <form onSubmit={(e) => void create(e)} className="grid gap-3 rounded-xl border bg-card p-5 sm:grid-cols-2">
      <h2 className="font-bold sm:col-span-2">Tạo chủ spa</h2>
      <div><Label htmlFor="ownerName">Họ tên chủ spa</Label><Input id="ownerName" required maxLength={255} value={name} disabled={locked} onChange={(e) => setName(e.target.value)} /></div>
      <div><Label htmlFor="ownerPhone">Số điện thoại chủ spa</Label><Input id="ownerPhone" type="tel" required value={phone} disabled={locked} onChange={(e) => setPhone(e.target.value)} /></div>
      <div className="sm:col-span-2"><Label htmlFor="firstBranch">Tên chi nhánh đầu tiên</Label><Input id="firstBranch" required maxLength={255} value={branch} disabled={locked} onChange={(e) => setBranch(e.target.value)} /></div>
      <div><Label htmlFor="ownerPassword">Mật khẩu bàn giao</Label><Input id="ownerPassword" type="password" autoComplete="new-password" minLength={8} required value={password} disabled={locked} onChange={(e) => setPassword(e.target.value)} /></div>
      <div><Label htmlFor="ownerConfirm">Nhập lại mật khẩu</Label><Input id="ownerConfirm" type="password" autoComplete="new-password" required value={confirm} disabled={locked} onChange={(e) => setConfirm(e.target.value)} /></div>
      {!hasOwners && <div className="sm:col-span-2"><BrandColorPicker id="ownerThemeColor" value={ownerColor || branding.theme_color} onChange={setOwnerColor} disabled={locked} /></div>}
      {attempt && !busy && <p className="text-sm sm:col-span-2">Chưa xác nhận được tài khoản đã tạo. Nhấn thử lại để kiểm tra và tiếp tục.</p>}
      <Button type="submit" disabled={busy}>{busy ? "Đang tạo..." : attempt ? "Thử lại tạo tài khoản" : "Tạo tài khoản chủ spa"}</Button>
    </form>}
    {operator && <section className="space-y-3">
      <h2 className="font-bold">Tài khoản đã cấp</h2>
      {rows.length === 0 && <p className="text-sm text-muted-foreground">Chưa có tài khoản nào được tạo tại đây.</p>}
      <p className="text-xs text-muted-foreground">Thông tin bên dưới ghi nhận thời điểm cấp. Mở quản lý để xem thông tin hiện tại.</p>
      {rows.map((row) => <article key={row.id} data-testid="provision-row" className="space-y-2 rounded-xl border p-4 text-sm"><strong>{row.owner_name}</strong><p>{row.phone_number} • {row.branch_name}</p><p className="text-xs text-muted-foreground">{formatDateTimeVN(row.created_at)}</p><Button variant="outline" disabled={locked} onClick={()=>setSelectedOwner(row.id)}>Quản lý & Bàn giao</Button></article>)}
      <div className="flex gap-2"><Button variant="outline" disabled={locked || offset === 0} onClick={() => setOffset(Math.max(0,offset-50))}>Trang trước</Button><Button variant="outline" disabled={locked || rows.length<50} onClick={() => setOffset(offset+50)}>Trang sau</Button></div>
    </section>}
    {operator && hasOwners && <details className="disclosure"><summary className="min-h-11 cursor-pointer py-2 font-semibold">Cài đặt giao diện</summary><OperatorBranding disabled={locked} /></details>}
    {operator && selectedOwner && <OperatorOwner key={selectedOwner} id={selectedOwner}/>}
  </main>;
}
