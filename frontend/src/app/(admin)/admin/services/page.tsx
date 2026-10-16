"use client";

import * as React from "react";
import { Edit2, Plus, Sparkles, Trash2 } from "lucide-react";
import {
  createService,
  deleteService,
  fetchServices,
  updateService,
} from "@/lib/api";
import type { ServiceItem } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";
import { useAdminAuth } from "@/components/admin/auth-context";
import { Button } from "@/components/ui/button";
import { Badge, Card, CardContent } from "@/components/ui/card";
import { Input, Label, Textarea } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";

export default function AdminServicesPage(): React.ReactElement {
  const { user } = useAdminAuth();
  const isAdmin = user?.role === "ADMIN";

  const [services, setServices] = React.useState<ServiceItem[]>([]);
  const [loading, setLoading] = React.useState<boolean>(true);
  const [error, setError] = React.useState<string | null>(null);
  const [infoMessage, setInfoMessage] = React.useState<string | null>(null);

  // Modal state
  const [modalOpen, setModalOpen] = React.useState<boolean>(false);
  const [editing, setEditing] = React.useState<ServiceItem | null>(null);
  const [name, setName] = React.useState<string>("");
  const [description, setDescription] = React.useState<string>("");
  const [durationMinutes, setDurationMinutes] = React.useState<number>(60);
  const [price, setPrice] = React.useState<number>(350000);
  const [isPackage, setIsPackage] = React.useState<boolean>(false);
  const [totalSessions, setTotalSessions] = React.useState<number>(1);
  const [isActive, setIsActive] = React.useState<boolean>(true);
  const [saving, setSaving] = React.useState<boolean>(false);

  const loadServices = React.useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchServices();
      setServices(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể tải dịch vụ");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadServices();
  }, [loadServices]);

  const openCreateModal = (): void => {
    setEditing(null);
    setName("");
    setDescription("");
    setDurationMinutes(60);
    setPrice(350000);
    setIsPackage(false);
    setTotalSessions(1);
    setIsActive(true);
    setModalOpen(true);
  };

  const openEditModal = (svc: ServiceItem): void => {
    setEditing(svc);
    setName(svc.name);
    setDescription(svc.description || "");
    setDurationMinutes(svc.duration_minutes);
    setPrice(parseFloat(svc.price));
    setIsPackage(svc.is_package);
    setTotalSessions(svc.total_sessions);
    setIsActive(svc.is_active);
    setModalOpen(true);
  };

  const handleSave = async (
    e: React.FormEvent<HTMLFormElement>
  ): Promise<void> => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setInfoMessage(null);
    try {
      const payload = {
        name: name.trim(),
        description: description.trim() || null,
        duration_minutes: durationMinutes,
        price,
        is_package: isPackage,
        total_sessions: isPackage ? Math.max(2, totalSessions) : 1,
        is_active: isActive,
      };
      if (editing) {
        const updated = await updateService(editing.id, payload);
        setServices((prev) =>
          prev.map((s) => (s.id === updated.id ? updated : s))
        );
      } else {
        const created = await createService(payload);
        setServices((prev) => [created, ...prev]);
      }
      setModalOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lưu dịch vụ thất bại");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (svc: ServiceItem): Promise<void> => {
    setError(null);
    setInfoMessage(null);
    try {
      const res = await deleteService(svc.id);
      if (res.mode === "soft") {
        setInfoMessage(
          `Dịch vụ "${svc.name}" đã phát sinh lịch hẹn/thẻ nên được chuyển sang Ngưng hoạt động (Soft-delete).`
        );
      } else {
        setInfoMessage(`Đã xóa vĩnh viễn dịch vụ "${svc.name}".`);
      }
      await loadServices();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Xóa dịch vụ thất bại");
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">
            Danh mục Dịch vụ & Gói Liệu trình
          </h1>
          <p className="text-xs text-muted-foreground">
            Cấu hình dịch vụ lẻ (1 buổi) và gói thẻ liệu trình nhiều buổi cho
            Spa
          </p>
        </div>
        {isAdmin && (
          <Button size="sm" onClick={openCreateModal}>
            <Plus className="h-4 w-4" />
            Thêm dịch vụ mới
          </Button>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-rose-300 bg-rose-50 px-4 py-2.5 text-xs font-medium text-rose-700">
          {error}
        </div>
      )}

      {infoMessage && (
        <div className="rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-2.5 text-xs font-medium text-emerald-800">
          {infoMessage}
        </div>
      )}

      {loading ? (
        <Card>
          <CardContent className="p-10 text-center text-sm text-muted-foreground">
            Đang tải danh mục dịch vụ...
          </CardContent>
        </Card>
      ) : services.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <Sparkles className="h-8 w-8 text-muted-foreground" />
            <p className="mt-2 text-sm font-medium">Chưa có dịch vụ nào</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-border bg-muted/60 text-[11px] font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Tên dịch vụ</th>
                  <th className="px-4 py-3">Phân loại</th>
                  <th className="px-4 py-3">Thời lượng</th>
                  <th className="px-4 py-3">Đơn giá</th>
                  <th className="px-4 py-3">Trạng thái</th>
                  {isAdmin && (
                    <th className="px-4 py-3 text-right">Thao tác</th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {services.map((svc) => (
                  <tr key={svc.id} className="hover:bg-muted/30">
                    <td className="px-4 py-3">
                      <p className="font-semibold text-foreground text-sm">
                        {svc.name}
                      </p>
                      {svc.description && (
                        <p className="text-muted-foreground line-clamp-1">
                          {svc.description}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {svc.is_package ? (
                        <Badge variant="default">
                          Gói liệu trình ({svc.total_sessions} buổi)
                        </Badge>
                      ) : (
                        <Badge variant="secondary">Dịch vụ lẻ (1 buổi)</Badge>
                      )}
                    </td>
                    <td className="px-4 py-3 font-medium">
                      {svc.duration_minutes} phút
                    </td>
                    <td className="px-4 py-3 font-bold text-foreground">
                      {formatCurrency(svc.price)}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={svc.is_active ? "success" : "outline"}>
                        {svc.is_active ? "Đang hoạt động" : "Tạm ngưng"}
                      </Badge>
                    </td>
                    {isAdmin && (
                      <td className="px-4 py-3 text-right">
                        <div className="inline-flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => openEditModal(svc)}
                            title="Chỉnh sửa"
                          >
                            <Edit2 className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-rose-600 hover:text-rose-700"
                            onClick={() => void handleDelete(svc)}
                            title="Xóa / Ngưng dịch vụ"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? "Chỉnh sửa Dịch vụ" : "Thêm Dịch vụ / Gói liệu trình"}
      >
        <form onSubmit={(e) => void handleSave(e)} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="svcName">Tên dịch vụ</Label>
            <Input
              id="svcName"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="VD: Chăm sóc da chuyên sâu / Liệu trình trị mụn 10 buổi"
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="svcDesc">Mô tả chi tiết</Label>
            <Textarea
              id="svcDesc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Quy trình các bước thực hiện..."
            />
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="svcDuration">Thời lượng 1 buổi (phút)</Label>
              <Input
                id="svcDuration"
                type="number"
                min={5}
                max={480}
                value={durationMinutes}
                onChange={(e) =>
                  setDurationMinutes(parseInt(e.target.value || "30", 10))
                }
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="svcPrice">Giá niêm yết (VNĐ)</Label>
              <Input
                id="svcPrice"
                type="number"
                min={0}
                step={1000}
                value={price}
                onChange={(e) =>
                  setPrice(parseFloat(e.target.value || "0"))
                }
                required
              />
            </div>
          </div>

          <div className="rounded-lg border border-border bg-muted/30 p-3 space-y-3">
            <label className="flex cursor-pointer items-center gap-2 text-xs font-semibold">
              <input
                type="checkbox"
                checked={isPackage}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setIsPackage(checked);
                  setTotalSessions(checked ? Math.max(2, totalSessions) : 1);
                }}
                className="h-4 w-4 accent-primary"
              />
              <span>Đây là Gói thẻ liệu trình nhiều buổi (is_package)</span>
            </label>

            {isPackage && (
              <div className="space-y-1.5">
                <Label htmlFor="svcSessions">Tổng số buổi trong gói</Label>
                <Input
                  id="svcSessions"
                  type="number"
                  min={2}
                  max={200}
                  value={totalSessions}
                  onChange={(e) =>
                    setTotalSessions(parseInt(e.target.value || "2", 10))
                  }
                  required
                />
              </div>
            )}
          </div>

          <label className="flex cursor-pointer items-center gap-2 text-xs font-semibold">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="h-4 w-4 accent-primary"
            />
            <span>Đang mở bán & hiển thị trên trang Đặt lịch của khách</span>
          </label>

          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setModalOpen(false)}
            >
              Hủy
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Đang lưu..." : "Lưu dịch vụ"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
