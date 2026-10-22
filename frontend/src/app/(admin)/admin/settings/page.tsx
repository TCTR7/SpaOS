"use client";

import * as React from "react";
import { SpaLogo } from "@/components/spa-logo";
import { useBranchGuard } from "@/lib/branch-guard";
import { useBranding } from "@/components/brand-provider";
import { Save, Settings as SettingsIcon } from "lucide-react";
import { fetchTenantSettings, updateTenantSettings } from "@/lib/api";
import { useAdminAuth } from "@/components/admin/auth-context";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";

export default function AdminSettingsPage(): React.ReactElement {
  const {branding} = useBranding();
  const { refreshMe } = useAdminAuth();

  const [slug, setSlug] = React.useState<string>("");
  const [name, setName] = React.useState<string>("");
  const [address, setAddress] = React.useState("");
  const [contactPhone, setContactPhone] = React.useState("");
  const [logoData, setLogoData] = React.useState("");
  const fileChoice = React.useRef(0);
  const [readingLogo, setReadingLogo] = React.useState(false);
  const [logoUrl, setLogoUrl] = React.useState<string>("");
  const [themeColor, setThemeColor] = React.useState<string>("#be185d");
  const [openTime, setOpenTime] = React.useState<string>("09:00");
  const [closeTime, setCloseTime] = React.useState<string>("20:00");
  const [bufferMinutes, setBufferMinutes] = React.useState<number>(10);

  const [loading, setLoading] = React.useState<boolean>(true);
  const [saving, setSaving] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string | null>(null);
  const [successMsg, setSuccessMsg] = React.useState<string | null>(null);

  const [attempt, setAttempt] = React.useState(0);
  const [baseline, setBaseline] = React.useState("");
  const draft = JSON.stringify([name, logoUrl, themeColor, openTime, closeTime, bufferMinutes, address, contactPhone]);
  useBranchGuard(!loading && !!baseline && (draft !== baseline || !!logoData), saving || readingLogo);
  React.useEffect(() => {
    void (async () => {
      setLoading(true); setError(null);
      try {
        const t = await fetchTenantSettings();
        setBaseline(JSON.stringify([t.name, t.logo_url || "", t.theme_color || "#be185d", (t.open_time || "09:00:00").slice(0,5), (t.close_time || "20:00:00").slice(0,5), t.buffer_minutes, t.address || "", t.contact_phone || ""]));
        setAddress(t.address || ""); setContactPhone(t.contact_phone || ""); setLogoData("");
        setSlug(t.slug);
        setName(t.name);
        setLogoUrl(t.logo_url || "");
        setThemeColor(t.theme_color || "#be185d");
        setOpenTime((t.open_time || "09:00:00").slice(0, 5));
        setCloseTime((t.close_time || "20:00:00").slice(0, 5));
        setBufferMinutes(t.buffer_minutes);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Không thể tải cấu hình Spa"
        );
      } finally {
        setLoading(false);
      }
    })();
  }, [attempt]);

  const handleSubmit = async (
    e: React.FormEvent<HTMLFormElement>
  ): Promise<void> => {
    e.preventDefault();
    if (saving || readingLogo || loading || !baseline) return;
    setSaving(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const updated = await updateTenantSettings({
        address: address.trim() || null, contact_phone: contactPhone.trim() || null,
        ...(logoData ? { logo_data: logoData } : {}),
        name: name.trim(),
        logo_url: logoUrl.trim() || null,
        ...(branding.configured ? {} : {theme_color: themeColor.trim() || null}),
        open_time: openTime.length === 5 ? `${openTime}:00` : openTime,
        close_time: closeTime.length === 5 ? `${closeTime}:00` : closeTime,
        buffer_minutes: bufferMinutes,
      });
      setLogoUrl(updated.logo_url || ""); setLogoData("");
      setBaseline(JSON.stringify([name, updated.logo_url || "", themeColor, openTime, closeTime, bufferMinutes, address, contactPhone]));
      await refreshMe();
      setSuccessMsg("Đã lưu cấu hình Spa thành công!");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Cập nhật cấu hình thất bại"
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto min-w-0 max-w-2xl space-y-5 [overflow-wrap:anywhere]">
      <div>
        <h1 className="text-xl font-bold text-foreground">
          Cài đặt spa
        </h1>
        <p className="text-xs text-muted-foreground">
          Thiết lập thông tin spa, giờ mở cửa và thời gian chuẩn bị giữa hai lịch hẹn.
        </p>
      </div>

      {error && (
        <div role="alert" className="rounded-lg border border-rose-300 bg-rose-50 px-4 py-2.5 text-xs font-medium text-rose-700">
          <p>{error}</p>{!baseline && <Button type="button" variant="outline" onClick={() => setAttempt((v) => v+1)}>Thử tải lại cấu hình</Button>}
        </div>
      )}

      {successMsg && (
        <div className="rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-2.5 text-xs font-medium text-emerald-800">
          {successMsg}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <SettingsIcon className="h-4 w-4 text-primary" />
            Thương hiệu & thông tin spa
          </CardTitle>
          <CardDescription>
            Đường dẫn đặt lịch công khai cho khách hàng:{" "}
            <code className="font-semibold text-primary">/{slug}</code>
          </CardDescription>
        </CardHeader>

        <CardContent>
          {loading ? (
            <p className="py-8 text-center text-xs text-muted-foreground">
              Đang tải thông tin cấu hình...
            </p>
          ) : (
            <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4"><fieldset disabled={saving || readingLogo} className="space-y-4 border-0 p-0">
              <div className="space-y-1.5">
                <Label htmlFor="spaName">Tên hiển thị của Spa</Label>
                <Input
                  id="spaName"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div><Label htmlFor="branchAddress">Địa chỉ chi nhánh</Label><Input id="branchAddress" maxLength={500} value={address} onChange={(event) => setAddress(event.target.value)} /></div>
                <div><Label htmlFor="branchContact">Số điện thoại liên hệ</Label><Input id="branchContact" type="tel" value={contactPhone} onChange={(event) => setContactPhone(event.target.value)} /></div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="logoFile">Tải ảnh logo từ thiết bị</Label>
                <Input id="logoFile" type="file" accept="image/png" onChange={async (event) => {
                  const file = event.target.files?.[0]; if (!file) return;
                  const choice = ++fileChoice.current;
                  if (file.type !== "image/png" || file.size > 262144) { setError("Chọn ảnh PNG tối đa 256 KB, kích thước tối đa 2048 × 2048."); return; }
                  setReadingLogo(true);
                  const reader = new FileReader();
                  reader.onload = () => { if (choice === fileChoice.current && typeof reader.result === "string") { setLogoData(reader.result.split(",")[1]); setError(null); } };
                  reader.onloadend = () => { if (choice === fileChoice.current) setReadingLogo(false); };
                  reader.onerror = () => setError("Chưa đọc được ảnh. Hãy chọn lại."); reader.readAsDataURL(file);
                }} />
                <p className="text-xs text-muted-foreground">Ảnh PNG tối đa 256 KB và 2048 × 2048. Ảnh chỉ được lưu khi bạn nhấn Lưu.</p>
                <div className="flex items-center gap-4 rounded-2xl border bg-muted/30 p-4">
                  <SpaLogo name={name || "Tên spa của bạn"} src={logoData ? "data:image/png;base64," + logoData : logoUrl} alt="Xem trước logo chi nhánh" className="h-20 w-20" />
                  <div className="min-w-0"><p className="text-xs text-muted-foreground">Khách hàng sẽ nhìn thấy</p><p className="mt-1 text-xl font-bold [overflow-wrap:anywhere]">{name || "Tên spa của bạn"}</p><p className="mt-1 text-xs text-muted-foreground">Logo và tên trên trang dịch vụ, đặt lịch và hồ sơ khách.</p></div>
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="logoUrl">Đường dẫn ảnh logo (không bắt buộc)</Label>
                  <Input
                    id="logoUrl"
                    placeholder="https://example.com/logo.png"
                    value={logoUrl}
                    onChange={(e) => setLogoUrl(e.target.value)}
                  />
                </div>

                <div className="space-y-1.5">
                  {branding.configured ? <p className="text-sm font-medium">Màu thương hiệu</p> : <Label htmlFor="themeColor">Màu thương hiệu</Label>}

                  {branding.configured ? <p className="flex min-h-11 items-center gap-2 text-sm"><span className="inline-block h-6 w-6 rounded border" style={{ backgroundColor: branding.theme_color }} />Màu thương hiệu đã được thiết lập chung. Liên hệ đơn vị triển khai nếu cần đổi.</p> : <div className="flex items-center gap-2">
                    <input
                      type="color" disabled={branding.configured}
                      value={branding.configured ? branding.theme_color : themeColor}
                      onChange={(e) => setThemeColor(e.target.value)}
                      className="h-9 w-12 cursor-pointer rounded border border-input bg-background p-0.5"
                    />
                    <Input
                      id="themeColor" disabled={branding.configured}
                      value={branding.configured ? branding.theme_color : themeColor}
                      onChange={(e) => setThemeColor(e.target.value)}
                      placeholder="#be185d"
                    />
                  </div>}
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                <div className="space-y-1.5">
                  <Label htmlFor="openTime">Giờ mở cửa</Label>
                  <Input
                    id="openTime"
                    type="time"
                    value={openTime}
                    onChange={(e) => setOpenTime(e.target.value)}
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="closeTime">Giờ đóng cửa</Label>
                  <Input
                    id="closeTime"
                    type="time"
                    value={closeTime}
                    onChange={(e) => setCloseTime(e.target.value)}
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="bufferMinutes">
                    Thời gian chuẩn bị giữa hai lịch hẹn (phút)
                  </Label>
                  <Input
                    id="bufferMinutes"
                    type="number"
                    min={0}
                    max={180}
                    value={bufferMinutes}
                    onChange={(e) =>
                      setBufferMinutes(parseInt(e.target.value || "0", 10))
                    }
                    required
                  />
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <Button type="submit" disabled={saving || readingLogo || loading || !baseline}>
                  <Save className="h-4 w-4" />
                  {saving ? "Đang lưu cấu hình..." : "Lưu thay đổi"}
                </Button>
              </div>
            </fieldset></form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
