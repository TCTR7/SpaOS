"use client";

import * as React from "react";
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
  const draft = JSON.stringify([name, logoUrl, themeColor, openTime, closeTime, bufferMinutes]);
  useBranchGuard(!loading && !!baseline && draft !== baseline, saving);
  React.useEffect(() => {
    void (async () => {
      setLoading(true); setError(null);
      try {
        const t = await fetchTenantSettings();
        setBaseline(JSON.stringify([t.name, t.logo_url || "", t.theme_color || "#be185d", (t.open_time || "09:00:00").slice(0,5), (t.close_time || "20:00:00").slice(0,5), t.buffer_minutes]));
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
    if (saving || loading || !baseline) return;
    setSaving(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await updateTenantSettings({
        name: name.trim(),
        logo_url: logoUrl.trim() || null,
        ...(branding.configured ? {} : {theme_color: themeColor.trim() || null}),
        open_time: openTime.length === 5 ? `${openTime}:00` : openTime,
        close_time: closeTime.length === 5 ? `${closeTime}:00` : closeTime,
        buffer_minutes: bufferMinutes,
      });
      setBaseline(draft);
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
            Thông số chung của Spa
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
            <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
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
                <div className="space-y-1.5">
                  <Label htmlFor="logoUrl">Logo URL (Tùy chọn)</Label>
                  <Input
                    id="logoUrl"
                    placeholder="https://example.com/logo.png"
                    value={logoUrl}
                    onChange={(e) => setLogoUrl(e.target.value)}
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="themeColor">Màu chủ đạo (Theme Color)</Label>
                  {branding.configured && <p className="text-xs text-muted-foreground">Màu thương hiệu chung {branding.theme_color} do đơn vị triển khai quản lý.</p>}
                  <div className="flex items-center gap-2">
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
                  </div>
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
                <Button type="submit" disabled={saving || loading || !baseline}>
                  <Save className="h-4 w-4" />
                  {saving ? "Đang lưu cấu hình..." : "Lưu thay đổi"}
                </Button>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
