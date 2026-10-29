"use client";
import * as React from "react";
import { Modal } from "@/components/ui/modal";
import { spaPath } from "@/lib/spa-path";
import { SpaLogo } from "@/components/spa-logo";
import { Badge } from "@/components/ui/card";
import { BranchDirtyError } from "@/lib/branch-guard";
import { useBranchGuard } from "@/lib/branch-guard";
import { useAdminAuth } from "@/components/admin/auth-context";
import { apiRequest, createBranch, fetchStaffList, grantBranchStaff } from "@/lib/api";
import type { BranchAccess, UserDetail } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";

export default function BranchesPage(): React.ReactElement {
  const { user, tenant, branches, refreshMe, reloadTenant, changeBranch } = useAdminAuth();
  const [createdBranch, setCreatedBranch] = React.useState<string | null>(() => typeof window === "undefined" ? null : sessionStorage.getItem("spaos_setup_branch_" + tenant?.id + "_" + user?.id));
  const [discardSetup,setDiscardSetup]=React.useState(false);
  const [managed,setManaged]=React.useState<BranchAccess[]>([]);
  const [attempt,setAttempt]=React.useState(0);
  const [statusTarget,setStatusTarget]=React.useState<BranchAccess|null>(null);
  const [name, setName] = React.useState("");
  const [staff, setStaff] = React.useState<UserDetail[]>([]);
  const [staffId, setStaffId] = React.useState("");
  const [target, setTarget] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState("");
  useBranchGuard(!!name || !!staffId || !!target, busy);
  const owner = user?.role === "ADMIN" && branches.some((b) => b.tenant.id === tenant?.id && b.is_owner);
  React.useEffect(() => {
    if (!owner) return;
    let cancelled = false;
    void Promise.all([fetchStaffList(),apiRequest<BranchAccess[]>("/branches/manage")]).then(([data,all]) => { if (!cancelled) {setStaff(data);setManaged(all);} })
      .catch((e: unknown) => { if (!cancelled) setError(e instanceof Error ? e.message : "Không tải được nhân viên"); });
    return () => { cancelled = true; };
  }, [owner, tenant?.id, attempt, branches]);
  if (!owner) return <p role="alert" className="feedback-error">Bạn chưa thể quản lý chi nhánh. Vui lòng liên hệ chủ spa.</p>;
  return <div className="mx-auto max-w-4xl min-w-0 space-y-5 [overflow-wrap:anywhere]"><h1 className="text-xl font-bold">Quản lý chi nhánh</h1>
    {error && <div role="alert" className="text-rose-700">{error}<Button variant="outline" onClick={()=>{setError(null);setAttempt(v=>v+1);}}>Tải lại danh sách</Button></div>}{message && <p role="status" className="feedback-success">{message}</p>}
    <section className="space-y-3 rounded-xl border neu-surface bg-card p-4"><h2 className="font-bold">Các chi nhánh của bạn</h2>
      {managed.map((b) => <div key={b.tenant.id} className="flex flex-wrap items-center justify-between gap-4 rounded-xl border bg-muted/20 p-4"><div className="flex min-w-0 flex-1 items-center gap-3"><SpaLogo name={b.tenant.name} src={b.tenant.logo_url} /><div className="min-w-0"><p className="font-semibold [overflow-wrap:anywhere]">{b.tenant.name}</p>{b.tenant.id === tenant?.id && <Badge variant="secondary" className="mt-1">Đang làm việc</Badge>}</div></div><a className="action-link" href={spaPath("/" + b.tenant.slug)} target="_blank" rel="noreferrer">Trang đặt lịch</a>{b.tenant.status!=="ACTIVE"&&<Badge variant="secondary">Tạm ngưng</Badge>}{b.tenant.id!==tenant?.id&&<Button variant="outline" disabled={busy} onClick={()=>setStatusTarget(b)}>{b.tenant.status==="ACTIVE"?"Tạm ngưng ":"Mở lại "}{b.tenant.name}</Button>}</div>)}
    </section>
    <form className="space-y-3 rounded-xl border neu-surface bg-card p-4" onSubmit={async (e) => { e.preventDefault(); if (busy) return; setBusy(true); setError(null); setMessage(""); try {
      const created = await createBranch(name); setCreatedBranch(created.tenant.id); sessionStorage.setItem("spaos_setup_branch_" + tenant?.id + "_" + user?.id, created.tenant.id); setName(""); await refreshMe(); setMessage("Đã tạo chi nhánh. Chọn chi nhánh trên thanh phía trên để thiết lập dịch vụ và nhân sự.");
    } catch (e) { setError(e instanceof Error ? e.message : "Không tạo được chi nhánh"); } finally { setBusy(false); } }}>
      <h2 className="font-bold">Thêm chi nhánh</h2><Label htmlFor="branchName">Tên chi nhánh</Label><Input id="branchName" required maxLength={255} value={name} disabled={busy} onChange={(e) => setName(e.target.value)} />
      <Button disabled={busy || !name.trim()} type="submit">Tạo chi nhánh</Button>
    </form>
    {createdBranch && <section className="space-y-2 rounded-xl border neu-surface bg-card p-4"><h2 className="font-bold">Bước tiếp theo: thiết lập chi nhánh mới</h2><p className="text-sm">Bổ sung địa chỉ, dịch vụ và ca làm rồi kiểm tra giờ trống trước khi chia sẻ cho khách.</p><Button disabled={busy} onClick={() => { void changeBranch(createdBranch).catch((e: unknown) => { if(e instanceof BranchDirtyError)setDiscardSetup(true);else setError(e instanceof Error ? e.message : "Chưa chuyển được chi nhánh"); setBusy(false); }); }}>Chuyển sang thiết lập chi nhánh mới</Button></section>}
    <form className="space-y-3 rounded-xl border neu-surface bg-card p-4" onSubmit={async (e) => { e.preventDefault(); if (busy) return; setBusy(true); setError(null); setMessage(""); try {
      await grantBranchStaff(target, staffId); setStaffId(""); setTarget(""); setMessage("Đã thêm nhân viên vào chi nhánh. Nhân viên tiếp tục dùng số điện thoại và mật khẩu hiện tại.");
    } catch (e) { setError(e instanceof Error ? e.message : "Không thêm được nhân viên vào chi nhánh"); } finally { setBusy(false); } }}>
      <h2 className="font-bold">Cho nhân viên làm thêm chi nhánh</h2>
      <Label htmlFor="branchStaff">Nhân viên tại {tenant?.name}</Label>
      <select id="branchStaff" required disabled={busy} className="h-11 w-full min-w-0 text-base sm:text-sm rounded-md border bg-background px-2" value={staffId} onChange={(e) => setStaffId(e.target.value)}><option value="">Chọn nhân viên</option>{staff.filter((s) => s.is_active).map((s) => <option key={s.id} value={s.id}>{s.full_name} • {s.phone_number}</option>)}</select>
      <Label htmlFor="targetBranch">Chi nhánh làm thêm</Label>
      <select id="targetBranch" required disabled={busy} className="h-11 w-full min-w-0 text-base sm:text-sm rounded-md border bg-background px-2" value={target} onChange={(e) => setTarget(e.target.value)}><option value="">Chọn chi nhánh</option>{branches.filter((b) => b.is_owner && b.tenant.id !== tenant?.id).map((b) => <option key={b.tenant.id} value={b.tenant.id}>{b.tenant.name}</option>)}</select>
      <Button disabled={busy || !staffId || !target} type="submit">Thêm vào chi nhánh</Button>
      <p className="text-xs text-muted-foreground">Cấp quyền chưa tạo ca làm. Bạn có thể thiết lập theo bất kỳ thứ tự nào; sau khi cấp quyền, vào Nhân sự → Ca làm để phân công ngày làm tại chi nhánh.</p>
    </form>
    <Modal open={discardSetup} onClose={()=>setDiscardSetup(false)} title="Chuyển sang chi nhánh mới?" pending={busy}>
      <p className="mb-4 text-sm">Các mục chưa lưu trên màn hình này sẽ bị bỏ. Nhân viên đã thêm thành công vẫn được giữ quyền.</p>
      <div className="flex flex-wrap gap-2"><Button variant="outline" onClick={()=>setDiscardSetup(false)}>Tiếp tục nhập</Button><Button disabled={busy} onClick={()=>{if(!createdBranch)return;setBusy(true);void changeBranch(createdBranch,true).catch((e:unknown)=>{setError(e instanceof Error?e.message:"Chưa chuyển được chi nhánh");setBusy(false);setDiscardSetup(false);});}}>Bỏ nội dung chưa lưu và chuyển</Button></div>
    </Modal>
    <Modal open={statusTarget!==null} onClose={()=>setStatusTarget(null)} title={statusTarget?.tenant.status==="ACTIVE"?"Tạm ngưng chi nhánh?":"Mở lại chi nhánh?"} pending={busy}>
      <p className="mb-4 text-sm">{statusTarget?.tenant.name}. Khi tạm ngưng, cần xử lý lịch hẹn và bàn giao khách về chủ spa trước; ca tương lai tại đây sẽ kết thúc. Lịch sử được giữ. Khi mở lại, thiết lập ca nhận khách và kiểm tra giới hạn gói.</p>
      <Button disabled={busy} onClick={async()=>{
        if(!statusTarget||busy)return;setBusy(true);setError(null);
        try{
          await apiRequest(`/branches/${statusTarget.tenant.id}/status`,{method:"PATCH",body:{status:statusTarget.tenant.status==="ACTIVE"?"INACTIVE":"ACTIVE"}});
          setStatusTarget(null);await reloadTenant();setAttempt(v=>v+1);setMessage("Đã cập nhật trạng thái chi nhánh. Lịch sử được giữ nguyên.");
        }catch(e){setStatusTarget(null);setError(e instanceof Error?e.message:"Chưa cập nhật được chi nhánh");}
        finally{setBusy(false);}
      }}>{busy?"Đang cập nhật...":"Xác nhận trạng thái chi nhánh"}</Button>
    </Modal>
  </div>;
}
