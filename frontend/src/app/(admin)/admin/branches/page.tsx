"use client";
import * as React from "react";
import { useAdminAuth } from "@/components/admin/auth-context";
import { createBranch, fetchStaffList, grantBranchStaff } from "@/lib/api";
import type { UserDetail } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";

export default function BranchesPage(): React.ReactElement {
  const { user, tenant, branches, refreshMe } = useAdminAuth();
  const [name, setName] = React.useState("");
  const [staff, setStaff] = React.useState<UserDetail[]>([]);
  const [staffId, setStaffId] = React.useState("");
  const [target, setTarget] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState("");
  const owner = user?.role === "ADMIN" && branches.some((b) => b.tenant.id === tenant?.id && b.is_owner);
  React.useEffect(() => {
    if (!owner) return;
    let cancelled = false;
    void fetchStaffList().then((data) => { if (!cancelled) setStaff(data); })
      .catch((e: unknown) => { if (!cancelled) setError(e instanceof Error ? e.message : "Không tải được nhân viên"); });
    return () => { cancelled = true; };
  }, [owner, tenant?.id]);
  if (!owner) return <p role="alert">Chỉ chủ hệ thống được quản lý chi nhánh.</p>;
  return <div className="space-y-5"><h1 className="text-xl font-bold">Quản lý chi nhánh</h1>
    {error && <p role="alert" className="text-rose-700">{error}</p>}{message && <p role="status">{message}</p>}
    <section className="space-y-3 rounded-xl border bg-card p-4"><h2 className="font-bold">Các chi nhánh của bạn</h2>
      {branches.map((b) => <div key={b.tenant.id} className="flex flex-wrap justify-between gap-2 border-b py-2"><span>{b.tenant.name}</span><a className="text-sm underline" href={"/" + b.tenant.slug} target="_blank" rel="noreferrer">Trang đặt lịch</a></div>)}
    </section>
    <form className="space-y-3 rounded-xl border bg-card p-4" onSubmit={async (e) => { e.preventDefault(); setBusy(true); setError(null); setMessage(""); try {
      await createBranch(name); await refreshMe(); setName(""); setMessage("Đã tạo chi nhánh. Chọn chi nhánh trên thanh phía trên để thiết lập dịch vụ và nhân sự.");
    } catch (e) { setError(e instanceof Error ? e.message : "Không tạo được chi nhánh"); } finally { setBusy(false); } }}>
      <h2 className="font-bold">Thêm chi nhánh</h2><Label htmlFor="branchName">Tên chi nhánh</Label><Input id="branchName" required maxLength={255} value={name} disabled={busy} onChange={(e) => setName(e.target.value)} />
      <Button disabled={busy || !name.trim()} type="submit">Tạo chi nhánh</Button>
    </form>
    <form className="space-y-3 rounded-xl border bg-card p-4" onSubmit={async (e) => { e.preventDefault(); setBusy(true); setError(null); setMessage(""); try {
      await grantBranchStaff(target, staffId); setMessage("Đã cấp quyền chi nhánh cho nhân viên. Tài khoản dùng chung SĐT và mật khẩu hiện có.");
    } catch (e) { setError(e instanceof Error ? e.message : "Không cấp được quyền"); } finally { setBusy(false); } }}>
      <h2 className="font-bold">Cho nhân viên làm thêm chi nhánh</h2>
      <Label htmlFor="branchStaff">Nhân viên tại {tenant?.name}</Label>
      <select id="branchStaff" required disabled={busy} className="h-9 w-full rounded-md border bg-background px-2" value={staffId} onChange={(e) => setStaffId(e.target.value)}><option value="">Chọn nhân viên</option>{staff.filter((s) => s.is_active).map((s) => <option key={s.id} value={s.id}>{s.full_name} • {s.phone_number}</option>)}</select>
      <Label htmlFor="targetBranch">Chi nhánh được cấp thêm</Label>
      <select id="targetBranch" required disabled={busy} className="h-9 w-full rounded-md border bg-background px-2" value={target} onChange={(e) => setTarget(e.target.value)}><option value="">Chọn chi nhánh</option>{branches.filter((b) => b.is_owner && b.tenant.id !== tenant?.id).map((b) => <option key={b.tenant.id} value={b.tenant.id}>{b.tenant.name}</option>)}</select>
      <Button disabled={busy || !staffId || !target} type="submit">Cấp quyền chi nhánh</Button>
      <p className="text-xs text-muted-foreground">Lịch làm việc và khách phụ trách được thiết lập riêng. Để thu hồi quyền ở một chi nhánh, tắt hoạt động nhân viên tại chi nhánh đó.</p>
    </form>
  </div>;
}
