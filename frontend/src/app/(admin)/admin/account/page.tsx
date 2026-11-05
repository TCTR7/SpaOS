"use client";
import * as React from "react";
import { Camera, Trash2 } from "lucide-react";
import { CredentialForm } from "@/components/credential-form";
import { StaffAvatar } from "@/components/admin/staff-avatar";
import { ImageCropper } from "@/components/image-cropper";
import { useAdminAuth } from "@/components/admin/auth-context";
import { deleteStaffPhoto, uploadStaffPhoto } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function AccountPage(): React.ReactElement {
  const { user, refreshMe } = useAdminAuth();
  const fileInput = React.useRef<HTMLInputElement>(null);
  const [cropFile, setCropFile] = React.useState<File | null>(null);
  const [photoBusy, setPhotoBusy] = React.useState(false);
  const [photoMsg, setPhotoMsg] = React.useState<string | null>(null);
  const [photoError, setPhotoError] = React.useState<string | null>(null);

  const choosePhoto = (event: React.ChangeEvent<HTMLInputElement>): void => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setPhotoError("Vui lòng chọn một tệp ảnh.");
      return;
    }
    setPhotoError(null);
    setCropFile(file);
  };

  const savePhoto = async (data: string): Promise<void> => {
    setCropFile(null);
    if (!user || photoBusy) return;
    setPhotoBusy(true);
    setPhotoError(null);
    setPhotoMsg(null);
    try {
      await uploadStaffPhoto(user.id, data);
      await refreshMe();
      setPhotoMsg("Đã cập nhật ảnh đại diện.");
    } catch (err) {
      setPhotoError(err instanceof Error ? err.message : "Tải ảnh thất bại");
    } finally {
      setPhotoBusy(false);
    }
  };

  const removePhoto = async (): Promise<void> => {
    if (!user || photoBusy) return;
    setPhotoBusy(true);
    setPhotoError(null);
    setPhotoMsg(null);
    try {
      await deleteStaffPhoto(user.id);
      await refreshMe();
      setPhotoMsg("Đã xóa ảnh đại diện.");
    } catch (err) {
      setPhotoError(err instanceof Error ? err.message : "Xóa ảnh thất bại");
    } finally {
      setPhotoBusy(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-2xl space-y-4">
      <h1 className="text-xl font-bold">Tài khoản của tôi</h1>
      {user && (
        <>
          <Card>
            <CardContent className="flex flex-col items-center gap-4 p-5 sm:flex-row">
              <StaffAvatar name={user.full_name} src={user.photo_url} className="h-24 w-24 text-3xl" />
              <div className="min-w-0 flex-1 space-y-2 text-center sm:text-left">
                <p className="text-base font-bold text-foreground">{user.full_name}</p>
                <p className="text-xs text-muted-foreground">Ảnh đại diện hiển thị trên hồ sơ và khi khách hàng chọn Kỹ thuật viên.</p>
                {photoError && <p role="alert" className="text-xs font-medium text-rose-700">{photoError}</p>}
                {photoMsg && <p role="status" className="text-xs font-medium text-emerald-700">{photoMsg}</p>}
                <div className="flex flex-wrap justify-center gap-2 sm:justify-start">
                  <input ref={fileInput} type="file" accept="image/*" className="sr-only" aria-label="Chọn ảnh đại diện" onChange={choosePhoto} />
                  <ImageCropper file={cropFile} title="Chỉnh ảnh đại diện" round format="jpeg" outputSize={600} onCancel={() => setCropFile(null)} onConfirm={(data) => void savePhoto(data)} />
                  <Button type="button" variant="outline" size="sm" disabled={photoBusy} onClick={() => fileInput.current?.click()}>
                    <Camera className="h-4 w-4" />
                    {photoBusy ? "Đang xử lý..." : user.photo_url ? "Đổi ảnh đại diện" : "Tải ảnh đại diện"}
                  </Button>
                  {user.photo_url && (
                    <Button type="button" variant="outline" size="sm" className="text-rose-600" disabled={photoBusy} onClick={() => void removePhoto()}>
                      <Trash2 className="h-4 w-4" />
                      Xóa ảnh
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
          <CredentialForm key={user.id} phone={user.phone_number} onSaved={() => void refreshMe()} />
        </>
      )}
    </div>
  );
}
