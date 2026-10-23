"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Camera, Save, Trash2 } from "lucide-react";
import { StaffAvatar } from "@/components/admin/staff-avatar";
import { useAdminAuth } from "@/components/admin/auth-context";
import { Button } from "@/components/ui/button";
import { Badge, Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label, Textarea } from "@/components/ui/input";
import { deleteStaffPhoto, fetchServices, fetchStaffList, replaceStaffSkills, updateStaff, uploadStaffPhoto } from "@/lib/api";
import { useBranchGuard } from "@/lib/branch-guard";
import { ImageCropper } from "@/components/image-cropper";
import type { ServiceItem, UserDetail } from "@/lib/types";

interface Draft { jobTitle: string; bio: string; years: string; detail: string; skills: string[] }

function toDraft(staff: UserDetail): Draft {
  return {
    jobTitle: staff.job_title || "", bio: staff.bio || "",
    years: staff.experience_years === null || staff.experience_years === undefined ? "" : String(staff.experience_years),
    detail: staff.experience_detail || "", skills: [...(staff.skill_service_ids || [])].sort(),
  };
}

export default function StaffProfilePage(): React.ReactElement {
  const { user } = useAdminAuth();
  const params = useParams<{ id: string }>();
  const staffId = params.id;
  const [staff, setStaff] = React.useState<UserDetail | null>(null);
  const [services, setServices] = React.useState<ServiceItem[]>([]);
  const [draft, setDraft] = React.useState<Draft | null>(null);
  const [baseline, setBaseline] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [photoBusy, setPhotoBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [message, setMessage] = React.useState<string | null>(null);
  const fileInput = React.useRef<HTMLInputElement>(null);
  const [cropFile, setCropFile] = React.useState<File | null>(null);

  const load = React.useCallback(async (): Promise<void> => {
    setLoading(true); setError(null);
    try {
      const [list, serviceList] = await Promise.all([fetchStaffList(), fetchServices()]);
      const found = list.find((row) => row.id === staffId) || null;
      setServices(serviceList); setStaff(found);
      if (found) { const next = toDraft(found); setDraft(next); setBaseline(JSON.stringify(next)); }
      else setError("Không tìm thấy nhân viên này trong chi nhánh đang chọn.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được hồ sơ nhân viên");
    } finally { setLoading(false); }
  }, [staffId]);

  React.useEffect(() => { if (user?.role === "ADMIN") void load(); }, [load, user?.role]);
  const dirty = !!draft && JSON.stringify(draft) !== baseline;
  useBranchGuard(dirty, saving || photoBusy);

  if (user?.role !== "ADMIN") return <p>Chỉ quản trị viên được chỉnh hồ sơ nhân viên.</p>;
  const patch = (change: Partial<Draft>): void => { setDraft((current) => (current ? { ...current, ...change } : current)); setMessage(null); };
  const toggleSkill = (id: string): void => {
    if (!draft) return;
    patch({ skills: (draft.skills.includes(id) ? draft.skills.filter((value) => value !== id) : [...draft.skills, id]).sort() });
  };

  const save = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    if (!staff || !draft || saving) return;
    const years = draft.years.trim() === "" ? null : Number(draft.years);
    if (years !== null && (!Number.isInteger(years) || years < 0 || years > 60)) { setError("Số năm kinh nghiệm phải là số nguyên từ 0 đến 60."); return; }
    setSaving(true); setError(null); setMessage(null);
    try {
      await updateStaff(staff.id, {
        job_title: draft.jobTitle.trim() || null, bio: draft.bio.trim() || null,
        experience_years: years, experience_detail: draft.detail.trim() || null,
      });
      const updated = await replaceStaffSkills(staff.id, draft.skills);
      setStaff(updated); const next = toDraft(updated); setDraft(next); setBaseline(JSON.stringify(next));
      setMessage("Đã lưu hồ sơ nhân viên.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lưu hồ sơ thất bại");
    } finally { setSaving(false); }
  };

  const choosePhoto = (event: React.ChangeEvent<HTMLInputElement>): void => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (!file.type.startsWith("image/")) { setError("Vui lòng chọn một tệp ảnh."); return; }
    setError(null); setCropFile(file);
  };

  const savePhoto = async (data: string): Promise<void> => {
    setCropFile(null);
    if (!staff || photoBusy) return;
    setPhotoBusy(true); setError(null); setMessage(null);
    try {
      const updated = await uploadStaffPhoto(staff.id, data);
      setStaff((current) => (current ? { ...current, photo_url: updated.photo_url } : current));
      setMessage("Đã cập nhật ảnh nhân viên.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Tải ảnh thất bại");
    } finally { setPhotoBusy(false); }
  };

  const removePhoto = async (): Promise<void> => {
    if (!staff || photoBusy) return;
    setPhotoBusy(true); setError(null); setMessage(null);
    try {
      await deleteStaffPhoto(staff.id);
      setStaff((current) => (current ? { ...current, photo_url: null } : current));
      setMessage("Đã xóa ảnh nhân viên.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Xóa ảnh thất bại");
    } finally { setPhotoBusy(false); }
  };

  return (
    <div className="mx-auto min-w-0 max-w-3xl space-y-5 [overflow-wrap:anywhere]">
      <Link href="/admin/staff" className="inline-flex min-h-11 items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" />Danh sách nhân sự
      </Link>
      {error && <div role="alert" className="rounded-lg border border-rose-300 bg-rose-50 px-4 py-2.5 text-sm font-medium text-rose-700">{error}</div>}
      {message && <div role="status" className="rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-2.5 text-sm font-medium text-emerald-800">{message}</div>}
      {loading && <p role="status" className="py-8 text-center text-sm text-muted-foreground">Đang tải hồ sơ...</p>}
      {!loading && !staff && <Button variant="outline" onClick={() => void load()}>Thử tải lại</Button>}
      {staff && draft && (
        <form onSubmit={(event) => void save(event)} className="space-y-5">
          <Card>
            <CardContent className="flex flex-col items-center gap-4 p-5 sm:flex-row sm:items-center">
              <StaffAvatar name={staff.full_name} src={staff.photo_url} className="h-28 w-28 text-4xl" />
              <div className="min-w-0 flex-1 space-y-2 text-center sm:text-left">
                <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
                  <h1 className="text-xl font-bold">{staff.full_name}</h1>
                  <Badge variant={staff.is_active ? "success" : "outline"}>{staff.is_active ? "Đang làm việc" : "Ngưng làm việc"}</Badge>
                </div>
                <p className="text-sm text-muted-foreground">SĐT: {staff.phone_number}</p>
                <div className="flex flex-wrap justify-center gap-2 sm:justify-start">
                  <input ref={fileInput} type="file" accept="image/*" className="sr-only" aria-label="Chọn ảnh nhân viên" onChange={choosePhoto} />
                  <ImageCropper file={cropFile} title="Chỉnh ảnh nhân viên" round format="jpeg" outputSize={600} onCancel={() => setCropFile(null)} onConfirm={(data) => void savePhoto(data)} />
                  <Button type="button" variant="outline" disabled={photoBusy} onClick={() => fileInput.current?.click()}>
                    <Camera className="h-4 w-4" />{photoBusy ? "Đang xử lý..." : staff.photo_url ? "Đổi ảnh" : "Tải ảnh lên"}
                  </Button>
                  {staff.photo_url && <Button type="button" variant="outline" className="text-rose-600" disabled={photoBusy} onClick={() => void removePhoto()}><Trash2 className="h-4 w-4" />Xóa ảnh</Button>}
                </div>
                <p className="text-xs text-muted-foreground">Chọn ảnh bất kỳ, không giới hạn dung lượng; kéo và phóng to để căn vào khung tròn. Ảnh được lưu ngay khi bạn bấm Dùng ảnh này.</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Thông tin &amp; kinh nghiệm</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="space-y-1.5 sm:col-span-2">
                  <Label htmlFor="jobTitle">Chức danh</Label>
                  <Input id="jobTitle" maxLength={100} value={draft.jobTitle} onChange={(e) => patch({ jobTitle: e.target.value })} placeholder="VD: Chuyên viên chăm sóc da" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="expYears">Số năm kinh nghiệm</Label>
                  <Input id="expYears" inputMode="numeric" value={draft.years} onChange={(e) => patch({ years: e.target.value.replace(/[^0-9]/g, "").slice(0, 2) })} placeholder="VD: 5" />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="staffBio">Giới thiệu ngắn</Label>
                <Textarea id="staffBio" maxLength={2000} value={draft.bio} onChange={(e) => patch({ bio: e.target.value })} placeholder="Phong cách làm việc, điểm mạnh..." />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="expDetail">Quá trình làm việc, chứng chỉ</Label>
                <Textarea id="expDetail" maxLength={4000} className="min-h-[120px]" value={draft.detail} onChange={(e) => patch({ detail: e.target.value })} placeholder="Nơi từng làm, khóa đào tạo, chứng chỉ..." />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Kỹ năng (dịch vụ thực hiện được)</CardTitle>
              <CardDescription>Khi tạo lịch hẹn, chỉ nhân viên có kỹ năng khớp dịch vụ được đề xuất. Nhân viên chưa chọn kỹ năng nào vẫn được xếp lịch như trước và hiển thị ở mục riêng.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {services.length === 0 && <p className="text-sm text-muted-foreground">Chưa có dịch vụ. <Link className="underline" href="/admin/services">Tạo danh mục dịch vụ</Link> trước.</p>}
              {services.map((service) => (
                <label key={service.id} className="flex min-h-11 cursor-pointer items-start gap-3 rounded-lg border border-border px-3 py-2 text-sm hover:bg-muted/40">
                  <input type="checkbox" className="mt-0.5 h-5 w-5 shrink-0 accent-primary" checked={draft.skills.includes(service.id)} onChange={() => toggleSkill(service.id)} />
                  <span className="min-w-0">
                    <span className="font-medium">{service.name}</span>
                    <span className="block text-xs text-muted-foreground">
                      {service.is_package ? `Gói ${service.total_sessions} buổi` : "Dịch vụ lẻ"} · {service.duration_minutes} phút{service.is_active ? "" : " · Tạm ngưng"}
                    </span>
                  </span>
                </label>
              ))}
            </CardContent>
          </Card>

          <div className="sticky bottom-[calc(5rem+env(safe-area-inset-bottom))] z-20 flex justify-end md:bottom-4">
            <Button type="submit" disabled={saving || !dirty} className="shadow-lg"><Save className="h-4 w-4" />{saving ? "Đang lưu..." : "Lưu hồ sơ"}</Button>
          </div>
        </form>
      )}
    </div>
  );
}
