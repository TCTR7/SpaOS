"use client";

import * as React from "react";
import {
  Edit2,
  PackagePlus,
  Plus,
  Search,
  Ticket,
  User as UserIcon,
} from "lucide-react";
import {
  createCustomer,
  fetchCustomerPackages,
  fetchCustomers,
  fetchServices,
  issueCustomerPackage,
  updateCustomer,
} from "@/lib/api";
import type {
  CustomerPackageItem,
  ServiceItem,
  UserDetail,
} from "@/lib/types";
import { cn, formatCurrency, formatDateTimeVN } from "@/lib/utils";
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

export default function AdminCustomersPage(): React.ReactElement {
  const [customers, setCustomers] = React.useState<UserDetail[]>([]);
  const [packageServices, setPackageServices] = React.useState<ServiceItem[]>(
    []
  );
  const [searchQuery, setSearchQuery] = React.useState<string>("");
  const [selectedCustomer, setSelectedCustomer] =
    React.useState<UserDetail | null>(null);
  const [packages, setPackages] = React.useState<CustomerPackageItem[]>([]);
  const [loading, setLoading] = React.useState<boolean>(true);
  const [packagesLoading, setPackagesLoading] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string | null>(null);

  // Create / Edit Customer Modal
  const [customerModalOpen, setCustomerModalOpen] =
    React.useState<boolean>(false);
  const [editingCustomer, setEditingCustomer] =
    React.useState<UserDetail | null>(null);
  const [fullName, setFullName] = React.useState<string>("");
  const [phoneNumber, setPhoneNumber] = React.useState<string>("");
  const [notes, setNotes] = React.useState<string>("");
  const [password, setPassword] = React.useState<string>("");
  const [savingCustomer, setSavingCustomer] = React.useState<boolean>(false);

  // Issue Package Modal
  const [pkgModalOpen, setPkgModalOpen] = React.useState<boolean>(false);
  const [pkgServiceId, setPkgServiceId] = React.useState<string>("");
  const [pkgName, setPkgName] = React.useState<string>("");
  const [pkgSessions, setPkgSessions] = React.useState<number>(10);
  const [pkgExpiry, setPkgExpiry] = React.useState<string>("");
  const [savingPackage, setSavingPackage] = React.useState<boolean>(false);

  const loadCustomers = React.useCallback(
    async (q?: string): Promise<void> => {
      setLoading(true);
      setError(null);
      try {
        const list = await fetchCustomers({ q: q ?? searchQuery, limit: 100 });
        setCustomers(list);
        if (list.length > 0 && !selectedCustomer) {
          setSelectedCustomer(list[0]);
        }
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Không thể tải danh sách khách hàng"
        );
      } finally {
        setLoading(false);
      }
    },
    [searchQuery, selectedCustomer]
  );

  const loadPackageServices = React.useCallback(async (): Promise<void> => {
    try {
      const svcs = await fetchServices({ is_active: true, is_package: true });
      setPackageServices(svcs);
    } catch {
      // ignore
    }
  }, []);

  const loadSelectedCustomerPackages = React.useCallback(
    async (customerId: string): Promise<void> => {
      setPackagesLoading(true);
      try {
        const list = await fetchCustomerPackages(customerId);
        setPackages(list);
      } catch {
        setPackages([]);
      } finally {
        setPackagesLoading(false);
      }
    },
    []
  );

  React.useEffect(() => {
    void loadCustomers("");
    void loadPackageServices();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  React.useEffect(() => {
    if (selectedCustomer) {
      void loadSelectedCustomerPackages(selectedCustomer.id);
    } else {
      setPackages([]);
    }
  }, [selectedCustomer, loadSelectedCustomerPackages]);

  const openAddCustomer = (): void => {
    setEditingCustomer(null);
    setFullName("");
    setPhoneNumber("");
    setNotes("");
    setPassword("");
    setCustomerModalOpen(true);
  };

  const openEditCustomer = (c: UserDetail): void => {
    setEditingCustomer(c);
    setFullName(c.full_name);
    setPhoneNumber(c.phone_number);
    setNotes(c.notes || "");
    setPassword("");
    setCustomerModalOpen(true);
  };

  const handleSaveCustomer = async (
    e: React.FormEvent<HTMLFormElement>
  ): Promise<void> => {
    e.preventDefault();
    setSavingCustomer(true);
    setError(null);
    try {
      if (editingCustomer) {
        const updated = await updateCustomer(editingCustomer.id, {
          full_name: fullName.trim(),
          notes: notes.trim() || null,
        });
        setCustomers((prev) =>
          prev.map((c) => (c.id === updated.id ? updated : c))
        );
        if (selectedCustomer?.id === updated.id) {
          setSelectedCustomer(updated);
        }
      } else {
        const created = await createCustomer({
          full_name: fullName.trim(),
          phone_number: phoneNumber.trim(),
          notes: notes.trim() || null,
          password: password.trim() || undefined,
        });
        setCustomers((prev) => [created, ...prev]);
        setSelectedCustomer(created);
      }
      setCustomerModalOpen(false);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Lưu thông tin khách hàng thất bại"
      );
    } finally {
      setSavingCustomer(false);
    }
  };

  const openIssuePackageModal = (): void => {
    const firstPkg = packageServices[0];
    setPkgServiceId(firstPkg?.id || "");
    setPkgName(firstPkg?.name || "");
    setPkgSessions(firstPkg?.total_sessions || 10);
    setPkgExpiry("");
    setPkgModalOpen(true);
  };

  const handleIssuePackage = async (
    e: React.FormEvent<HTMLFormElement>
  ): Promise<void> => {
    e.preventDefault();
    if (!selectedCustomer || !pkgServiceId) return;
    setSavingPackage(true);
    setError(null);
    try {
      const expiryISO = pkgExpiry
        ? new Date(`${pkgExpiry}T23:59:59+07:00`).toISOString()
        : null;
      await issueCustomerPackage({
        customer_id: selectedCustomer.id,
        service_id: pkgServiceId,
        package_name: pkgName.trim() || undefined,
        total_sessions: pkgSessions,
        expiry_date: expiryISO,
      });
      setPkgModalOpen(false);
      await loadSelectedCustomerPackages(selectedCustomer.id);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Cấp thẻ liệu trình thất bại"
      );
    } finally {
      setSavingPackage(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">
            Khách hàng & Quản lý Thẻ Liệu trình (CRM)
          </h1>
          <p className="text-xs text-muted-foreground">
            Tra cứu hồ sơ tình trạng da, lịch sử thẻ liệu trình và cấp gói liệu
            trình mới cho khách
          </p>
        </div>
        <Button size="sm" onClick={openAddCustomer}>
          <Plus className="h-4 w-4" />
          Thêm khách hàng mới
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-300 bg-rose-50 px-4 py-2.5 text-xs font-medium text-rose-700">
          {error}
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-12">
        {/* Left column: Customer Search & List */}
        <Card className="lg:col-span-5">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Danh sách Khách hàng</CardTitle>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void loadCustomers(searchQuery);
              }}
              className="mt-2 flex gap-2"
            >
              <div className="relative flex-1">
                <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Tìm theo Tên hoặc Số điện thoại..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Button type="submit" variant="secondary" size="sm">
                Tìm
              </Button>
            </form>
          </CardHeader>
          <CardContent className="max-h-[540px] overflow-y-auto divide-y divide-border pt-0">
            {loading ? (
              <p className="py-8 text-center text-xs text-muted-foreground">
                Đang tải khách hàng...
              </p>
            ) : customers.length === 0 ? (
              <p className="py-8 text-center text-xs text-muted-foreground">
                Không tìm thấy khách hàng nào.
              </p>
            ) : (
              customers.map((c) => {
                const isSelected = selectedCustomer?.id === c.id;
                return (
                  <div
                    key={c.id}
                    onClick={() => setSelectedCustomer(c)}
                    className={cn(
                      "flex cursor-pointer items-center justify-between gap-2 rounded-lg px-3 py-3 transition",
                      isSelected
                        ? "bg-primary/10 font-medium"
                        : "hover:bg-muted/60"
                    )}
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-foreground">
                        {c.full_name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        SĐT: {c.phone_number}
                      </p>
                      {c.notes && (
                        <p className="mt-0.5 truncate text-[11px] text-slate-600">
                          Ghi chú: {c.notes}
                        </p>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation();
                        openEditCustomer(c);
                      }}
                      title="Sửa thông tin"
                    >
                      <Edit2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>

        {/* Right column: Selected Customer Profile & Treatment Packages */}
        <Card className="lg:col-span-7">
          {!selectedCustomer ? (
            <CardContent className="flex flex-col items-center justify-center py-16 text-center">
              <UserIcon className="h-10 w-10 text-muted-foreground" />
              <p className="mt-2 text-sm font-medium">
                Chọn 1 khách hàng bên trái để xem Thẻ liệu trình
              </p>
            </CardContent>
          ) : (
            <>
              <CardHeader className="flex flex-col gap-3 border-b border-border sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <CardTitle className="text-lg">
                    {selectedCustomer.full_name}
                  </CardTitle>
                  <CardDescription>
                    SĐT: <strong>{selectedCustomer.phone_number}</strong> • Tạo
                    lúc: {formatDateTimeVN(selectedCustomer.created_at)}
                  </CardDescription>
                  <p className="mt-1.5 text-xs text-slate-700">
                    <strong>Ghi chú da / sức khỏe:</strong>{" "}
                    {selectedCustomer.notes || "Chưa có ghi chú"}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => openEditCustomer(selectedCustomer)}
                  >
                    <Edit2 className="h-3.5 w-3.5" />
                    Sửa hồ sơ
                  </Button>
                  <Button size="sm" onClick={openIssuePackageModal}>
                    <PackagePlus className="h-4 w-4" />
                    Cấp thẻ liệu trình
                  </Button>
                </div>
              </CardHeader>

              <CardContent className="pt-4 space-y-3">
                <h4 className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
                  <Ticket className="h-4 w-4 text-primary" />
                  Thẻ liệu trình đang sở hữu ({packages.length})
                </h4>

                {packagesLoading ? (
                  <p className="py-6 text-center text-xs text-muted-foreground">
                    Đang tải thẻ liệu trình...
                  </p>
                ) : packages.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-border p-8 text-center text-xs text-muted-foreground">
                    Khách hàng này chưa có thẻ liệu trình nào. Nhấn &ldquo;Cấp
                    thẻ liệu trình&rdquo; để bán gói mới.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {packages.map((pkg) => {
                      const pct = Math.min(
                        100,
                        Math.round(
                          (pkg.used_sessions / Math.max(pkg.total_sessions, 1)) *
                            100
                        )
                      );
                      return (
                        <div
                          key={pkg.id}
                          className="rounded-xl border border-border bg-muted/20 p-4 space-y-2"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <p className="text-sm font-bold text-foreground">
                                {pkg.package_name}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                Ngày cấp: {formatDateTimeVN(pkg.created_at)}
                                {pkg.expiry_date &&
                                  ` • Hạn dùng: ${formatDateTimeVN(pkg.expiry_date)}`}
                              </p>
                            </div>
                            <Badge
                              variant={
                                pkg.status === "ACTIVE"
                                  ? "success"
                                  : pkg.status === "COMPLETED"
                                    ? "secondary"
                                    : "danger"
                              }
                            >
                              {pkg.status}
                            </Badge>
                          </div>

                          <div className="space-y-1">
                            <div className="flex items-center justify-between text-xs">
                              <span>
                                Đã thực hiện:{" "}
                                <strong>
                                  {pkg.used_sessions} / {pkg.total_sessions}{" "}
                                  buổi
                                </strong>
                              </span>
                              <span className="font-semibold text-primary">
                                Còn lại: {pkg.remaining_sessions} buổi
                              </span>
                            </div>
                            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                              <div
                                className="h-full bg-primary transition-all"
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </>
          )}
        </Card>
      </div>

      {/* Add / Edit Customer Modal */}
      <Modal
        open={customerModalOpen}
        onClose={() => setCustomerModalOpen(false)}
        title={
          editingCustomer
            ? "Cập nhật hồ sơ Khách hàng"
            : "Thêm Khách hàng mới"
        }
      >
        <form
          onSubmit={(e) => void handleSaveCustomer(e)}
          className="space-y-4"
        >
          <div className="space-y-1.5">
            <Label htmlFor="custName">Họ và tên khách hàng</Label>
            <Input
              id="custName"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Nguyễn Thu Trang"
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="custPhone">Số điện thoại</Label>
            <Input
              id="custPhone"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="0901234567"
              disabled={Boolean(editingCustomer)}
              required
            />
          </div>

          {!editingCustomer && (
            <div className="space-y-1.5">
              <Label htmlFor="custPwd">
                Mật khẩu đăng nhập App (Để trống hệ thống tự sinh)
              </Label>
              <Input
                id="custPwd"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Tùy chọn (>= 6 ký tự)"
              />
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="custNotes">
              Ghi chú tình trạng da / dị ứng / sở thích
            </Label>
            <Textarea
              id="custNotes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Da nhạy cảm, thích lực massage nhẹ..."
            />
          </div>

          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setCustomerModalOpen(false)}
            >
              Hủy
            </Button>
            <Button type="submit" disabled={savingCustomer}>
              {savingCustomer ? "Đang lưu..." : "Lưu thông tin"}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Issue Customer Package Modal */}
      <Modal
        open={pkgModalOpen}
        onClose={() => setPkgModalOpen(false)}
        title={`Cấp thẻ liệu trình mới — ${selectedCustomer?.full_name ?? ""}`}
        description="Chọn dịch vụ gói (is_package = true) để khởi tạo thẻ liệu trình cho khách."
      >
        <form onSubmit={(e) => void handleIssuePackage(e)} className="space-y-4">
          {packageServices.length === 0 ? (
            <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-800">
              Spa chưa có Dịch vụ nào thuộc loại Gói liệu trình (
              <code>is_package = true</code>). Hãy tạo Gói liệu trình trong mục{" "}
              <strong>Danh mục Dịch vụ</strong> trước.
            </div>
          ) : (
            <>
              <div className="space-y-1.5">
                <Label htmlFor="pkgService">Chọn Gói liệu trình gốc</Label>
                <select
                  id="pkgService"
                  value={pkgServiceId}
                  onChange={(e) => {
                    const id = e.target.value;
                    setPkgServiceId(id);
                    const found = packageServices.find((s) => s.id === id);
                    if (found) {
                      setPkgName(found.name);
                      setPkgSessions(found.total_sessions);
                    }
                  }}
                  className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  required
                >
                  {packageServices.map((svc) => (
                    <option key={svc.id} value={svc.id}>
                      {svc.name} ({svc.total_sessions} buổi •{" "}
                      {formatCurrency(svc.price)})
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="pkgCustomName">Tên hiển thị trên thẻ</Label>
                <Input
                  id="pkgCustomName"
                  value={pkgName}
                  onChange={(e) => setPkgName(e.target.value)}
                  required
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="pkgSessions">Tổng số buổi</Label>
                  <Input
                    id="pkgSessions"
                    type="number"
                    min={1}
                    max={200}
                    value={pkgSessions}
                    onChange={(e) =>
                      setPkgSessions(parseInt(e.target.value || "1", 10))
                    }
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="pkgExpiry">Ngày hết hạn (Tùy chọn)</Label>
                  <Input
                    id="pkgExpiry"
                    type="date"
                    value={pkgExpiry}
                    onChange={(e) => setPkgExpiry(e.target.value)}
                  />
                </div>
              </div>
            </>
          )}

          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setPkgModalOpen(false)}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              disabled={savingPackage || packageServices.length === 0}
            >
              {savingPackage ? "Đang cấp thẻ..." : "Xác nhận cấp thẻ"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
