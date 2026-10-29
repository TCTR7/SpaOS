"use client";

import * as React from "react";
import { WorkforceEditor } from "@/components/admin/workforce-editor";
import { useAdminAuth } from "@/components/admin/auth-context";
import { CredentialForm } from "@/components/credential-form";
import { useBranchGuard } from "@/lib/branch-guard";
import { useListDetail } from "@/lib/use-list-detail";
import Link from "@/components/spa-link";
import { StaffAvatar } from "@/components/admin/staff-avatar";
import { CalendarClock, Contact, Edit2, Plus, Save, UserCheck } from "lucide-react";
import {
  createStaff,
  fetchStaffList,
  updateStaff,
} from "@/lib/api";
import type { UserDetail } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Badge,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input, Label, Textarea } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";

export default function AdminStaffPage(): React.ReactElement {
  const {branches,tenant} = useAdminAuth();
  const [branchIds,setBranchIds] = React.useState<string[]>([]);
  const detail = useListDetail();
  const [accountDirty, setAccountDirty] = React.useState(false);
  const [accountBusy, setAccountBusy] = React.useState(false);
  const [dateDirty, setDateDirty] = React.useState(false), [dateBusy, setDateBusy] = React.useState(false);
  const [schedDirty, setSchedDirty] = React.useState(false);
  const [pendingStaff, setPendingStaff] = React.useState<UserDetail | null>(null);
  const staffFlight = React.useRef(false);
  const [staffList, setStaffList] = React.useState<UserDetail[]>([]);
  const [selectedStaff, setSelectedStaff] = React.useState<UserDetail | null>(
    null
  );
  const [loading, setLoading] = React.useState<boolean>(true);
  const [savingSched, setSavingSched] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string | null>(null);
  const [successMsg, setSuccessMsg] = React.useState<string | null>(null);

  // Staff Create / Edit Modal
  const [modalOpen, setModalOpen] = React.useState<boolean>(false);
  const [editingStaff, setEditingStaff] = React.useState<UserDetail | null>(
    null
  );
  const [fullName, setFullName] = React.useState<string>("");
  const [phoneNumber, setPhoneNumber] = React.useState<string>("");
  const [password, setPassword] = React.useState<string>("");
  const [notes, setNotes] = React.useState<string>("");
  const [isActive, setIsActive] = React.useState<boolean>(true);
  const [savingStaff, setSavingStaff] = React.useState<boolean>(false);

  useBranchGuard(schedDirty, savingSched);
  const loadStaff = React.useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const list = await fetchStaffList();
      setStaffList(list);
      if (selectedStaff) setSelectedStaff((current) => list.find((row) => row.id === current?.id) || null);
      if (list.length > 0 && !selectedStaff) {
        setSelectedStaff(list[0]);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Không thể tải danh sách Kỹ thuật viên"
      );
    } finally {
      setLoading(false);
    }
  }, [selectedStaff]);

  React.useEffect(() => {
    void loadStaff();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openAddStaff = (): void => {
    if (savingSched) return;
    setEditingStaff(null);
    setBranchIds(tenant ? [tenant.id] : []);
    setFullName("");
    setPhoneNumber("");
    setPassword("");
    setNotes("");
    setIsActive(true);
    setModalOpen(true);
  };

  const openEditStaff = (st: UserDetail): void => {
    if (savingSched) return;
    setEditingStaff(st);
    setFullName(st.full_name);
    setPhoneNumber(st.phone_number);
    setPassword("");
    setNotes(st.notes || "");
    setIsActive(st.is_active);
    setModalOpen(true);
  };

  const handleSaveStaff = async (
    e: React.FormEvent<HTMLFormElement>
  ): Promise<void> => {
    e.preventDefault();
    if (staffFlight.current) return;
    staffFlight.current = true;
    setSavingStaff(true);
    setError(null);
    setSuccessMsg(null);
    try {
      if (editingStaff) {
        const payload: Partial<{
          full_name: string;
          phone_number: string;
          password: string;
          notes: string | null;
          is_active: boolean;
        }> = {
          full_name: fullName.trim(),
          notes: notes.trim() || null,
          is_active: isActive,
        };

        const updated = await updateStaff(editingStaff.id, payload);
        setStaffList((prev) =>
          prev.map((s) => (s.id === updated.id ? updated : s))
        );
        if (selectedStaff?.id === updated.id) {
          setSelectedStaff(updated);
        }
      } else {
        const created = await createStaff({
          branch_ids:branchIds,
          full_name: fullName.trim(),
          phone_number: phoneNumber.trim(),
          password: password.trim(),
          notes: notes.trim() || null,
        });
        setStaffList((prev) => [created, ...prev]);
        setSelectedStaff(created); detail.open();
      }
      setModalOpen(false);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Lưu thông tin nhân sự thất bại"
      );
    } finally {
      staffFlight.current = false;
      setSavingStaff(false);
    }
  };

  return (
    <div className="min-w-0 space-y-5 [overflow-wrap:anywhere]">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">
            Nhân viên và lịch làm việc
          </h1>
          <p className="text-xs text-muted-foreground">
            Quản lý nhân viên và sắp xếp lịch làm
            việc 7 ngày trong tuần
          </p>
        </div>
        <Button size="sm" onClick={openAddStaff}>
          <Plus className="h-4 w-4" />
          Thêm Kỹ thuật viên mới
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-300 bg-rose-50 px-4 py-2.5 text-xs font-medium text-rose-700">
          {error}
        </div>
      )}

      {successMsg && (
        <div className="rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-2.5 text-xs font-medium text-emerald-800">
          {successMsg}
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-12">
        {/* Left: Staff List */}
        <div ref={detail.listRef} className={cn("min-w-0 lg:col-span-4", detail.detailOpen && "hidden lg:block")}><Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">
              Danh sách Kỹ thuật viên ({staffList.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 pt-0">
            {loading ? (
              <p className="py-8 text-center text-xs text-muted-foreground">
                Đang tải nhân sự...
              </p>
            ) : error && staffList.length === 0 ? (
              <Button variant="outline" onClick={() => void loadStaff()}>Thử tải lại nhân sự</Button>
            ) : staffList.length === 0 ? (
              <p className="py-8 text-center text-xs text-muted-foreground">
                Chưa có Kỹ thuật viên nào.
              </p>
            ) : (
              staffList.map((st) => {
                const active = selectedStaff?.id === st.id;
                return (
                  <div
                    key={st.id}
                    className={cn(
                      "flex cursor-pointer items-center justify-between gap-2 rounded-lg border p-3 transition",
                      active
                        ? "border-primary bg-primary/10"
                        : "border-border hover:bg-muted/50"
                    )}
                  >
                    <StaffAvatar name={st.full_name} src={st.photo_url} />
                    <button type="button" aria-pressed={active} disabled={savingSched || accountBusy || dateBusy}
                      onClick={(event) => {
                        if ((schedDirty || accountDirty || dateDirty) && selectedStaff?.id !== st.id) setPendingStaff(st);
                        else { if (selectedStaff?.id !== st.id) { } setSelectedStaff(st); detail.open(event.currentTarget); }
                      }} className="min-w-0 flex-1 py-1 text-left">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-sm font-semibold text-foreground">
                          {st.full_name}
                        </p>
                        <Badge variant={st.is_active ? "success" : "outline"}>
                          {st.is_active ? "Đang làm việc" : "Ngưng làm việc"}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        SĐT: {st.phone_number}
                      </p>
                      {st.job_title && <p className="text-xs font-medium text-primary">{st.job_title}{st.experience_years ? ` · ${st.experience_years} năm KN` : ""}</p>}
                      {st.notes && (
                        <p className="mt-0.5 line-clamp-2 text-xs text-slate-600">
                          {st.notes}
                        </p>
                      )}
                    </button>
                    <Button
                      variant="ghost"
                      aria-label={`Sửa thông tin ${st.full_name}`}
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation();
                        openEditStaff(st);
                      }}
                    >
                      <Edit2 className="h-3.5 w-3.5" />
                    </Button>
                    <Link href={`/admin/staff/${st.id}`} aria-label={`Hồ sơ ${st.full_name}`} title="Hồ sơ, ảnh & kỹ năng"
                      className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-md text-primary hover:bg-accent sm:h-9 sm:w-9">
                      <Contact className="h-4 w-4" />
                    </Link>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card></div>

        <Card className={cn("min-w-0 lg:col-span-8", !detail.detailOpen && "hidden lg:block")}>
          {selectedStaff ? <><div className="p-3 lg:hidden"><Button variant="outline" onClick={detail.back}>Quay lại danh sách KTV</Button></div><WorkforceEditor key={selectedStaff.id} staffId={selectedStaff.id} onDirtyChange={setSchedDirty} onBusyChange={setSavingSched}/></> : <CardContent>Chọn nhân viên để phân công theo ngày.</CardContent>}
        </Card>
      </div>

      {selectedStaff && detail.detailOpen && <div className="ml-auto w-full max-w-2xl space-y-4">
        <CredentialForm key={selectedStaff.id + ":account"} staffId={selectedStaff.id} phone={selectedStaff.phone_number} onSaved={() => void loadStaff()} onBusyChange={setAccountBusy} onDirtyChange={setAccountDirty} />
      </div>}
      {/* Add / Edit Staff Modal */}
      <Modal open={!!pendingStaff} onClose={() => setPendingStaff(null)} title="Bỏ thay đổi chưa lưu?">
        <p>Đổi nhân viên sẽ bỏ các thay đổi chưa lưu.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => setPendingStaff(null)}>Tiếp tục chỉnh sửa</Button>
          <Button onClick={() => { setSelectedStaff(pendingStaff); setSchedDirty(false); setPendingStaff(null); detail.open(); }}>Bỏ thay đổi và chọn KTV</Button>
        </div>
      </Modal>
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        pending={savingStaff}
        dirty={editingStaff ? fullName !== editingStaff.full_name || phoneNumber !== editingStaff.phone_number || notes !== (editingStaff.notes || "") || isActive !== editingStaff.is_active || !!password : !!fullName || !!phoneNumber || !!notes || !!password}
        title={
          editingStaff
            ? "Cập nhật Kỹ thuật viên"
            : "Thêm kỹ thuật viên"
        }
      >
        <form onSubmit={(e) => void handleSaveStaff(e)} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="stName">Họ và tên Kỹ thuật viên</Label>
            <Input
              id="stName"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Trần Ngọc Mai"
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="stPhone">Số điện thoại đăng nhập</Label>
            <Input
              id="stPhone" readOnly={Boolean(editingStaff)}
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="0900000015"
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="stPwd">
              {editingStaff
                ? "Đổi mật khẩu ở mục Tài khoản đăng nhập bên dưới lịch làm"
                : "Mật khẩu đăng nhập (>= 6 ký tự)"}
            </Label>
            <Input
              id="stPwd" disabled={Boolean(editingStaff)}
              type="password"
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required={!editingStaff}
            />
          </div>

          {!editingStaff&&<fieldset className="space-y-2"><legend className="text-sm font-semibold">Chi nhánh được làm việc</legend>{branches.filter(b=>b.is_owner).map(b=><label key={b.tenant.id} className="flex min-h-11 items-center gap-3"><input type="checkbox" disabled={b.tenant.id===tenant?.id} checked={b.tenant.id===tenant?.id||branchIds.includes(b.tenant.id)} onChange={e=>setBranchIds(v=>e.target.checked?[...v,b.tenant.id]:v.filter(x=>x!==b.tenant.id))}/>{b.tenant.name}</label>)}</fieldset>}
          <div className="space-y-1.5">
            <Label htmlFor="stNotes">Chuyên môn / Ghi chú</Label>
            <Textarea
              id="stNotes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Chuyên viên điều trị mụn, massage cổ vai gáy..."
            />
          </div>

          {editingStaff && (
            <label className="flex cursor-pointer items-center gap-2 text-xs font-semibold">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="h-4 w-4 accent-primary"
              />
              <span>Tài khoản đang hoạt động (nhận lịch hẹn)</span>
            </label>
          )}

          <div className="flex justify-end gap-2">
            <Button type="submit" disabled={savingStaff}>
              {savingStaff ? "Đang lưu..." : "Lưu Kỹ thuật viên"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
